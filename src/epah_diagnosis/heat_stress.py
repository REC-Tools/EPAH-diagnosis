from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from epah_diagnosis.cooling import (
    geometry_contains_point,
    geometry_reference_point,
)


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


def classify_daily_max_utci(value_c: float) -> tuple[bool, bool, bool]:
    return (
        value_c >= STRONG_HEAT_STRESS_C,
        value_c >= VERY_STRONG_HEAT_STRESS_C,
        value_c > EXTREME_HEAT_STRESS_C,
    )


def _normalize_longitude(value: float) -> float:
    return value - 360.0 if value > 180.0 else value


def _to_celsius(value: float) -> float:
    # ERA5-HEAT UTCI is conventionally stored in kelvin.
    return value - 273.15 if value > 150 else value


def compute_municipal_heat_stress_from_netcdf(
    netcdf_path: Path,
    geojson_path: Path,
    reference_year: int,
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
        latitudes = [float(value) for value in dataset[lat_name].values]
        raw_longitudes = [float(value) for value in dataset[lon_name].values]
        longitudes = [_normalize_longitude(value) for value in raw_longitudes]

        results: list[HeatStressResult] = []

        for feature in geo["features"]:
            municipality = feature["properties"]["municipality"]
            geometry = feature["geometry"]

            selected: list[tuple[int, int]] = []
            for lat_idx, lat in enumerate(latitudes):
                for lon_idx, lon in enumerate(longitudes):
                    if geometry_contains_point(geometry, lon, lat):
                        selected.append((lat_idx, lon_idx))

            if not selected:
                ref_lon, ref_lat = geometry_reference_point(geometry)
                nearest = min(
                    (
                        (
                            (lat - ref_lat) ** 2 + (lon - ref_lon) ** 2,
                            lat_idx,
                            lon_idx,
                        )
                        for lat_idx, lat in enumerate(latitudes)
                        for lon_idx, lon in enumerate(longitudes)
                    ),
                    key=lambda item: item[0],
                )
                selected = [(nearest[1], nearest[2])]

            daily_maxima: dict[str, float] = {}

            for time_idx in range(int(dataset.sizes[time_name])):
                raw_time = dataset[time_name].values[time_idx]
                timestamp = str(raw_time)
                day = timestamp[:10]
                if not day.startswith(str(reference_year)):
                    continue

                cell_values = []
                for lat_idx, lon_idx in selected:
                    raw_value = float(
                        values.isel(
                            {
                                time_name: time_idx,
                                lat_name: lat_idx,
                                lon_name: lon_idx,
                            }
                        ).values
                    )
                    if math.isfinite(raw_value):
                        cell_values.append(_to_celsius(raw_value))

                if not cell_values:
                    continue

                municipal_hourly = sum(cell_values) / len(cell_values)
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
                )
            )

        return sorted(results, key=lambda item: item.municipality)
    finally:
        dataset.close()
