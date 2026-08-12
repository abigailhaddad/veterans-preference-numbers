"""Apply crosswalk.yaml to live OPM/EHRI accessions data.

One file (crosswalk.yaml) has two sections read together here:
  `regimes`         - which legal regime governed veterans'-preference
                      applicability for the hiring action (first-match-wins CASE)
  `dha_authorities` - which direct-hire authority (if any) the record's
                      series+grade+date(+agency) is ELIGIBLE under -- a separate,
                      cross-cutting dimension, since DHA eligibility leaves no
                      trace in service type/pay plan/appointment type

Both are folded into ONE final "veterans_preference" verdict per record:
  Yes (applies) / Ambiguous (DHA-eligible) / Limited (exempt from 302 ranking) /
  No (outside title 5) / No (not preference-eligible) / Unknown

Nothing is downloaded to disk; everything is queried live via DuckDB/httpfs against
the public impactproject/opm-ehri-data accessions parquet.

Usage:
    python3 apply_crosswalk.py [--start 202401] [--end 202412] [--detail]
"""
import argparse
import json
import re
import urllib.request
from pathlib import Path

for pkg, mod in [("duckdb", "duckdb"), ("pyyaml", "yaml"), ("pandas", "pandas")]:
    try:
        __import__(mod)
    except ImportError:
        import subprocess, sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pkg])

import duckdb
import pandas as pd
import yaml

HF = "https://huggingface.co/datasets/impactproject/opm-ehri-data/resolve/main/"
TREE = "https://huggingface.co/api/datasets/impactproject/opm-ehri-data/tree/main?recursive=true"
HERE = Path(__file__).parent
DOD_AGENCY_PREFIXES = "('AF','AR','NV','DD')"

VERDICT_LABEL = {
    "outside_title5": "No (outside title 5)",
    "exempt_from_302": "Limited (exempt from 302 ranking procedures)",
    "not_preference_eligible": "No (not preference-eligible)",
    "unknown": "Unknown",
    # "applies_full" is special-cased in main(), split by DHA-eligibility
}
VERDICT_ORDER = [
    "Yes (applies)", "Ambiguous (DHA-eligible)",
    "Limited (exempt from 302 ranking procedures)", "No (outside title 5)",
    "No (not preference-eligible)", "Unknown",
]


def list_all_files() -> list[dict]:
    """Every file in the HF tree, following pagination.

    The tree API caps a single response at 1000 entries (Link header,
    rel="next", cursor-based). A one-shot fetch silently truncates -- the repo
    already has 1000+ files total, and accessions/employment only happened to
    survive the first page because "accessions" and "employment" sort before
    "separations" alphabetically. Confirmed 2026-08-08 by pulling all pages:
    392 accessions files, 340 employment, 393 separations, none of which a
    single-page fetch would have shown in full much longer.
    """
    url = TREE
    out: list[dict] = []
    while url:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as r:
            headers = dict(r.getheaders())
            out.extend(json.load(r))
        link = headers.get("Link")
        m = re.search(r'<([^>]+)>;\s*rel="next"', link) if link else None
        url = m.group(1) if m else None
    return out


def monthly_accession_urls(start: str, end: str, include_late: bool = True) -> list[str]:
    """Latest version per month, from `start` through `end` (YYYYMM strings).

    With include_late (the default), the FILE range runs past `end` to the newest
    month published, while the effective-date filter in the query still honors
    `end`. A monthly file carries personnel actions whose effective date falls in
    earlier months, so reading only the files inside the window undercounts it --
    and undercounts the most recent year worst, because its late filings have not
    landed yet. Measured 2026-08: the 2025 files hold 995 actions effective in
    2024, and the 2026 H1 files hold another 1,489 effective in 2024 plus 10,893
    effective in 2025. So CY2024 read from its own 12 files is 273,730, but
    276,214 once later files are included, and CY2025 jumps 116,076 -> 126,969+
    and is still climbing. Pass --no-late-reports to restore the old, faster,
    window-only behavior.
    """
    file_end = "999999" if include_late else end
    files = list_all_files()
    best: dict[str, tuple[int, str]] = {}
    for f in files:
        m = re.search(r"accessions_(\d{6})_v(\d+)\.parquet", f["path"])
        if not m:
            continue
        month, ver = m.group(1), int(m.group(2))
        if start <= month <= file_end and (month not in best or ver > best[month][0]):
            best[month] = (ver, f["path"])
    return [HF + best[m][1] for m in sorted(best)]


