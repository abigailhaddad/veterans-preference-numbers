# Veterans' preference in federal hiring — deriving the numbers

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/abigailhaddad/veterans-preference-numbers/blob/main/veterans_preference_numbers.ipynb)

A single, self-contained notebook that derives the federal-workforce figures behind the
argument that veterans' preference in federal hiring reaches only a minority of veterans.

## Which federal hires does veterans' preference actually reach?

<!-- AUTOGEN:headline START -->
Of the 276,214 people hired into the federal government in calendar year 2024:

| | Share | What it means |
|---|---|---|
| **Standard preference rules applied** | **58.4%** | The ordinary 5- and 10-point preference system |
| Preference counted, but no required ranking | 5.6% | Mostly VA medical staff; Attorneys |
| Preference didn't apply to the job | 5.4% | Mostly National Guard dual-status technicians; DoD cyber workforce |
| Not covered by the preference law at all | 4.4% | Mostly VA doctors, dentists, and nurses; Paid experts and consultants |
| **Could have skipped preference ranking — can't tell** | **10.3%** | The job qualified for a fast-track hiring authority that waives ranking. Whether the agency used it isn't recorded. |
| **Can't tell from the data** | **15.9%** | The hiring authority isn't identifiable |
<!-- AUTOGEN:headline END -->

**About a quarter of all federal hiring — the bottom two rows — can't be resolved either
way.** That's the honest headline, and it's a property of the data, not of the effort spent
on it.

### By year

<!-- AUTOGEN:byyear START -->
| Year | Standard rules applied | Could have skipped ranking | Can't tell | People hired |
|---|---|---|---|---|
| 2015 | 59.3% | 3.2% | 19.6% | 256,761 |
| 2016 | 61.3% | 3.2% | 19.5% | 262,612 |
| 2017 | 53.9% | 3.9% | 22.7% | 224,500 |
| 2018 | 56.1% | 7.3% | 17.9% | 253,136 |
| 2019 | 54.7% | 9.0% | 18.9% | 282,417 |
| 2020 | 51.9% | 9.5% | 19.8% | 274,218 |
| 2021 | 52.4% | 9.1% | 20.4% | 261,750 |
| 2022 | 56.1% | 11.7% | 16.9% | 321,388 |
| 2023 | 55.0% | 9.2% | 17.5% | 326,424 |
| 2024 | 58.4% | 10.3% | 15.9% | 276,214 |
| 2025 | 52.8% | 6.8% | 18.1% | 126,969 |
| 2026 (Jan–Jun) | 58.7% | 5.7% | 15.9% | 85,514 |
<!-- AUTOGEN:byyear END -->

The three columns not shown — preference counted but not ranked, didn't apply, not covered —
make up the remainder. The full six-way split by year is in
[`crosswalk_by_year_201001_202606.csv`](crosswalk/crosswalk_by_year_201001_202606.csv).

**The fast-track share roughly tripled**, from 3.2% in 2015–16 to 9–12% from 2019 on. The
jump lands in 2018, which is when the government-wide STEM and cybersecurity direct-hire
authorities came in. That's the share of hiring where preference ranking *could* have been
bypassed and the data can't say whether it was.

"Standard rules applied" has no trend — it moves between 52% and 61% with no direction.

> **The last two rows are incomplete and will grow.** A monthly data file carries personnel
> actions that took effect in earlier months, so recent years keep accruing hires for a
> couple of years after the fact. Measured August 2026: CY2024 read from its own twelve
> files came to 273,730, but 276,214 once later files were included — and CY2025 went from
> 116,076 to 126,969, a 9% difference, with more still to come. 2026 covers January–June
> only. **Treat 2025 and 2026 as floors, and don't compute a year-over-year drop off them.**

> **This is provisional. Don't treat the numbers as settled.**
>
> The government doesn't publish *which legal authority* was used for each hire. That field
> exists internally — OPM reports VRA and VEOA totals from it — but it isn't in the public
> data. So the table above is reconstructed from indirect signals: service type, pay plan,
> job series, grade.
>
> That means about **70% of hires are sorted by a catch-all rule** — "nothing indicated an
> exception, so assume the standard rules applied" — rather than by direct evidence. Most of
> the 58.4% top row rests on that assumption. Every figure is a floor.

## The other figures

Derived by the notebook, separately from the crosswalk above:

- **The stock** — veterans currently in federal jobs (~560k), ~28% of the workforce, and
  their share of the veteran population (EHRI-as-is and coverage-adjusted).
- **The flow, 2010–2024** — annual veteran new hires (~48k–78k), with the veteran share of
  all new hires falling from ~30% to ~21%.
- **2024 vs 2025** — the hiring-freeze collapse (~54k → ~21k, a ~60% drop). **Recheck this
  one.** It was computed before the late-reporting effect described above was known, and
  2025 is the year that effect hits hardest — total 2025 accessions rose 9% just from
  reading later files. The drop is real but the magnitude is overstated.
