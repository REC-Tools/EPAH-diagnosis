# Municipality comparison table

The integrated profile can be transformed into a transparent comparison table
for the 27 municipalities.

Run:

```
python scripts/build_municipality_comparison.py
```

Output:

`data/derived/municipality_comparison.csv`

For each numerical dimension the table contains:
- the original indicator value;
- a rank from 1 to 27, where 1 means the highest observed value among the
  Green Community municipalities.

Dimensions:
- population aged 65 and over;
- low-income taxpayer proxy;
- pre-1981 residential building stock;
- heating degree days;
- mean altitude;
- road time to DEA I/II;
- road time to complete upper-secondary education pole;
- road time to active passenger rail gateway.

The SNAI class is retained as a categorical field.

## Interpretation

Ranks are descriptive comparisons only. A high rank in one dimension does not
mean that the municipality is energy poor, and ranks from different dimensions
must not be summed as if they formed an official energy-poverty index.

The table is intended to support transparent screening and discussion before
more direct energy-affordability and consumption indicators are added.
