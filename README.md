# Veterans' preference in federal hiring — deriving the numbers

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/abigailhaddad/veterans-preference-numbers/blob/main/veterans_preference_numbers.ipynb)

A single, self-contained notebook that derives the federal-workforce figures behind the
argument that veterans' preference in federal hiring reaches only a minority of veterans.

**Run it:** click the *Open in Colab* badge, or open
[`veterans_preference_numbers.ipynb`](veterans_preference_numbers.ipynb) and run top to
bottom. The only dependency is DuckDB (installed by the notebook if needed).

OPM/EHRI figures are queried **live** from the public HuggingFace dataset
[`impactproject/opm-ehri-data`](https://huggingface.co/datasets/impactproject/opm-ehri-data)
with DuckDB over HTTPS — nothing is downloaded to disk. External population figures (VA
VetPop, Census ACS, DoD/CRS, MSPB) are entered with their sources in the cells that use them.

## What it derives

- **The stock** — veterans currently in federal jobs (~560k), ~28% of the workforce, and
  their share of the veteran population (EHRI-as-is and coverage-adjusted).
- **The flow, 2010–2024** — annual veteran new hires (~48k–78k), with the veteran share of
  all new hires falling from ~30% to ~21%.
- **2024 vs 2025** — the hiring-freeze collapse (~54k → ~21k, a ~60% drop).
- **Education** — federally-employed veterans with a bachelor's+ (~48%) vs veterans
  nationally (~32%).
- **Where preference bites** — competitive vs excepted service, alongside MSPB's 50%-vs-22%
  competitive-examining vs direct-hire finding.
- **The "ever" ceiling** — the share of veterans who ever hold a federal job (~1 in 4), with
  the first-time-hire share *measured* from length-of-service, not assumed.

## Caveats

- **EHRI undercounts** — it excludes the Postal Service (which applies preference) and a few
  other bodies, so its veteran headcount is a floor; coverage-adjusted figures apply a ~1.15×
  uplift as a knob.
- **The "ever" number is a ceiling** — it credits preference with *every* veteran hire, many
  of which would have happened on the merits regardless.
- **Numbers refresh with the data** — everything is queried live, so figures may drift
  slightly as the dataset updates.
