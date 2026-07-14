# Veterans' preference in federal hiring — deriving the numbers

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/abigailhaddad/veterans-preference-numbers/blob/main/veterans_preference_numbers.ipynb)

A single, self-contained notebook that derives — from source — the federal-workforce
figures behind the argument that veterans' preference in federal hiring reaches only a
minority of veterans.

**Run it:** click the *Open in Colab* badge above, or open
[`veterans_preference_numbers.ipynb`](veterans_preference_numbers.ipynb) locally and run
top to bottom. The only dependency is DuckDB (the notebook installs it if needed); pandas
is already present on Colab.

## What it does

OPM/EHRI figures are queried **live** from the public HuggingFace dataset
[`impactproject/opm-ehri-data`](https://huggingface.co/datasets/impactproject/opm-ehri-data)
with DuckDB over HTTPS — **nothing is downloaded to disk** and there are no local files to
stage. The notebook lists the dataset's parquet files from the HuggingFace repo API, keeps
the latest version of each month, and queries them in place.

External veteran-population figures (VA VetPop, Census ACS, DoD/CRS, MSPB) are national
published statistics, not in EHRI; each is entered with its source in the cell where it is
used.

## What it derives

- **The stock** — veterans currently in federal jobs (~560k), their share of the workforce
  (~28%), and their share of the veteran population, shown both EHRI-as-is and
  coverage-adjusted (EHRI omits USPS + a few agencies).
- **The flow, 2010–2024** — annual veteran new hires (transfers excluded), the ~48k–78k
  range, and the veteran share of all new hires falling from ~30% to ~21%.
- **2024 vs 2025** — the hiring-freeze collapse (~54k → ~21k veteran hires, a ~60% drop).
- **Education** — federally-employed veterans with a bachelor's+ (~48%) vs veterans
  nationally (~32%).
- **Where preference bites** — competitive service vs excepted service, alongside MSPB's
  50%-vs-22% competitive-examining vs direct-hire finding.
- **The "ever" estimate** — the ceiling on how many veterans ever hold a federal job
  (~1 in 4), with the first-time-hire share *measured* from length-of-service at hire
  rather than assumed.

## Caveats

- **EHRI undercounts.** It excludes the Postal Service (which *does* apply veterans'
  preference) and a few other bodies, so its veteran headcount is a floor. Coverage-adjusted
  figures apply a ~1.15× uplift as a knob.
- **The "ever" number is a ceiling.** It credits veterans' preference with *every* veteran
  hire; many of those hires would have happened on the merits regardless.
- **Numbers refresh with the data.** Because everything is queried live, figures may drift
  slightly as the dataset updates. The point is the derivation, not a frozen snapshot.
