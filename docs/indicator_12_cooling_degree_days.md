# Indicator 12 - Cooling Degree Days

## EPAH alignment

EPAH includes Cooling Degree Days (CDD) as a climate indicator of the
climate-driven energy requirement for cooling. It should be cross-read with
building efficiency, affordability, cooling equipment and thermal-comfort
indicators.

## Method

The project follows the Eurostat/JRC climatological convention:

- if daily mean outdoor temperature is below 24 C: daily CDD = 0;
- if daily mean outdoor temperature is at least 24 C:
  daily CDD = Tmean - 21 C.

Daily values are summed for the calendar year.

Reference year for the first local implementation: **2025**, the latest complete
calendar year at implementation time.

## Source

Copernicus Climate Change Service, ERA5-Land post-processed daily statistics,
2 m air temperature, daily mean.

ERA5-Land provides a gridded reanalysis. For each municipality, the project
uses the daily mean across ERA5-Land grid-cell centres falling within the
official ISTAT 2026 municipality polygon. If a municipality contains no grid
cell centre because it is smaller than the grid resolution, the nearest grid
cell to a geometry reference point is used.

The ERA5 reader now requires explicit Kelvin/Celsius units and a complete,
unique Gregorian daily calendar for the selected year (including leap days).
Daily coordinates must represent midnight dates; hourly inputs are not daily
means. Missing or non-finite observations in any selected cell block the
calculation instead of changing the spatial denominator or shortening the year.
Other complete years in the same file are excluded. A nearest-cell fallback
is limited to 30 km from the geometry reference point by default, configurable
through `max_fallback_km`; its actual distance is retained in the result.
This limit is a technical guard, not proof of mountain-climate representativeness.

## Setup

Copernicus CDS requires:
1. a CDS account;
2. acceptance of the dataset terms;
3. a personal access token configured in `~/.cdsapirc`.

Install dependencies:

`pip install -e .`

Download:

`python scripts/download_era5_land_daily_temperature.py`

Create a technical preview (the historical finalizer name no longer promotes data):

```bash
uv run --locked python scripts/finalize_cooling_degree_days.py \
  --input data/raw/era5_land_daily_mean_temperature_2025.nc \
  --reference-year 2025 --out-dir outputs/quality/era5-cdd-review-01
```

## Outputs

The source NetCDF remains in its original location. A fresh output directory
contains `preview.csv` (27 rows, reference year and fallback distances),
`qa.json`, a SHA-256 `manifest.json` and review instructions. Status remains
`technical_draft_do_not_publish`. No canonical matrix rows are written and
no methodological approval is inferred. The destination must be separate
from input/evidence directories and outside protected source/data directories.

## Limitations

CDD is not a direct energy-poverty measure. It does not represent:
- actual air-conditioning ownership;
- cooling-system efficiency;
- electricity consumption or expenditure;
- affordability of cooling;
- indoor temperature or thermal comfort;
- short-duration heat-wave severity.

It should be interpreted alongside age, dwelling efficiency and future direct
summer thermal-comfort / affordability indicators.
