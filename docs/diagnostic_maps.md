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


## PR-08: complete set of nine maps and cartographic QA

The canonical maps are now generated in one staged bundle with
`python scripts/build_v0_1_bundle.py`, after input QA and verified ISTAT
boundaries are available. The eight numeric maps are population 65+, low
income, pre-1981 residential buildings, heating degree days, mean altitude,
road access to DEA I/II, access to complete upper-secondary school poles,
and active passenger-rail gateways. **SNAI 2020 A–F is a ninth categorical
map**, not a continuous scale.

Cartographic safeguards include strict code join to the canonical 27
six-digit ISTAT municipality identifiers, rejection of missing/duplicated
or invalid boundaries, Polygon/MultiPolygon validation, checks for valid
latitude/longitude and explicit support for polygon holes. Every map is
labelled as aggregated screening data. The measure of service accessibility
uses municipal reference-point road times, not actual home-to-service
routes or public transport. Publication remains blocked until human
source/methodological reviews are complete.
