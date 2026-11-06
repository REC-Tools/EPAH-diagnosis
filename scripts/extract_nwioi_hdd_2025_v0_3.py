"""Extract an H03 technical preview from original ARPA NWIOI NetCDF files.

Offline only. Requires official masked grid and ISTAT municipal polygons. Does not
modify canonical indicator data and never asserts scientific approval.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import xarray as xr

from epah_diagnosis.cooling import geometry_contains_point
from prepare_hdd_eurostat_2025_v0_3 import (
    REQUIRED, STATUS, aggregate, dates_in_year, digest, normalize_name,
    read_registry, write_outputs,
)

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / 'data/municipalities.csv'
GEOJSON = ROOT / 'data/geography/municipalities_2026.geojson'
YEAR = 2025
OUTPUT_CSV = 'nwioi_2025_municipal_daily.csv'
OUTPUT_QA = 'extraction_qa.json'
TEMPERATURE_ALIASES = {'latitude': ('latitude', 'lat'),
                       'longitude': ('longitude', 'lon'),
                       'time': ('time', 'valid_time')}
COLUMNS = REQUIRED


@dataclass(frozen=True)
class Grid:
    lat_name: str
    lon_name: str
    latitudes: np.ndarray
    longitudes: np.ndarray


@dataclass(frozen=True)
class Cell:
    row: int
    column: int
    latitude: float
    longitude: float

    @property
    def cell_id(self) -> str:
        return f'NWIOI:i{self.row:03d}:j{self.column:03d}'


def _axis(ds: xr.Dataset, kind: str) -> str:
    found = [key for key in TEMPERATURE_ALIASES[kind] if key in ds.coords]
    if len(found) != 1:
        raise ValueError(f'Expected exactly one {kind} coordinate; found {found}')
    key = found[0]
    if ds[key].ndim != 1 or ds[key].dims != (key,):
        raise ValueError(f'Coordinate {key!r} must be a 1D coordinate/dimension')
    return key


def grid_of(ds: xr.Dataset) -> Grid:
    lat_name, lon_name = _axis(ds, 'latitude'), _axis(ds, 'longitude')
    lat = np.asarray(ds[lat_name].values, dtype=float)
    lon = np.asarray(ds[lon_name].values, dtype=float)
    if not len(lat) or not len(lon) or not np.all(np.isfinite(lat)) or not np.all(np.isfinite(lon)):
        raise ValueError('Grid coordinates must be finite and non-empty')
    if len(np.unique(lat)) != len(lat) or len(np.unique(lon)) != len(lon):
        raise ValueError('Duplicate grid coordinate')
    if not (np.all(np.diff(lat) > 0) or np.all(np.diff(lat) < 0)):
        raise ValueError('Latitude coordinate must be strictly monotone')
    if not (np.all(np.diff(lon) > 0) or np.all(np.diff(lon) < 0)):
        raise ValueError('Longitude coordinate must be strictly monotone')
    normalized_lon = np.where(lon > 180.0, lon - 360.0, lon)
    if np.any(np.abs(lat) > 90) or np.any(np.abs(normalized_lon) > 180):
        raise ValueError('Coordinates are not geographic WGS84 degrees')
    return Grid(lat_name, lon_name, lat, normalized_lon)


def _same_grid(a: Grid, b: Grid) -> None:
    for kind, first, second in [('latitude', a.latitudes, b.latitudes),
                                ('longitude', a.longitudes, b.longitudes)]:
        if len(first) != len(second) or not np.allclose(first, second, atol=1e-8, rtol=0):
            raise ValueError(f'Temperature and mask {kind} grids are not aligned')


def _variable(ds: xr.Dataset, explicit: str | None, dimensions: set[str], kind: str) -> str:
    if explicit is not None:
        if explicit not in ds.data_vars:
            raise ValueError(f'Unknown {kind} variable {explicit!r}; available {list(ds.data_vars)}')
        candidates = [explicit]
    else:
        candidates = [key for key, val in ds.data_vars.items() if set(val.dims) == dimensions]
    if len(candidates) != 1:
        raise ValueError(f'Ambiguous {kind} variable: {candidates}; supply --{kind}-variable')
    name = candidates[0]
    if set(ds[name].dims) != dimensions:
        raise ValueError(f'{kind} variable has unsupported dimensions {ds[name].dims}')
    if not np.issubdtype(ds[name].dtype, np.number):
        raise ValueError(f'{kind} variable must be numeric')
    return name


def _temperature_units(ds: xr.Dataset, var: str) -> tuple[str, float]:
    raw = str(ds[var].attrs.get('units', '')).strip().casefold().replace(' ', '')
    celsius = {'c', 'degc', 'degree_celsius', 'degrees_celsius', 'degreecelsius',
               'degreescelsius', 'celsius', '°c', 'degrees_c', 'degree_c'}
    kelvin = {'k', 'kelvin', 'degrees_kelvin', 'degree_kelvin'}
    if raw in celsius:
        return raw, 0.0
    if raw in kelvin:
        return raw, -273.15
    raise ValueError(f'Temperature variable {var!r}: unknown units {raw!r}; refusing to guess')


def _year_indices(ds: xr.Dataset, time_axis: str, year: int) -> tuple[list[int], list[str]]:
    try:
        timestamps = np.asarray(ds[time_axis].dt.strftime('%Y-%m-%d').values)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError('Expected a CF-decoded daily Gregorian time coordinate') from exc
    expected = dates_in_year(year)
    found: dict[str, int] = {}
    for i, text in enumerate(timestamps):
        stamp = str(text)
        if stamp.startswith(f'{year}-'):
            if stamp in found:
                raise ValueError(f'Duplicate source date {stamp}')
            found[stamp] = i
    if set(found) != set(expected):
        missing = sorted(set(expected) - set(found))
        extra = sorted(set(found) - set(expected))
        raise ValueError(f'Incomplete year {year}: missing={missing[:5]}, extra={extra[:5]}')
    return [found[day] for day in expected], expected


def _mask(ds: xr.Dataset, grid: Grid, variable: str | None) -> tuple[str, np.ndarray]:
    name = _variable(ds, variable, {grid.lat_name, grid.lon_name}, 'mask')
    a = np.asarray(ds[name].transpose(grid.lat_name, grid.lon_name).values, dtype=float)
    if not np.all(np.isfinite(a)) or not np.all(np.isin(a, [0, 1])):
        raise ValueError('ARPA region mask must contain only explicit 0 and 1; no missing cells')
    if not np.any(a == 1):
        raise ValueError('ARPA region mask has no valid Piemonte grid cell')
    return name, a == 1


def _validate_geometries(path: Path, registry: dict[str, str]) -> dict[str, dict]:
    source = json.loads(path.read_text(encoding='utf-8'))
    if source.get('type') != 'FeatureCollection':
        raise ValueError('Official ISTAT boundaries require a GeoJSON FeatureCollection')
    crs = source.get('crs')
    if crs and crs.get('properties', {}).get('name') not in (
        'urn:ogc:def:crs:OGC:1.3:CRS84', 'EPSG:4326', 'OGC:CRS84'
    ):
        raise ValueError('Municipal geometry is not CRS84 / WGS84 degrees')
    features: dict[str, dict] = {}
    for f in source.get('features', []):
        p = f.get('properties') or {}
        code, name = str(p.get('municipality_code', '')), str(p.get('municipality', ''))
        if code not in registry or code in features or normalize_name(name) != normalize_name(registry.get(code, '')):
            raise ValueError(f'Unexpected, duplicated or inconsistent ISTAT geometry {code!r}')
        if str(p.get('boundary_year')) != '2026':
            raise ValueError(f'Municipal ISTAT geometry {code} requires boundary_year=2026')
        geometry = f.get('geometry') or {}
        if geometry.get('type') not in {'Polygon', 'MultiPolygon'}:
            raise ValueError(f'Unsupported geometry for {code}')
        polygons = geometry.get('coordinates', [])
        polygons = [polygons] if geometry['type'] == 'Polygon' else polygons
        coords = []
        for polygon in polygons:
            if not polygon or len(polygon[0]) < 4:
                raise ValueError(f'Empty or invalid ring for {code}')
            for ring in polygon:
                for point in ring:
                    if not isinstance(point, (list, tuple)) or len(point) < 2:
                        raise ValueError(f'Invalid polygon coordinate for {code}')
                    lon, lat = float(point[0]), float(point[1])
                    if not all(map(math.isfinite, (lon, lat))) or not (6 <= lon <= 11 and 43 <= lat <= 47.5):
                        raise ValueError(f'Polygon outside Piemonte envelope for {code}')
                    coords.append((lon, lat))
        if not coords:
            raise ValueError(f'Empty geometry for {code}')
        features[code] = geometry
    if set(features) != set(registry):
        raise ValueError(f'Missing municipality polygons: {sorted(set(registry) - set(features))}')
    return features


def _vertex_reference(geometry: dict) -> tuple[float, float]:
    polygons = geometry['coordinates'] if geometry['type'] == 'MultiPolygon' else [geometry['coordinates']]
    ring = max((p[0] for p in polygons if p), key=len)
    points = ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else ring
    return sum(v[0] for v in points) / len(points), sum(v[1] for v in points) / len(points)


def _distance_to_geometry_km(lon: float, lat: float, geometry: dict) -> float:
    """Approximate distance to polygon boundary for short (<30 km) fallbacks."""
    polygons = geometry['coordinates'] if geometry['type'] == 'MultiPolygon' else [geometry['coordinates']]
    factor = math.cos(math.radians(lat))
    nearest = float('inf')
    for polygon in polygons:
        for ring in polygon:
            for a, b in zip(ring, ring[1:]):
                ax, ay = (a[0] - lon) * 111.32 * factor, (a[1] - lat) * 111.32
                bx, by = (b[0] - lon) * 111.32 * factor, (b[1] - lat) * 111.32
                dx, dy = bx - ax, by - ay
                t = max(0.0, min(1.0, -(ax * dx + ay * dy) / (dx * dx + dy * dy))) if dx or dy else 0.0
                nearest = min(nearest, math.hypot(ax + t * dx, ay + t * dy))
    return nearest


def _assign_cells(geo: dict[str, dict], grid: Grid, valid_mask: np.ndarray,
                  max_fallback_km: float) -> tuple[dict[str, Cell], list[dict[str, object]]]:
    valid = [Cell(i, j, float(lat), float(lon))
             for i, lat in enumerate(grid.latitudes)
             for j, lon in enumerate(grid.longitudes) if valid_mask[i, j]]
    if not valid:
        raise ValueError('No ARPA masked grid cells available')
    assignments: dict[str, Cell] = {}
    qa: list[dict[str, object]] = []
    for code, geometry in sorted(geo.items()):
        ref_lon, ref_lat = _vertex_reference(geometry)
        inside = [c for c in valid if geometry_contains_point(geometry, c.longitude, c.latitude)]
        if inside:
            chosen = min(inside, key=lambda c: (
                (c.longitude - ref_lon) ** 2 * math.cos(math.radians(ref_lat)) ** 2
                + (c.latitude - ref_lat) ** 2, c.row, c.column))
            method, distance_km = 'masked_grid_center_inside_polygon', 0.0
        else:
            ranked = sorted((_distance_to_geometry_km(c.longitude, c.latitude, geometry), c.row, c.column, c)
                            for c in valid)
            distance_km, _, _, chosen = ranked[0]
            if distance_km > max_fallback_km:
                raise ValueError(f'{code}: nearest ARPA masked cell is {distance_km:.2f} km from polygon '
                                 f'(maximum {max_fallback_km:.2f} km)')
            method = 'nearest_masked_cell_to_polygon_boundary'
        assignments[code] = chosen
        qa.append({'municipality_code': code, 'grid_cell_id': chosen.cell_id,
                   'grid_latitude': round(chosen.latitude, 6),
                   'grid_longitude': round(chosen.longitude, 6),
                   'selection': method, 'boundary_distance_km_approx': round(distance_km, 3),
                   'matched_mask_value': 1})
    return assignments, qa


def _temperatures(ds: xr.Dataset, var: str, time: str, grid: Grid, indices: list[int],
                  cell: Cell, shift: float) -> np.ndarray:
    values = np.asarray(ds[var].isel({time: indices, grid.lat_name: cell.row,
                                      grid.lon_name: cell.column}).values, dtype=float)
    if values.shape != (len(indices),):
        raise ValueError(f'Temperature time series has wrong shape {values.shape}')
    values = values + shift
    if not np.all(np.isfinite(values)):
        raise ValueError(f'Temperature contains missing or non-finite values in {cell.cell_id}')
    if not np.all((-65 <= values) & (values <= 65)):
        raise ValueError(f'Temperature outside -65/+65 C in {cell.cell_id}')
    return values


def extract(tmin_path: Path, tmax_path: Path, mask_path: Path, boundaries_path: Path,
            registry_path: Path, year: int, *, tmin_variable: str | None = None,
            tmax_variable: str | None = None, mask_variable: str | None = None,
            max_fallback_km: float = 25.0) -> tuple[list[dict[str, str]], dict[str, object]]:
    """Return complete normalized daily records plus explicit source/geometry QA."""
    if not 0 < max_fallback_km <= 100 or not math.isfinite(max_fallback_km):
        raise ValueError('max_fallback_km must be finite and in (0,100]')
    expected_paths = (tmin_path, tmax_path, mask_path, boundaries_path, registry_path)
    if not all(p.is_file() for p in expected_paths) or len({p.resolve() for p in expected_paths}) != 5:
        raise ValueError('Five distinct, existing original input files are required')
    registry = read_registry(registry_path)
    geometries = _validate_geometries(boundaries_path, registry)
    with xr.open_dataset(tmin_path, decode_times=True, mask_and_scale=True) as tn, \
         xr.open_dataset(tmax_path, decode_times=True, mask_and_scale=True) as tx, \
         xr.open_dataset(mask_path, decode_times=True, mask_and_scale=False) as mk:
        tn_grid, tx_grid, mask_grid = grid_of(tn), grid_of(tx), grid_of(mk)
        _same_grid(tn_grid, tx_grid)
        _same_grid(tn_grid, mask_grid)
        tn_time, tx_time = _axis(tn, 'time'), _axis(tx, 'time')
        tn_var = _variable(tn, tmin_variable, {tn_time, tn_grid.lat_name, tn_grid.lon_name}, 'tmin')
        tx_var = _variable(tx, tmax_variable, {tx_time, tx_grid.lat_name, tx_grid.lon_name}, 'tmax')
        tn_unit, tn_shift = _temperature_units(tn, tn_var)
        tx_unit, tx_shift = _temperature_units(tx, tx_var)
        mask_var, mask = _mask(mk, mask_grid, mask_variable)
        tn_indices, tn_dates = _year_indices(tn, tn_time, year)
        tx_indices, tx_dates = _year_indices(tx, tx_time, year)
        if tn_dates != tx_dates:
            raise ValueError('Tmin/Tmax source calendars differ')
        assignments, qa_cells = _assign_cells(geometries, tn_grid, mask, max_fallback_km)
        series_cache: dict[tuple[int, int], tuple[np.ndarray, np.ndarray]] = {}
        records: list[dict[str, str]] = []
        for code, cell in sorted(assignments.items()):
            key = cell.row, cell.column
            if key not in series_cache:
                a = _temperatures(tn, tn_var, tn_time, tn_grid, tn_indices, cell, tn_shift)
                b = _temperatures(tx, tx_var, tx_time, tx_grid, tx_indices, cell, tx_shift)
                if np.any(a > b):
                    raise ValueError(f'Tmin exceeds Tmax for {cell.cell_id}')
                series_cache[key] = a, b
            a, b = series_cache[key]
            for idx, day in enumerate(tn_dates):
                records.append({
                    'municipality_code': code,
                    'municipality': registry[code],
                    'date': day,
                    'grid_cell_id': cell.cell_id,
                    'grid_latitude': f'{cell.latitude:.6f}',
                    'grid_longitude': f'{cell.longitude:.6f}',
                    'tmin_c': f'{a[idx]:.6f}',
                    'tmax_c': f'{b[idx]:.6f}',
                })
        return records, {
            'status': STATUS, 'candidate_id': 'H03', 'source_id': 'F08',
            'reference_year': year, 'daily_observations': len(records),
            'municipality_count': len(assignments),
            'unique_masked_cells': len(series_cache),
            'source_dataset': 'ARPA Piemonte NWIOI gridded daily Tmin/Tmax',
            'temperature_units_tmin': tn_unit, 'temperature_units_tmax': tx_unit,
            'tmin_variable': tn_var, 'tmax_variable': tx_var,
            'mask_variable': mask_var,
            'source_netcdf_temporal_grid_and_temperature_checks_passed': True,
            'technical_geospatial_cell_selection_completed': True,
            'masked_cells_only': True,
            'municipality_assignments': qa_cells,
            'limitations': 'Single 0.125-degree masked grid cell per Comune; centerpoint or nearest-cell fallback, not municipal area average; altitude differences unresolved.',
            'scientific_approval': False, 'canonical_data_modified': False,
        }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tmin-netcdf', required=True, type=Path)
    p.add_argument('--tmax-netcdf', required=True, type=Path)
    p.add_argument('--mask-netcdf', required=True, type=Path, help='Original ARPA NWIOI Piemonte region mask, mandatory')
    p.add_argument('--boundaries-geojson', type=Path, default=GEOJSON,
                   help='27 official 2026 ISTAT polygons, not a centroids table')
    p.add_argument('--registry', type=Path, default=REGISTRY)
    p.add_argument('--reference-year', type=int, default=YEAR)
    p.add_argument('--out-dir', required=True, type=Path,
                   help='Fresh local directory; existing results are never overwritten')
    p.add_argument('--tmin-variable')
    p.add_argument('--tmax-variable')
    p.add_argument('--mask-variable')
    p.add_argument('--max-fallback-km', type=float, default=25.0)
    p.add_argument('--expected-tmin-sha256', help='Optional independently recorded original hash')
    p.add_argument('--expected-tmax-sha256', help='Optional independently recorded original hash')
    p.add_argument('--expected-mask-sha256', help='Optional independently recorded mask hash')
    p.add_argument('--expected-boundaries-sha256', help='Optional independently recorded ISTAT GeoJSON hash')
    args = p.parse_args(argv)
    if args.out_dir.exists():
        p.error('Existing output directory: previous evidence must be preserved')
    for key, path, expected in [('Tmin', args.tmin_netcdf, ''), ('Tmax', args.tmax_netcdf, ''),
                                ('Mask', args.mask_netcdf, ''), ('GeoJSON', args.boundaries_geojson, ''),
                                ('Registry', args.registry, '')]:
        if not path.is_file():
            p.error(f'Missing {key} input {path}')
    source_paths = {
        'tmin_netcdf': args.tmin_netcdf,
        'tmax_netcdf': args.tmax_netcdf,
        'mask_netcdf': args.mask_netcdf,
        'boundaries_geojson': args.boundaries_geojson,
        'municipality_registry': args.registry,
    }
    initial_hashes = {label: digest(path) for label, path in source_paths.items()}
    for label, expected in (
        ('tmin_netcdf', args.expected_tmin_sha256),
        ('tmax_netcdf', args.expected_tmax_sha256),
        ('mask_netcdf', args.expected_mask_sha256),
        ('boundaries_geojson', args.expected_boundaries_sha256),
    ):
        if expected is not None:
            if not re.fullmatch(r'[a-fA-F0-9]{64}', expected) or initial_hashes[label] != expected.lower():
                p.error(f'Original source hash invalid or mismatch: {label}')
    values, qa = extract(args.tmin_netcdf, args.tmax_netcdf, args.mask_netcdf,
                         args.boundaries_geojson, args.registry, args.reference_year,
                         tmin_variable=args.tmin_variable, tmax_variable=args.tmax_variable,
                         mask_variable=args.mask_variable, max_fallback_km=args.max_fallback_km)
    # Complete all computational QA before creating the output directory.
    args.out_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.epah_h03_nwioi_', dir=args.out_dir.parent) as tmp:
        work = Path(tmp)
        normalized = work / OUTPUT_CSV
        with normalized.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator='\n')
            writer.writeheader()
            writer.writerows(values)
        registry = read_registry(args.registry)
        annual, annual_qa = aggregate(normalized, registry, args.reference_year)
        write_outputs(work / 'h03_preview', annual, annual_qa, normalized,
                      args.tmin_netcdf, args.tmax_netcdf, args.registry)
        if {label: digest(path) for label, path in source_paths.items()} != initial_hashes:
            raise ValueError('A source file changed during processing; all outputs discarded')
        qa['input_hashes_sha256'] = {**initial_hashes, 'normalized_daily_csv': digest(normalized)}
        qa['annual_hdd_preview_sha256'] = digest(work / 'h03_preview' / 'hdd_eurostat_annual_preview.csv')
        (work / OUTPUT_QA).write_text(json.dumps(qa, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        # Exclusive final folder creation; never rename over an existing directory.
        try:
            args.out_dir.mkdir()
        except FileExistsError as exc:
            raise FileExistsError(f'Preserve previously existing output: {args.out_dir}') from exc
        try:
            for child in work.iterdir():
                shutil.move(str(child), str(args.out_dir / child.name))
        except Exception:
            shutil.rmtree(args.out_dir)
            raise
    print(f'H03: generated {len(annual)} annual estimates and {len(values)} daily observations')
    print(f'Review files: {args.out_dir} (technical_draft_do_not_publish)')
    print('Scientific validation and municipal representativeness remain pending')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
