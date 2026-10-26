# Municipal profile dataset

`scripts/build_municipality_profile.py` creates the first integrated municipal
baseline for the 27 Green Community municipalities.

The script reads `data/verification_matrix.csv` and requires all three baseline
indicators to be marked **Dato validato**:

1. `population_65_plus`
2. `income_vulnerability`
3. `old_building_stock`

It writes:

`data/derived/municipality_profile.csv`

No composite energy-poverty score is produced at this stage. The output keeps
the three dimensions separate so that later maps and comparisons remain
transparent and interpretable.

The script intentionally fails if even one municipality is missing a validated
indicator. This makes the integrated dataset a quality gate rather than a
best-effort merge.
