# Indicator 15 - Local energy affordability and thermal comfort

## Why this module exists

Most public data available at municipality level describe **vulnerability
conditions** rather than directly observed energy poverty.

EPAH explicitly includes direct indicators such as:
- inability to keep the home adequately warm;
- arrears on utility bills;
- inability to keep the dwelling comfortably cool in summer;
- high energy expenditure burden and low absolute energy expenditure.

For the 27 Green Community municipalities, public EU-wide datasets generally do
not provide these indicators at municipality level. This module therefore
supports a small **local anonymous aggregate data collection**.

## Privacy design

The repository does not require or store:
- names;
- addresses;
- tax identifiers;
- POD/PDR codes;
- exact household income;
- individual questionnaire responses.

Only municipality-level aggregate counts are ingested.

To avoid unstable or potentially revealing small-number outputs, percentages
are suppressed when fewer than **10 respondents** are available for a
municipality. Such rows are retained as acquired data but are not marked as
validated percentages.

## Required aggregate fields

Save the completed file as:

`data/raw/local_energy_affordability.csv`

Required columns:

- `municipality`
- `respondents`
- `unable_warm_yes`
- `utility_arrears_yes`
- `unable_cool_yes`
- `reduced_heating_cost_yes`

All counts must be explicit nonnegative integers. Missing answers are not zero;
fractional counts and duplicate municipality records are rejected. Integer-valued
spreadsheet forms such as `20.0` and `20,0` are accepted. This format assumes a
common valid-response denominator for all four questions; do not encode item
nonresponse as a negative answer.

A ready-to-fill template is provided at:

`data/reference/local_energy_affordability_template.csv`

## Suggested questionnaire wording

Questions should refer to the household and a clearly specified recent period.

Recommended concepts:

1. **Winter thermal affordability**
   - In the last heating season, was your household unable, for economic
     reasons, to keep the dwelling adequately warm?

2. **Utility arrears**
   - In the last 12 months, has your household been in arrears on electricity,
     gas or other household energy bills because of financial difficulty?

3. **Summer thermal affordability**
   - During the most recent summer, was your household unable, for economic
     reasons, to keep the dwelling adequately cool?

4. **Self-restriction**
   - In the last heating season, did your household reduce or avoid heating
     because of energy costs?

Use yes/no responses for these four variables if the goal is direct
comparability and simple aggregation.

## Indicators produced

The pipeline produces four municipal percentages:

- `inability_keep_home_warm`
- `utility_bill_arrears`
- `inability_keep_home_cool`
- `reduced_heating_for_cost`

The first three align directly with EPAH indicator concepts. The fourth is a
local diagnostic self-restriction indicator that complements them.

## Run

The historical finalizer name now invokes a **preview-only** builder. It requires
an explicit reference period and a fresh output directory outside the source
and canonical-data directories. It never changes the matrix, catalog, or
approval state:

```bash
uv run --locked python scripts/finalize_local_energy_affordability.py \
  --input data/raw/local_energy_affordability.csv \
  --period-start 2025-01-01 --period-end 2025-12-31 \
  --out-dir outputs/quality/local-affordability-review-01
```

The dates above are an example: use the documented period of the actual survey.
Use UTF-8 CSV. Outputs are `preview.csv`, `summary.json`, `qa.json`, a SHA-256
`manifest.json` and review instructions, all in the new directory. They retain
`technical_draft_do_not_publish`; no rows become `Dato validato` automatically.

For municipalities with fewer than ten respondents, the preview blanks **both
counts and percentages**, including the respondent total, and records
`small_sample_suppressed`. Summary totals and rates include only eligible
municipalities; they contain no all-municipality count from which a suppressed
count can be recovered. An all-suppressed survey produces null aggregate rates.
The raw input is not copied into the preview: keep it in a separate location
with appropriate access controls. QA records technical status and municipality
coverage without exposing suppressed counts.

This minimum threshold does not guarantee anonymity or statistical reliability.
Review small positive/complementary cells, other available outputs, sampling,
nonresponse and valid-response denominators before sharing. The
[v0.4 review](v0_4_review_and_roadmap.md) describes the wider methodology work.

## Interpretation

These are substantially closer to direct energy-poverty conditions than the
existing structural proxies, but they remain self-reported and sample
dependent.

They should be cross-read with:
- income vulnerability;
- old building stock and APE;
- heating fuel mix;
- Heating Degree Days;
- Cooling Degree Days;
- Heat Stress Days.

No overall energy-poverty score is calculated.
