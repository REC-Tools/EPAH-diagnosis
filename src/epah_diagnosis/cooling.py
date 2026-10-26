from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path


CDD_TRIGGER_C = 24.0
CDD_REFERENCE_C = 21.0


@dataclass(frozen=True)
class CoolingDegreeDayResult:
    municipality: str
    cdd: float
    grid_cells: int
    reference_year: int


def daily_cdd(mean_temperature_c: float) -> float:
    if mean_temperature_c >= CDD_TRIGGER_C:
        return mean_temperature_c - CDD_REFERENCE_C
    return 0.0


def annual_cdd(mean_temperatures_c: list[float]) -> float:
    return round(sum(daily_cdd(value) for value in mean_temperatures_c), 2)


def _ring_contains_point(ring: list[list[float]], lon: float, lat: float) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][:2]
        xj, yj = ring[j][:2]

        intersects = (
            (yi > lat) != (yj > lat)
            and lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-15) + xi
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def geometry_contains_point(geometry: dict, lon: float, lat: float) -> bool:
    geometry_type = geometry["type"]
    coordinates = geometry["coordinates"]

    polygons = coordinates if geometry_type == "MultiPolygon" else [coordinates]
    if geometry_type not in {"Polygon", "MultiPolygon"}:
        raise ValueError(f"Unsupported geometry type: {geometry_type}")

    for polygon in polygons:
        if not polygon:
            continue
        exterior = polygon[0]
        if not _ring_contains_point(exterior, lon, lat):
            continue

        holes = polygon[1:]
        if any(_ring_contains_point(hole, lon, lat) for hole in holes):
            continue
        return True

    return False


def geometry_reference_point(geometry: dict) -> tuple[float, float]:
    coordinates = geometry["coordinates"]
    polygons = coordinates if geometry["type"] == "MultiPolygon" else [coordinates]

    points: list[tuple[float, float]] = []
    for polygon in polygons:
        if not polygon:
            continue
        for point in polygon[0]:
            points.append((float(point[0]), float(point[1])))

    if not points:
        raise ValueError("Geometry has no exterior-ring coordinates.")

    lon = sum(point[0] for point in points) / len(points)
    lat = sum(point[1] for point in points) / len(points)
    return lon, lat


def bounding_box_from_geojson(path: Path, padding: float = 0.2) -> tuple[float, float, float, float]:
    data = json.loads(path.read_text(encoding="utf-8"))

    points: list[tuple[float, float]] = []
    for feature in data["features"]:
        geometry = feature["geometry"]
        coordinates = geometry["coordinates"]
        polygons = coordinates if geometry["type"] == "MultiPolygon" else [coordinates]
        for polygon in polygons:
            for ring in polygon:
                for point in ring:
                    points.append((float(point[0]), float(point[1])))

    if not points:
        raise ValueError("No coordinates found in municipality GeoJSON.")

    west = min(point[0] for point in points) - padding
    east = max(point[0] for point in points) + padding
    south = min(point[1] for point in points) - padding
    north = max(point[1] for point in points) + padding
    return north, west, south, east


def _normalize_longitude(value: float) -> float:
    return value - 360.0 if value > 180.0 else value


def compute_municipal_cdd_from_netcdf(
    netcdf_path: Path,
    geojson_path: Path,
    reference_year: int,
) -> list[CoolingDegreeDayResult]:
    try:
        import xarray as xr
    except ImportError as exc:
        raise RuntimeError(
            "xarray is required to process ERA5-Land NetCDF data. "
            "Install project dependencies with: pip install -e ."
        ) from exc

    data = json.loads(geojson_path.read_text(encoding="utf-8"))
    dataset = xr.open_dataset(netcdf_path)

    try:
        variable_name = next(
            (
                name
                for name in ("t2m", "2m_temperature")
                if name in dataset.data_vars
            ),
            None,
        )
        if variable_name is None:
            raise ValueError(
                "ERA5-Land temperature variable not found. "
                f"Available variables: {list(dataset.data_vars)}"
            )

        lat_name = "latitude" if "latitude" in dataset.coords else "lat"
        lon_name = "longitude" if "longitude" in dataset.coords else "lon"
        time_name = "valid_time" if "valid_time" in dataset.coords else "time"

        temperatures = dataset[variable_name]
        latitudes = [float(value) for value in dataset[lat_name].values]
        raw_longitudes = [float(value) for value in dataset[lon_name].values]
        longitudes = [_normalize_longitude(value) for value in raw_longitudes]

        results: list[CoolingDegreeDayResult] = []

        for feature in data["features"]:
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

            daily_means_c: list[float] = []
            for time_idx in range(int(dataset.sizes[time_name])):
                cell_values = []
                for lat_idx, lon_idx in selected:
                    value_k = float(
                        temperatures.isel(
                            {
                                time_name: time_idx,
                                lat_name: lat_idx,
                                lon_name: lon_idx,
                            }
                        ).values
                    )
                    if math.isfinite(value_k):
                        cell_values.append(value_k - 273.15)

                if cell_values:
                    daily_means_c.append(sum(cell_values) / len(cell_values))

            if not daily_means_c:
                raise ValueError(
                    f"No usable ERA5-Land daily temperatures for {municipality}."
                )

            results.append(
                CoolingDegreeDayResult(
                    municipality=municipality,
                    cdd=annual_cdd(daily_means_c),
                    grid_cells=len(selected),
                    reference_year=reference_year,
                )
            )

        return sorted(results, key=lambda item: item.municipality)
    finally:
        dataset.close()
