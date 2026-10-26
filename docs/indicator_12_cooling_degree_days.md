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

## Setup

Copernicus CDS requires:
1. a CDS account;
2. acceptance of the dataset terms;
3. a personal access token configured in `~/.cdsapirc`.

Install dependencies:

`pip install -e .`

Download:

`python scripts/download_era5_land_daily_temperature.py`

Finalize:

`python scripts/finalize_cooling_degree_days.py`

## Outputs

- `data/raw/era5_land_daily_mean_temperature_2025.nc`
- `data/indicators/cooling_degree_days_2025.csv`
- `data/indicators/cooling_degree_days_summary_2025.csv`
- 27 validated verification-matrix rows.

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
