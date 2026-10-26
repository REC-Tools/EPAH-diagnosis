# Diagnostic maps

This stage joins the validated municipal indicator profile with the official
ISTAT 2026 municipal boundaries.

## 1. Build enriched GeoJSON

Run:

`python scripts/build_municipality_geojson.py`

Input:
- `data/geography/municipalities_2026.geojson`
- `data/derived/municipality_profile.csv`

Output:
- `data/derived/municipality_profile.geojson`

Each municipal feature contains the three baseline indicators:
- population aged 65+ (%)
- taxpayers with declared income <= EUR 15,000 (%)
- residential buildings built before 1981 (%)

## 2. Generate maps

Run:

`python scripts/generate_diagnostic_maps.py`

Outputs:
- `outputs/maps/map_population_65_plus.png`
- `outputs/maps/map_income_vulnerability.png`
- `outputs/maps/map_old_building_stock.png`

These maps deliberately keep the three dimensions separate. No composite
energy-poverty score is generated at this stage.
