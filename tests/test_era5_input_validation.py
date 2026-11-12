"""Full-year synthetic ERA5 input regressions; no external data or downloads."""
import json

import numpy as np
import pandas as pd
import pytest
import xarray as xr

from epah_diagnosis.cooling import compute_municipal_cdd_from_netcdf, daily_cdd
from epah_diagnosis.heat_stress import compute_municipal_heat_stress_from_netcdf


def inputs(tmp_path, *, heat=False, year=2025, units="K", kind="complete", longitude=7.2):
    times = pd.date_range(f"{year}-01-01", f"{year + 1}-01-01",
                          freq="h" if heat else "D", inclusive="left")
    if kind == "missing":
        times = times.delete(12)
    elif kind == "duplicate":
        times = times[:-1].append(pd.DatetimeIndex([times[-2]]))
    elif kind == "wrong_year":
        times = pd.DatetimeIndex(["2024-01-01"])
    temperature = 38.0 if heat else 26.0
    data = np.full((len(times), 1, 1), temperature + (273.15 if units == "K" else 0))
    if kind == "nan":
        data[12, 0, 0] = np.nan
    nc = tmp_path / "source.nc"
    variable = "utci" if heat else "t2m"
    xr.Dataset({variable: (("time", "latitude", "longitude"), data, {"units": units})},
               coords={"time": times, "latitude": [45.2], "longitude": [longitude]}).to_netcdf(nc)
    geo = tmp_path / "geo.json"
    geo.write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"municipality": "Synthetic"}, "geometry": {
            "type": "Polygon", "coordinates": [[[7.1,45.1],[7.3,45.1],[7.3,45.3],[7.1,45.3],[7.1,45.1]]]}}
    ]}))
    return nc, geo


@pytest.mark.parametrize("year,days", [(2025,365), (2024,366)])
@pytest.mark.parametrize("units", ["K", "degrees_Celsius"])
def test_complete_cdd_calendar_and_explicit_units(tmp_path, year, days, units):
    nc, geo = inputs(tmp_path, year=year, units=units)
    result = compute_municipal_cdd_from_netcdf(nc, geo, year)[0]
    assert result.cdd == days * 5
    assert result.reference_year == year
    assert result.fallback_distance_km == 0


@pytest.mark.parametrize("heat", [False, True])
@pytest.mark.parametrize("kind", ["wrong_year", "missing", "duplicate", "nan"])
def test_invalid_annual_evidence_is_rejected(tmp_path, heat, kind):
    nc, geo = inputs(tmp_path, heat=heat, kind=kind)
    compute = compute_municipal_heat_stress_from_netcdf if heat else compute_municipal_cdd_from_netcdf
    with pytest.raises(ValueError, match="calendar|Duplicate|nonfinite"):
        compute(nc, geo, 2025)


@pytest.mark.parametrize("heat", [False, True])
@pytest.mark.parametrize("units", ["", "unknown"])
def test_missing_or_unknown_units_are_not_guessed(tmp_path, heat, units):
    nc, geo = inputs(tmp_path, heat=heat, units=units)
    compute = compute_municipal_heat_stress_from_netcdf if heat else compute_municipal_cdd_from_netcdf
    with pytest.raises(ValueError, match="temperature units"):
        compute(nc, geo, 2025)


def test_utci_counts_daily_maxima_after_complete_hourly_validation(tmp_path):
    nc, geo = inputs(tmp_path, heat=True, units="degrees_Celsius")
    result = compute_municipal_heat_stress_from_netcdf(nc, geo, 2025)[0]
    assert result.strong_days == 365
    assert result.very_strong_days == 365
    assert result.extreme_days == 0
    assert result.max_utci_c == 38


def test_daily_utci_cannot_be_mistaken_for_complete_hourly_coverage(tmp_path):
    nc, geo = inputs(tmp_path)
    with xr.open_dataset(nc) as source:
        dataset = source.rename({"t2m": "utci"}).load()
    dataset.to_netcdf(nc, mode="w")
    with pytest.raises(ValueError, match="hourly calendar"):
        compute_municipal_heat_stress_from_netcdf(nc, geo, 2025)


def test_grid_fallback_is_bounded_and_reported(tmp_path):
    nc, geo = inputs(tmp_path, longitude=7.5)
    result = compute_municipal_cdd_from_netcdf(nc, geo, 2025)[0]
    assert 0 < result.fallback_distance_km < 30
    with pytest.raises(ValueError, match="fallback limit"):
        compute_municipal_cdd_from_netcdf(nc, geo, 2025, max_fallback_km=1)


def test_grid_on_other_side_of_world_cannot_be_a_municipal_fallback(tmp_path):
    nc, geo = inputs(tmp_path, longitude=120)
    with pytest.raises(ValueError, match="fallback limit"):
        compute_municipal_cdd_from_netcdf(nc, geo, 2025)


def test_nan_is_not_zero_cooling_demand():
    with pytest.raises(ValueError, match="finite"):
        daily_cdd(float("nan"))