def sql_quote(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def sql_quote_list(items: list[str]) -> str:
    return "(" + ",".join(sql_quote(i) for i in items) + ")"


def grade_set(range_str: str) -> list[str]:
    if range_str == "all":
        lo, hi = 1, 15
    else:
        lo, hi = (int(x) for x in range_str.split("-"))
        hi = min(hi, 15)  # "09-99" -> cap at top of GS scale actually present in the data
    return [f"{g:02d}" for g in range(lo, hi + 1)]


def build_regime_case_sql(regimes: list[dict]) -> str:
    """First-match-wins CASE over `regimes`, in YAML list order.

    A regime may carry an optional top-level `eligible_from: "YYYY-MM"` when
    the underlying legal authority didn't exist (or didn't cover these
    records) before a known date -- e.g. DoD Cyber Excepted Service wasn't
    implemented until Aug 2017, so a DoD+excepted+GG hire from 2012 cannot
    actually be CES no matter how well the field-based heuristic matches it.
    When present, the date check is ANDed into the predicate; records before
    that date fall through to the next rule instead of being misclassified.
    Most regimes have no eligible_from because the underlying authority
    predates the accessions window (2005-present) entirely.
    """
    clauses = []
    for r in regimes:
        pred = r["sql_predicate"].strip()
        if pred.upper().startswith("TRUE"):
            clauses.append(f"    ELSE {sql_quote(r['label'])}")
            continue
        eligible_from = r.get("eligible_from")
        if eligible_from:
            date_clause = sql_quote(eligible_from.replace("-", "")[:6])
            pred = f"({pred})\n         AND personnel_action_effective_date_yyyymm >= {date_clause}"
        clauses.append(f"    WHEN {pred} THEN {sql_quote(r['label'])}")
    return "CASE\n" + "\n".join(clauses) + "\nEND"


def build_dha_case_sql(authorities: list[dict]) -> str:
    """First-match-wins CASE over every (authority, covered_series) pair.

    Several series (2210, 1550, 0854, 1811, 0343) are covered by more than one
    authority with different grade ranges and different conditionality. Entries
    are sorted UNCONDITIONAL FIRST: an unconditional grant (e.g. GW-008 for 1550
    GS-12-15) should win over a later, narrower, conditional grant (e.g. GW-009's
    AI-conditional 1550 GS-09-15) for any grade where both apply. Within each
    tier, original YAML order is kept, so for 2210 the broadest/oldest
    conditional grant (GW-002, GS-09-15 since 2003) is checked before the
    narrower/newer ones (GW-008, GW-009, Z5CL) -- functionally equivalent since
    all are equally "conditional, coding basis unconfirmed," but GW-002 already
    covers the full range so it is the one reported.
    """
    entries = []
    for auth in authorities:
        for s in auth["covered_series"]:
            entries.append((auth["id"], s, auth.get("agency_scope")))
    entries.sort(key=lambda e: bool(e[1].get("cybersecurity_coding_required", False)))

    clauses = []
    for auth_id, s, agency_scope in entries:
        grades = sql_quote_list(grade_set(s["grades"]))
        eligible_from = s["eligible_from"].replace("-", "")[:6]
        conditional = s.get("cybersecurity_coding_required", False)
        label = f"yes_conditional_{auth_id}" if conditional else f"yes_{auth_id}"
        agency_clause = (f"         AND substr(agency_code,1,2) IN {DOD_AGENCY_PREFIXES}\n"
                          if agency_scope == "dod" else "")
        clauses.append(
            f"    WHEN occupational_series_code = {sql_quote(s['series'])}\n"
            f"{agency_clause}"
            f"         AND grade IN {grades}\n"
            f"         AND personnel_action_effective_date_yyyymm >= {sql_quote(eligible_from)}\n"
            f"         AND position_occupied = 'COMPETITIVE SERVICE'\n"
            f"         AND pay_plan_code IN ('GS','GG')\n"
            f"    THEN {sql_quote(label)}"
        )
    return "CASE\n" + "\n".join(clauses) + "\n    ELSE 'no'\nEND"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="202401")
    ap.add_argument("--end", default="202412")
    ap.add_argument("--detail", action="store_true", help="also print bucket-level detail")
    ap.add_argument("--by-year", action="store_true",
                     help="print a year-by-year verdict-share trend table (needs a multi-year --start/--end)")
    ap.add_argument("--no-late-reports", action="store_true",
                     help="read only the files inside --start/--end. Faster, but undercounts: "
                          "later files carry actions effective inside the window (see "
                          "monthly_accession_urls). Off by default.")
    args = ap.parse_args()

    # Hard floor, not a bug: veteran_indicator AND position_occupied both first
    # appear in 2010-01 (33 cols through 2009-12, 65+ from 2010-01 on). Every
    # VA/Guard/FEMA/attorney/CES/ordinary-competitive regime predicate keys off
    # position_occupied -- before 2010 it's NULL under union_by_name, so those
    # WHEN clauses silently fail rather than misfire, and everything collapses
    # into "Unknown" instead of a real verdict. Confirmed via DESCRIBE across
    # 2005-2009 sample months (2026-08-07).
    if args.start < "201001":
        print(f"NOTE: veteran_indicator and position_occupied do not exist before "
              f"2010-01 (pre-2010 accessions have 33 cols vs 65+ from 2010-01 on) "
              f"-- most regime rules depend on position_occupied and would silently "
              f"collapse to 'Unknown' rather than misclassify. Clamping --start from "
              f"{args.start} to 201001.")
        args.start = "201001"

    spec = yaml.safe_load((HERE / "crosswalk.yaml").read_text())
    regimes = spec["regimes"]
    dha_authorities = spec["dha_authorities"]

    regime_case_sql = build_regime_case_sql(regimes)
    dha_case_sql = build_dha_case_sql(dha_authorities)
    label_to_status = {r["label"]: r["preference_status"] for r in regimes}
    label_to_confidence = {r["label"]: r["confidence"] for r in regimes}

    urls = monthly_accession_urls(args.start, args.end, include_late=not args.no_late_reports)
    late_note = "" if args.no_late_reports else ", plus later files for late-reported actions"
    print(f"Querying {len(urls)} monthly files ({args.start}-{args.end}{late_note})...")
    if not args.no_late_reports:
        print("      The most recent year in any run is still provisional: its late filings "
              "have not been published yet.")
    lst = "[" + ",".join(f"'{u}'" for u in urls) + "]"

    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")

    # union_by_name only reconciles a column that exists in AT LEAST ONE file in
    # the list. If NO file in the window has it, the name is simply absent and the
    # regime CASE fails to bind outright. That bites any window sitting entirely
    # inside 2010-2014, where pathways_group does not exist yet (it first appears
    # 2015-01, taking the schema 65 -> 68 cols): 201201-201212 raised
    # "Binder Error: Referenced column pathways_group not found", while
    # 201412-201501 worked only because the 201501 file carried the column.
    # Inject the absent ones as typed NULLs so their branches simply never match
    # and those records fall through to "Unknown" -- the documented behavior.
    referenced = list(spec["metadata"]["fields_used"]) + ["veteran_indicator"]
    present = {r[0] for r in con.execute(
        f"DESCRIBE SELECT * FROM read_parquet({lst}, union_by_name=true)").fetchall()}
    absent = [c for c in referenced if c not in present]
    filler = "".join(f", CAST(NULL AS VARCHAR) AS {c}" for c in absent)
    if absent:
        print(f"NOTE: absent from every file in {args.start}-{args.end}, treated as NULL "
              f"(records relying on them fall through to 'Unknown'): {', '.join(absent)}")
    # union_by_name=true: schemas drift across the accessions history (33 cols in
    # 2005 vs 68 today -- no department/veteran_indicator/pathways_group in the
    # earliest files). Without this, read_parquet on a mixed-schema file list
    # throws a binder error the moment --start reaches back far enough.
    df = con.execute(f"""
        SELECT {regime_case_sql} AS bucket,
               {dha_case_sql} AS dha_eligible,
               substr(personnel_action_effective_date_yyyymm, 1, 4) AS yr,
               SUM(TRY_CAST(count AS BIGINT)) AS hires,
               SUM(CASE WHEN veteran_indicator='Y' THEN TRY_CAST(count AS BIGINT) END) AS vets
        FROM (SELECT *{filler} FROM read_parquet({lst}, union_by_name=true))
        WHERE personnel_action_effective_date_yyyymm BETWEEN '{args.start}' AND '{args.end}'
        GROUP BY 1, 2, 3
    """).df().fillna({"vets": 0})

    df["preference_status"] = df.bucket.map(label_to_status)
    df["confidence"] = df.bucket.map(label_to_confidence)
    df["dha_flag"] = df.dha_eligible != "no"

    def verdict(row):
        if row.preference_status == "applies_full":
            return "Ambiguous (DHA-eligible)" if row.dha_flag else "Yes (applies)"
        return VERDICT_LABEL[row.preference_status]

    df["veterans_preference"] = df.apply(verdict, axis=1)

    pd.set_option("display.width", 320)
    order_key = {v: i for i, v in enumerate(VERDICT_ORDER)}

    if args.by_year:
        yearly = df.groupby(["yr", "veterans_preference"]).hires.sum().reset_index()
        totals = yearly.groupby("yr").hires.sum().rename("total")
        yearly = yearly.merge(totals, on="yr")
        yearly["pct"] = yearly.hires / yearly.total * 100
        pivot = yearly.pivot(index="yr", columns="veterans_preference", values="pct")
        pivot = pivot[[c for c in VERDICT_ORDER if c in pivot.columns]]
        print(f"\n=== Verdict share by year (% of that year's accessions), {args.start}-{args.end} ===\n")
        print(pivot.to_string(float_format=lambda x: f"{x:,.1f}", na_rep="-"))
        print(f"\n(accessions per year)")
        print(totals.to_string())

        # The period-total CSV below collapses every year together, so the trend
        # this table shows would otherwise exist only in stdout.
        by_year_out = HERE / f"crosswalk_by_year_{args.start}_{args.end}.csv"
        pivot.round(1).join(totals).to_csv(by_year_out)
        print(f"\nWrote {by_year_out}")

    summary = df.groupby("veterans_preference").agg(
        accessions=("hires", "sum"), veterans=("vets", "sum")).reset_index()
    summary["vet_pct"] = summary.veterans / summary.accessions * 100
    summary["pct_of_accessions"] = summary.accessions / summary.accessions.sum() * 100
    summary["_order"] = summary.veterans_preference.map(order_key)
    summary = summary.sort_values("_order").drop(columns="_order")

    print(f"\n=== {df.hires.sum():,.0f} accessions, {args.start}-{args.end} (full period) ===\n")
    print(summary[["veterans_preference", "accessions", "pct_of_accessions", "veterans", "vet_pct"]]
          .to_string(index=False, float_format=lambda x: f"{x:,.1f}"))

    detail = df.groupby(["veterans_preference", "bucket", "confidence"]).agg(
        accessions=("hires", "sum"), veterans=("vets", "sum")).reset_index()
    detail["vet_pct"] = detail.veterans / detail.accessions * 100
    detail["_order"] = detail.veterans_preference.map(order_key)
    detail = detail.sort_values(["_order", "accessions"], ascending=[True, False]).drop(columns="_order")

    if args.detail:
        print(f"\n=== DETAIL, by bucket within each verdict ===\n")
        print(detail[["veterans_preference", "bucket", "confidence", "accessions", "veterans", "vet_pct"]]
              .to_string(index=False, float_format=lambda x: f"{x:,.1f}"))

    # Filename encodes the window on purpose: a short exploratory run must not
    # silently overwrite the committed reference output for a different period.
    out = HERE / f"crosswalk_{args.start}_{args.end}.csv"
    detail.to_csv(out, index=False)
    print(f"\nWrote {out} (pass --detail to also print the bucket-level table)")


if __name__ == "__main__":
    main()
