from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from epah_diagnosis.climate_inputs import annual_time_indices, municipal_mean, temperature_offset


CDD_TRIGGER_C = 24.0
CDD_REFERENCE_C = 21.0


@dataclass(frozen=True)
class CoolingDegreeDayResult:
    municipality: str
    cdd: float
    grid_cells: int
    reference_year: int
    fallback_distance_km: float = 0.0


def daily_cdd(mean_temperature_c: float) -> float:
    if not math.isfinite(mean_temperature_c):
        raise ValueError("CDD requires finite daily temperatures")
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


def select_grid_cells(geometry: dict, latitudes: list[float], longitudes: list[float],
                      max_fallback_km: float) -> tuple[list[tuple[int, int]], float]:
    """Select polygon cells or a bounded geodesic fallback to its reference point."""
    from pyproj import Geod
    from epah_diagnosis.cartography import _polygons

    list(_polygons(geometry))  # Validate closed, finite WGS84 rings before selection.
    if (not math.isfinite(max_fallback_km) or max_fallback_km < 0
            or not latitudes or not longitudes
            or len(set(latitudes)) != len(latitudes) or len(set(longitudes)) != len(longitudes)
            or any(not math.isfinite(v) or abs(v) > 90 for v in latitudes)
            or any(not math.isfinite(v) or abs(v) > 180 for v in longitudes)):
        raise ValueError("Invalid geographic grid coordinates or fallback distance")
    selected = [(i, j) for i, lat in enumerate(latitudes)
                for j, lon in enumerate(longitudes) if geometry_contains_point(geometry, lon, lat)]
    if selected:
        return selected, 0.0
    lon_ref, lat_ref = geometry_reference_point(geometry)
    geod = Geod(ellps="WGS84")
    distance, row, col = min((abs(geod.inv(lon_ref, lat_ref, lon, lat)[2]) / 1000, i, j)
                              for i, lat in enumerate(latitudes) for j, lon in enumerate(longitudes))
    if distance > max_fallback_km:
        raise ValueError(f"Nearest grid cell is {distance:.2f} km from the geometry reference point; "
                         f"fallback limit is {max_fallback_km:g} km")
    return [(row, col)], distance


def compute_municipal_cdd_from_netcdf(
    netcdf_path: Path,
    geojson_path: Path,
    reference_year: int,
    *, max_fallback_km: float = 30.0,
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
        if set(temperatures.dims) != {time_name, lat_name, lon_name}:
            raise ValueError("Temperature variable requires exactly time, latitude and longitude dimensions")
        time_indices = annual_time_indices(dataset, time_name, reference_year)
        offset = temperature_offset(temperatures.attrs.get("units"))
        latitudes = [float(value) for value in dataset[lat_name].values]
        raw_longitudes = [float(value) for value in dataset[lon_name].values]
        longitudes = [_normalize_longitude(value) for value in raw_longitudes]

        results: list[CoolingDegreeDayResult] = []

        for feature in data["features"]:
            municipality = feature["properties"]["municipality"]
            geometry = feature["geometry"]

            selected, fallback_km = select_grid_cells(geometry, latitudes, longitudes, max_fallback_km)

            daily_means_c = municipal_mean(temperatures, time_name, lat_name, lon_name,
                                           time_indices, selected, offset, municipality)

            results.append(
                CoolingDegreeDayResult(
                    municipality=municipality,
                    cdd=annual_cdd(daily_means_c),
                    grid_cells=len(selected),
                    reference_year=reference_year,
                    fallback_distance_km=fallback_km,
                )
            )

        return sorted(results, key=lambda item: item.municipality)
    finally:
        dataset.close()
