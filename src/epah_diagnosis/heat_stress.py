from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from epah_diagnosis.cooling import (
    select_grid_cells,
)
from epah_diagnosis.climate_inputs import annual_time_indices, municipal_mean, temperature_offset


STRONG_HEAT_STRESS_C = 32.0
VERY_STRONG_HEAT_STRESS_C = 38.0
EXTREME_HEAT_STRESS_C = 46.0


@dataclass(frozen=True)
class HeatStressResult:
    municipality: str
    strong_days: int
    very_strong_days: int
    extreme_days: int
    max_utci_c: float
    grid_cells: int
    reference_year: int
    fallback_distance_km: float = 0.0


def classify_daily_max_utci(value_c: float) -> tuple[bool, bool, bool]:
    if not math.isfinite(value_c):
        raise ValueError("UTCI classification requires a finite temperature")
    return (
        value_c >= STRONG_HEAT_STRESS_C,
        value_c >= VERY_STRONG_HEAT_STRESS_C,
        value_c > EXTREME_HEAT_STRESS_C,
    )


def _normalize_longitude(value: float) -> float:
    return value - 360.0 if value > 180.0 else value


def compute_municipal_heat_stress_from_netcdf(
    netcdf_path: Path,
    geojson_path: Path,
    reference_year: int,
    *, max_fallback_km: float = 30.0,
) -> list[HeatStressResult]:
    try:
        import xarray as xr
    except ImportError as exc:
        raise RuntimeError(
            "xarray is required to process ERA5-HEAT NetCDF data. "
            "Install project dependencies with: pip install -e ."
        ) from exc

    geo = json.loads(geojson_path.read_text(encoding="utf-8"))
    dataset = xr.open_dataset(netcdf_path)

    try:
        variable_name = next(
            (
                name
                for name in (
                    "utci",
                    "universal_thermal_climate_index",
                )
                if name in dataset.data_vars
            ),
            None,
        )
        if variable_name is None:
            raise ValueError(
                "ERA5-HEAT UTCI variable not found. Available variables: "
                f"{list(dataset.data_vars)}"
            )

        lat_name = "latitude" if "latitude" in dataset.coords else "lat"
        lon_name = "longitude" if "longitude" in dataset.coords else "lon"
        time_name = "valid_time" if "valid_time" in dataset.coords else "time"

        values = dataset[variable_name]
        if set(values.dims) != {time_name, lat_name, lon_name}:
            raise ValueError("UTCI variable requires exactly time, latitude and longitude dimensions")
        time_indices = annual_time_indices(dataset, time_name, reference_year, hourly=True)
        offset = temperature_offset(values.attrs.get("units"))
        latitudes = [float(value) for value in dataset[lat_name].values]
        raw_longitudes = [float(value) for value in dataset[lon_name].values]
        longitudes = [_normalize_longitude(value) for value in raw_longitudes]

        results: list[HeatStressResult] = []

        for feature in geo["features"]:
            municipality = feature["properties"]["municipality"]
            geometry = feature["geometry"]

            selected, fallback_km = select_grid_cells(geometry, latitudes, longitudes, max_fallback_km)

            daily_maxima: dict[str, float] = {}
            hourly_values = municipal_mean(values, time_name, lat_name, lon_name,
                                           time_indices, selected, offset, municipality)
            timestamps = dataset[time_name].values
            for time_idx, municipal_hourly in zip(time_indices, hourly_values):
                day = str(timestamps[time_idx])[:10]
                previous = daily_maxima.get(day)
                if previous is None or municipal_hourly > previous:
                    daily_maxima[day] = municipal_hourly

            if not daily_maxima:
                raise ValueError(
                    f"No usable ERA5-HEAT UTCI observations for {municipality}."
                )

            strong = 0
            very_strong = 0
            extreme = 0

            for value_c in daily_maxima.values():
                is_strong, is_very_strong, is_extreme = classify_daily_max_utci(
                    value_c
                )
                strong += int(is_strong)
                very_strong += int(is_very_strong)
                extreme += int(is_extreme)

            results.append(
                HeatStressResult(
                    municipality=municipality,
                    strong_days=strong,
                    very_strong_days=very_strong,
                    extreme_days=extreme,
                    max_utci_c=max(daily_maxima.values()),
                    grid_cells=len(selected),
                    reference_year=reference_year,
                    fallback_distance_km=fallback_km,
                )
            )

        return sorted(results, key=lambda item: item.municipality)
    finally:
        dataset.close()
