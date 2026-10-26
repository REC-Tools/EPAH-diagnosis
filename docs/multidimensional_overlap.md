# Multidimensional overlap classification

This stage adds a transparent territorial overlap classification to the three
baseline indicators.

For each municipality, each indicator is compared with its **weighted Green
Community benchmark** produced by the corresponding indicator pipeline.

The output records:

- the Green Community benchmark for each indicator;
- the municipal difference in percentage points;
- whether the municipality is above the benchmark;
- a count from 0 to 3 of dimensions above benchmark;
- the names of the dimensions that are above benchmark.

The overlap count is **not an energy-poverty score** and is not interpreted as
the number or share of energy-poor households. It is a descriptive screening
tool showing where several territorial vulnerability signals coexist.

Run:

`python scripts/build_multidimensional_overlap.py`

Then:

`python scripts/generate_overlap_map.py`

Outputs:

- `data/derived/municipality_overlap.geojson`
- `outputs/maps/map_multidimensional_overlap.png`