- **Education** — federally-employed veterans with a bachelor's+ (~48%) vs veterans
  nationally (~32%).
- **Where preference bites** — competitive vs excepted service, alongside MSPB's 50%-vs-22%
  competitive-examining vs direct-hire finding.
- **The "ever" ceiling** — the share of veterans who ever hold a federal job (~1 in 4), with
  the first-time-hire share *measured* from length-of-service, not assumed.

These come from OPM's EHRI database (the government-wide federal personnel record), queried
**live** from the public HuggingFace dataset
[`impactproject/opm-ehri-data`](https://huggingface.co/datasets/impactproject/opm-ehri-data)
— nothing is downloaded. External population figures (VA VetPop, Census ACS, DoD/CRS, MSPB)
are entered with their sources in the cells that use them.

To re-run: click the *Open in Colab* badge above, or open
[`veterans_preference_numbers.ipynb`](veterans_preference_numbers.ipynb) and run top to
bottom. The only dependency is DuckDB, installed by the notebook if needed.

---

# How the crosswalk works

Everything below is methodology.

## Accession-level veterans'-preference crosswalk

One YAML, one script: [`crosswalk/crosswalk.yaml`](crosswalk/crosswalk.yaml) holds the
rules, [`crosswalk/apply_crosswalk.py`](crosswalk/apply_crosswalk.py) applies them to the
live data.

The YAML has two sections read together by the script:

- **`regimes`** — which legal regime governed veterans'-preference applicability for
  the hiring action: ordinary 5 USC 3309–3318 mechanical preference, a 5 CFR
  302.101(c) exemption (attorneys, Schedule C, SES), a statute that puts the hire
  outside title 5 altogether (VA title 38, PHS fellows, service academy faculty,
  FDIC, TSA, FAA), a person-level exclusion (National Guard dual-status technicians
  under 32 USC 709, DoD Cyber Excepted Service), or unknown. Each entry carries a
  legal citation, a `confidence` tag (`confirmed` / `inferred` / `residual`), and
  the exact detection rule.
- **`dha_authorities`** — seven confirmed direct-hire authorities, matched against
  accessions by series + grade + date (+ agency, for Z5CL). Six are government-wide
  (medical, IT/InfoSec, veterinary, STEM+Acquisitions, Cybersecurity, AI); one is
  DoD-specific. Sourced from primary memos and OPM's DHA listing page.

  This is a separate dimension rather than more `regimes` rules, because DHA
  eligibility leaves no trace in service type, pay plan, or appointment type — a DHA
  hire is recorded identically to an ordinary competitive one. So it can't be a branch
  in the same CASE statement; it has to cross-cut it.

Both are folded into one final `veterans_preference` verdict per accession: **Yes
(applies) / Ambiguous (DHA-eligible) / Limited (exempt from 302 ranking) / No
(outside title 5) / No (not preference-eligible) / Unknown.**

Run it:

```bash
cd crosswalk
python3 apply_crosswalk.py                          # defaults to 202401-202412
python3 apply_crosswalk.py --start 202101 --end 202605 --detail
python3 apply_crosswalk.py --start 201001 --end 202606 --by-year   # trend table
```

This queries the same live HF dataset the notebook uses — nothing downloaded — and writes
`crosswalk_<start>_<end>.csv`. `--detail` also prints the bucket-level breakdown within each
verdict; `--by-year` prints the year-by-year trend and writes
`crosswalk_by_year_<start>_<end>.csv`.

**Runs read past `--end` by default.** A monthly file carries actions that took effect in
earlier months, so a window read from only its own files undercounts — worst for the most
recent year, whose late filings don't exist yet. CY2024 is 273,730 from its twelve files and
276,214 once later files are included; CY2025 goes 116,076 → 126,969. So `--start 202401
--end 202412` reads 30 files, not 12, and is correspondingly slower. `--no-late-reports`
restores the fast window-only behavior and its undercount.

### Regenerating the tables

The two tables at the top of this file are generated, not hand-written. Don't edit them by
hand — anything between an `<!-- AUTOGEN:... -->` marker pair is overwritten:

```bash
cd crosswalk
python3 apply_crosswalk.py --start 201001 --end 202606 --by-year
python3 update_readme.py  --start 201001 --end 202606 --headline-year 2024 --min-year 2015
```

[`update_readme.py`](crosswalk/update_readme.py) reads the two CSVs and rewrites the marked
blocks. The plain-English row names come from `plain_label` on each rule in the YAML, so a
renamed rule updates the README on the next run. Prose outside the markers is never touched,
so any figure quoted in the surrounding text is still hand-maintained — keep those to a
minimum.

Committed reference runs:
[`crosswalk_by_year_201001_202606.csv`](crosswalk/crosswalk_by_year_201001_202606.csv) (the
by-year table above) and
[`crosswalk_201001_202606.csv`](crosswalk/crosswalk_201001_202606.csv) (bucket-level totals
for the whole period).

### Why you can't just run this on every year

The accessions data goes back to 2005, but the crosswalk is only meaningful from **2015
on**. Two separate things break as you go back — one about the data, one about the law.

**The data changed.** The accessions schema has three eras:

| Window | Columns | What's missing |
|---|---|---|
| 2005–2009 | 33 | `veteran_indicator`, `position_occupied`, `pathways_group` |
| 2010–2014 | 65 | `pathways_group` |
| 2015– | 68 | — |

`position_occupied` (`COMPETITIVE SERVICE` / `EXCEPTED SERVICE`) is what nearly every rule
keys off, so pre-2010 records can't be classified at all — they don't land in the *wrong*
bucket, they collapse into "Unknown." The script clamps any earlier `--start` up to 2010-01
rather than return a confidently empty answer. For 2010–2014, `pathways_group` is filled
with NULL and the Pathways rules fall through to "Unknown" instead.

That degradation is measurable, which is the real argument for 2015 as the floor:

<!-- AUTOGEN:degradation START -->
| Year | "Unknown" | "Yes (applies)" |
|---|---|---|
| 2012 | 30.3% | 49.5% |
| 2015 | 19.6% | 59.3% |
| 2024 | 15.9% | 58.4% |
<!-- AUTOGEN:degradation END -->

Nearly a third of 2012 accessions come back "Unknown." The crosswalk runs on 2010–2014 and
won't lie to you about it, but a third of the answer being blank is a different kind of
result than 2015+.

**The law changed, and the crosswalk only partly knows it.** The rules encode the legal
landscape as it stands now. Where an authority has a known start date, the rule is gated to
it, so an older hire can't be classified under a regime that didn't exist yet:

| Rule | Gated from |
|---|---|
| PHS fellows / special consultants | 2015-01 |
| DoD Cyber Excepted Service | 2017-08 |
| VA hybrid title 38, VIPER Act additions | 2022-12 |

All seven direct-hire authorities are gated the same way, from 2003 through 2024.

**But only 3 of the 25 `regimes` rules carry a date gate.** The other 22 are applied
unchanged across the whole window. For most that's fine — the underlying authority predates
2005 — but "predates the window" was established per authority, not per amendment, so a rule
whose *scope* shifted mid-window will silently apply its current scope to earlier years. The
further back you go, the more the output reflects today's law rather than the law in force
at the time. Multi-year runs are best read as a trend in the data, not as a legal history.

### Why it's a floor and not an estimate

The public accessions parquet has no legal-authority or nature-of-action field. The statute
that actually governed a hire simply isn't in the data, so most hires can only be classified
by appointment mechanics — that's what produces the table at the top of this file.

Both the "Unknown" and "Ambiguous" wedges there are undercounts. MSPB's Feb 2021 brief
(*Direct-Hire Authority Under 5 U.S.C. § 3304: Usage and Outcomes*) found DHA of all types
reached ~27% of competitive-service hires by FY2018 — and only 39% of that is §3304 DHA. The
other 61% is DoD's own NDAA-derived authorities (47%) and DoD Laboratory Demonstration
Project DHA (14%), neither enumerated here beyond Z5CL.

`known_gaps` in the YAML has the full list of what the crosswalk cannot see, plus what's
researchable next: agency-specific VA/DHS DHAs, DoD's ~19 other NDAA authorities, and more
named 38 USC 7401(3) professions without a verified series code.

### Citations

Every citation carries a `sources:` entry with a `verified:` tag recording *how* it was
checked — `primary_text_read` (statute/regulation/memo fetched and read directly),
`primary_doc_quoted_in_secondary` (read verbatim as quoted inside another primary document),
`search_summary_only`, or `unverified`. Of 56 citations: 46 `primary_text_read`, 6
`primary_doc_quoted_in_secondary`, and 4 still open — *Graves v. VA* (117 M.S.P.R. 697
(2012), no public URL located), 10 USC 1595, and NDAA FY1995 §342.

Three things that are easy to get wrong:

- **5 USC 3320** doesn't contain the "positive factor... as far as administratively
  feasible" language it usually gets cited for. That's 5 CFR 302.101(c).
- **VRA** is a competitive-service authority (5 CFR 307.101), not Schedule B. It sits in
  the competitive-service buckets.
- **DoD Cyber Excepted Service** doesn't apply 5/10-point preference at all (DoD CES FAQ,
  Q17).

## Caveats

- **EHRI undercounts** — it excludes the Postal Service (which applies preference) and a few
  other bodies, so its veteran headcount is a floor; coverage-adjusted figures apply a ~1.15×
  uplift as a knob.
- **The "ever" number is a ceiling** — it credits preference with *every* veteran hire, many
  of which would have happened on the merits regardless.
- **Numbers refresh with the data** — everything is queried live, so figures may drift
  slightly as the dataset updates.
