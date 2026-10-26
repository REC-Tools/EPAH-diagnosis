# Heating degree days and climate zone

## Indicator

**Heating degree days (GG)** and **climate zone** for each of the 27 Green
Community municipalities.

The legal basis is **DPR 26 August 1993, no. 412, Annex A**, the national table
of municipal heating degree days and climate zones.

The current legal text of Annex A is published by the Italian Ministry of
Economy and Finance legal documentation portal and is marked as in force from
9 August 2016.

## Interpretation

Heating degree days are a conventional indicator of winter heating demand.
Higher values indicate colder climatic conditions and, all else equal, a
greater potential need for space heating.

Under DPR 412/1993:

- Zone E: more than 2,100 and up to 3,000 GG
- Zone F: more than 3,000 GG

Zone F is the coldest regulatory class.

For the EPAH diagnosis this is treated as a **climate exposure indicator**, not
as a direct measure of energy poverty or actual household consumption.

## Source strategy

The repository stores a curated 27-municipality reference snapshot in:

`data/reference/climate_dpr412_green_community.csv`

This avoids scraping a legal website at every run. The source URL and legal
basis remain recorded in the output and verification matrix.

Run:

`python scripts/finalize_heating_degree_days.py`

Outputs:

- `data/indicators/heating_degree_days.csv`
- `data/indicators/heating_degree_days_summary.csv`
- 27 validated rows added to `data/verification_matrix.csv`

The Green Community summary is intentionally **unweighted** because heating
degree days describe municipal climate, not a household or population share.
