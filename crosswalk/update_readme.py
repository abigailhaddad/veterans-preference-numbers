"""Regenerate the numeric blocks in ../README.md from crosswalk output CSVs.

The README's tables were hand-maintained, and hand-maintained numbers go stale
silently. When the late-reported-actions effect was found (see
apply_crosswalk.monthly_accession_urls), CY2024 moved 273,730 -> 276,214 and the
old figure had to be chased through four places in the README; one was missed on
the first pass. This script makes the numbers a build artifact instead.

Everything between a matching pair of

    <!-- AUTOGEN:<name> START -->
    <!-- AUTOGEN:<name> END -->

is replaced. Text outside those markers is never touched, so the prose stays
hand-written.

Usage:
    python3 apply_crosswalk.py --start 201501 --end 202606 --by-year
    python3 update_readme.py --start 201501 --end 202606 --headline-year 2024
"""
import argparse
import re
from pathlib import Path

import pandas as pd
import yaml

HERE = Path(__file__).parent
README = HERE.parent / "README.md"

VERDICT_ORDER = [
    "Yes (applies)", "Ambiguous (DHA-eligible)",
    "Limited (exempt from 302 ranking procedures)", "No (outside title 5)",
    "No (not preference-eligible)", "Unknown",
]

# Plain-English name for each verdict, plus a fixed gloss where the category
# can't be explained by naming example buckets. Where the gloss is None the
# examples are generated from the detail CSV's largest buckets instead.
PLAIN_VERDICT = {
    "Yes (applies)":
        ("**Standard preference rules applied**",
         "The ordinary 5- and 10-point preference system"),
    "Limited (exempt from 302 ranking procedures)":
        ("Preference counted, but no required ranking", None),
    "No (not preference-eligible)":
        ("Preference didn't apply to the job", None),
    "No (outside title 5)":
        ("Not covered by the preference law at all", None),
    "Ambiguous (DHA-eligible)":
        ("**Could have skipped preference ranking — can't tell**",
         "The job qualified for a fast-track hiring authority that waives ranking. "
         "Whether the agency used it isn't recorded."),
    "Unknown":
        ("**Can't tell from the data**", "The hiring authority isn't identifiable"),
}

# Order the headline table by how the reader should read it: resolved verdicts
# first, then the two "can't tell" rows, which are the point.
HEADLINE_ORDER = [
    "Yes (applies)",
    "Limited (exempt from 302 ranking procedures)",
    "No (not preference-eligible)",
    "No (outside title 5)",
    "Ambiguous (DHA-eligible)",
    "Unknown",
]


def replace_block(text: str, name: str, body: str) -> str:
    """Swap the content between one AUTOGEN marker pair. Errors if absent."""
    start, end = f"<!-- AUTOGEN:{name} START -->", f"<!-- AUTOGEN:{name} END -->"
    pat = re.compile(rf"{re.escape(start)}.*?{re.escape(end)}", re.DOTALL)
    if not pat.search(text):
        raise SystemExit(f"marker pair AUTOGEN:{name} not found in {README}")
    # Replace via a function so backslashes/backreferences in `body` stay literal.
    return pat.sub(lambda _: f"{start}\n{body}\n{end}", text)


def plain_labels() -> dict[str, str]:
    spec = yaml.safe_load((HERE / "crosswalk.yaml").read_text())
    return {r["label"]: r.get("plain_label", r["label"]) for r in spec["regimes"]}


def headline_block(by_year: pd.DataFrame, detail: pd.DataFrame, year: int) -> str:
    if year not in by_year.index:
        raise SystemExit(f"--headline-year {year} not in the by-year CSV")
    row = by_year.loc[year]
    total = int(row["total"])
    names = plain_labels()

    lines = [
        f"Of the {total:,} people hired into the federal government in calendar year {year}:",
        "",
        "| | Share | What it means |",
        "|---|---|---|",
    ]
    for verdict in HEADLINE_ORDER:
        if verdict not in by_year.columns:
            continue
        label, gloss = PLAIN_VERDICT[verdict]
        if gloss is None:
            # Name the two largest buckets in this verdict. Illustrative only:
            # the detail CSV covers the whole run window, not just `year`, so
            # deliberately no percentages here -- they would mix periods.
            top = (detail[detail.veterans_preference == verdict]
                   .nlargest(2, "accessions").bucket.map(lambda b: names.get(b, b)))
            # Semicolons, not "and": several plain labels contain their own commas
            # and conjunctions ("VA doctors, dentists, and nurses"), so joining
            # with "and" produces "X and nurses and Y".
            gloss = "Mostly " + "; ".join(top) if len(top) else "—"
        share = row[verdict]
        share_txt = f"**{share:.1f}%**" if label.startswith("**") else f"{share:.1f}%"
        lines.append(f"| {label} | {share_txt} | {gloss} |")
    return "\n".join(lines)


def degradation_block(by_year: pd.DataFrame, sample_years: list[int]) -> str:
    """The 2010-2014 vs 2015+ comparison behind the recommended 2015 floor.

    Generated from the same run as everything else on purpose. These rows were
    originally measured one year at a time, before reading past --end was the
    default, so the early row used a window-only run while the later rows didn't
    -- a degradation table whose two halves used different methods.
    """
    lines = ['| Year | "Unknown" | "Yes (applies)" |', "|---|---|---|"]
    for yr in sample_years:
        if yr not in by_year.index:
            continue
        row = by_year.loc[yr]
        lines.append(f"| {yr} | {row['Unknown']:.1f}% | {row['Yes (applies)']:.1f}% |")
    return "\n".join(lines)


def by_year_block(by_year: pd.DataFrame, end: str, min_year: int) -> str:
    partial_year, partial_month = int(end[:4]), int(end[4:])
    lines = [
        "| Year | Standard rules applied | Could have skipped ranking | Can't tell | People hired |",
        "|---|---|---|---|---|",
    ]
    for yr, row in by_year[by_year.index >= min_year].iterrows():
        name = (f"{yr} (Jan–{['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][partial_month]})"
                if yr == partial_year and partial_month < 12 else str(yr))
        lines.append(
            f"| {name} | {row['Yes (applies)']:.1f}% | {row['Ambiguous (DHA-eligible)']:.1f}% "
            f"| {row['Unknown']:.1f}% | {int(row['total']):,} |"
        )
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="201501")
    ap.add_argument("--end", default="202606")
    ap.add_argument("--headline-year", type=int, default=2024)
    ap.add_argument("--min-year", type=int, default=2015,
                     help="first year shown in the by-year table. Defaults to the 2015 "
                          "accuracy floor; earlier years are still read so the degradation "
                          "table can quote them.")
    ap.add_argument("--degradation-years", default="2012,2015,2024",
                     help="the years compared in the 2015-floor argument")
    args = ap.parse_args()

    by_year = pd.read_csv(HERE / f"crosswalk_by_year_{args.start}_{args.end}.csv", index_col="yr")
    detail = pd.read_csv(HERE / f"crosswalk_{args.start}_{args.end}.csv")

    text = README.read_text()
    text = replace_block(text, "headline", headline_block(by_year, detail, args.headline_year))
    text = replace_block(text, "byyear", by_year_block(by_year, args.end, args.min_year))
    text = replace_block(text, "degradation", degradation_block(
        by_year, [int(y) for y in args.degradation_years.split(",")]))
    README.write_text(text)
    print(f"Updated {README} from {args.start}-{args.end} "
          f"(headline {args.headline_year}, by-year from {args.min_year})")


if __name__ == "__main__":
    main()
