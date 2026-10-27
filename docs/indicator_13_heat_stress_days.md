# Indicator 13 - Heat Stress Days

## EPAH alignment

The 2026 EPAH indicator framework introduces **Heat stress days** as a climate
indicator relevant to summer energy poverty.

The indicator uses the Universal Thermal Climate Index (UTCI) from the
Copernicus ERA5-HEAT dataset. UTCI represents a human thermal-response
"feels-like" temperature combining air temperature, humidity, wind and
radiation.

## Categories

Copernicus UTCI categories used by EPAH:

- moderate heat stress: 26 C to <32 C
- strong heat stress: 32 C to <38 C
- very strong heat stress: 38 C to <=46 C
- extreme heat stress: >46 C

The project uses as its **primary municipal indicator**:

**number of days with daily maximum UTCI >=32 C**

It also retains:
- days with UTCI >=38 C;
- days with UTCI >46 C;
- maximum daily UTCI.

## Source

Copernicus Climate Change Service:
**Thermal comfort indices derived from ERA5 reanalysis (ERA5-HEAT)**.

The dataset has a 0.25 degree regular latitude-longitude grid and hourly
temporal resolution, with additional daily/monthly/seasonal/yearly
statistics.

Reference year: **2025**, the latest complete calendar year used consistently
with the initial Cooling Degree Days implementation.

## Municipal aggregation

For each municipality:
1. select ERA5-HEAT grid-cell centres falling inside the ISTAT 2026 municipal
   polygon;
2. compute the municipality-average UTCI for each hourly timestamp;
3. compute the maximum municipal UTCI for each day;
4. count days crossing the UTCI thresholds.

For municipalities containing no grid-cell centre, the nearest grid cell is
used as a fallback.

## Pipeline

Download:

`python scripts/download_era5_heat_utci.py`

Finalize:

`python scripts/finalize_heat_stress_days.py`

Outputs:
- `data/raw/era5_heat_utci_2025.nc`
- `data/indicators/heat_stress_days_2025.csv`
- `data/indicators/heat_stress_days_summary_2025.csv`
- 27 validated rows in the verification matrix.

## Limitations

Heat stress days are an outdoor climate-exposure indicator. They do not measure:
- indoor thermal comfort;
- access to air conditioning;
- ability to afford cooling;
- dwelling insulation or passive cooling;
- individual health outcomes.

The indicator should therefore be cross-read with:
- population aged 65+;
- building energy performance;
- old building stock;
- Cooling Degree Days;
- future direct summer comfort and cooling-affordability indicators.
