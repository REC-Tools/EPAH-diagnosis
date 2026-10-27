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

`python scripts/finalize_local_energy_affordability.py`

Outputs:

- `data/indicators/local_energy_affordability.csv`
- `data/indicators/local_energy_affordability_summary.csv`
- four verification-matrix rows per municipality.

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
