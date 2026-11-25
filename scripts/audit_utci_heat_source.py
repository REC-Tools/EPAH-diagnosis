"""Replay annual heat counts against local daily UTCI maxima; no aggregation."""
from __future__ import annotations

import argparse
import calendar
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

import numpy as np
from netCDF4 import Dataset, num2date

THRESHOLDS = (26, 32, 38, 46)
CATALOGUE = 'https://cds.climate.copernicus.eu/datasets/derived-utci-historical?tab=overview'
CALENDARS = {'standard', 'gregorian', 'proleptic_gregorian'}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def coordinates(ds):
    result = []
    for name, unit in [('lat', 'degrees_north'), ('lon', 'degrees_east')]:
        v = ds.variables[name]
        a = np.ma.asarray(v[:], dtype=float)
        if (v.dimensions != (name,) or getattr(v, 'units', None) != unit
                or a.ndim != 1 or a.size < 2 or np.ma.getmaskarray(a).any()
                or not np.isfinite(a).all()):
            raise ValueError('Explicit finite latitude/longitude coordinates required')
        delta = np.diff(a)
        if not ((delta > 0).all() or (delta < 0).all()):
            raise ValueError('Coordinates must be unique and monotonic')
        if not np.allclose(np.abs(delta), .25, rtol=0, atol=1e-10):
            raise ValueError('Expected the documented 0.25-degree source grid')
        if np.any(np.abs(a) > (90 if name == 'lat' else 180)):
            raise ValueError('Coordinate outside the supported geographic range')
        result.append(np.asarray(a))
    return result


def field(ds, name):
    v = ds.variables[name]
    if len(v.dimensions) != 3 or set(v.dimensions) != {'time', 'lat', 'lon'}:
        raise ValueError('Expected explicit time/lat/lon dimensions')
    a = np.ma.asarray(v[:], dtype=float)
    return a.transpose([v.dimensions.index(d) for d in ('time', 'lat', 'lon')])


def times_and_bounds(ds):
    t = ds.variables['time']
    if t.dimensions != ('time',) or getattr(t, 'calendar', None) not in CALENDARS:
        raise ValueError('Explicit Gregorian calendar and time dimension required')
    if not isinstance(getattr(t, 'units', None), str):
        raise ValueError('Explicit time units required')
    raw = np.ma.asarray(t[:])
    if np.ma.getmaskarray(raw).any() or not np.isfinite(raw).all():
        raise ValueError('Time coordinates must be finite and unmasked')
    name = getattr(t, 'bounds', None)
    if name not in ds.variables:
        raise ValueError('Explicit source time bounds required')
    b = ds.variables[name]
    bounds = np.ma.asarray(b[:])
    if b.dimensions != ('time', 'bnds') or bounds.shape != (len(raw), 2):
        raise ValueError('Time bounds must have time/bnds dimensions')
    if np.ma.getmaskarray(bounds).any() or not np.isfinite(bounds).all():
        raise ValueError('Time bounds must be finite and unmasked')
    return num2date(raw, t.units, t.calendar), num2date(bounds, t.units, t.calendar)


def label(t):
    return (t.year, t.month, t.day, t.hour, t.minute, t.second, t.microsecond)


def inspect(annual, daily_zip, *, year=2025):
    """Return a source-only report; incomplete or mismatching data remain blocked."""
    annual, daily_zip = Path(annual), Path(daily_zip)
    for path in (annual, daily_zip):
        if not path.is_file() or path.is_symlink() or getattr(path, 'is_junction', lambda: False)():
            raise ValueError('Inputs must be regular local files')
    if not 1940 <= year <= 9998:
        raise ValueError('Reference year outside the supported range')
    before = {'annual_sha256': digest(annual), 'daily_zip_sha256': digest(daily_zip)}
    expected_days = 366 if calendar.isleap(year) else 365
    annual_values, annual_units = {}, {}
    with Dataset(annual) as ds:
        lat, lon = coordinates(ds)
        times, bounds = times_and_bounds(ds)
        if len(times) != 1 or times[0].year != year:
            raise ValueError('Annual observation does not match the selected year')
        if (label(bounds[0, 0]) != (year, 1, 1, 0, 0, 0, 0)
                or label(bounds[0, 1]) != (year, 12, 31, 23, 0, 0, 0)
                or not bounds[0, 0] <= times[0] <= bounds[0, 1]):
            raise ValueError('Annual support must retain source Jan 1 00:00 to Dec 31 23:00 endpoints')
        for threshold in THRESHOLDS:
            name = f'utci_days_above_{threshold}_daily_max'
            v = ds.variables[name]
            units = getattr(v, 'units', None)
            if units not in (None, 'days', 'day', 'd'):
                raise ValueError('Annual heat units conflict with day counts')
            a = field(ds, name)
            if a.shape != (1, len(lat), len(lon)):
                raise ValueError('Annual heat shape does not match its coordinates')
            valid = ~np.ma.getmaskarray(a) & np.isfinite(a.data)
            if np.any(valid & ((a.data < 0) | (a.data > expected_days) | (a.data != np.floor(a.data)))):
                raise ValueError('Annual counts must be integers within the selected year')
            annual_values[threshold], annual_units[threshold] = a[0], units

    shape = (len(lat), len(lon))
    valid_days = np.zeros(shape, dtype=np.int64)
    counts = {t: np.zeros(shape, dtype=np.int64) for t in THRESHOLDS}
    inclusive = {t: np.zeros(shape, dtype=np.int64) for t in THRESHOLDS}
    dates, member_hashes, history_hashes, units_received = set(), {}, {}, set()
    with ZipFile(daily_zip) as archive:
        members = [m for m in archive.infolist() if not m.is_dir()]
        if len(members) > 10000 or sum(m.file_size for m in members) > 1024 ** 3:
            raise ValueError('Daily archive exceeds the inspection size limit')
        if len({m.filename for m in members}) != len(members):
            raise ValueError('Duplicate archive member names')
        for m in members:
            p = PurePosixPath(m.filename)
            if p.is_absolute() or '..' in p.parts or '\\' in m.filename or ':' in m.filename:
                raise ValueError('Unsafe archive member name')
        nc_members = [m for m in members if m.filename.endswith('.nc')]
        if not nc_members:
            raise ValueError('Daily archive contains no NetCDF files')
        for m in nc_members:
            raw = archive.read(m)
            member_hashes[m.filename] = hashlib.sha256(raw).hexdigest()
            with Dataset('daily.nc', memory=raw) as ds:
                dlat, dlon = coordinates(ds)
                if set(dlat) != set(lat) or set(dlon) != set(lon):
                    raise ValueError('Daily and annual coordinates differ')
                a = field(ds, 'utci_daily_max')
                v = ds.variables['utci_daily_max']
                if a.shape[1:] != (len(dlat), len(dlon)):
                    raise ValueError('Daily heat shape does not match its coordinates')
                if getattr(v, 'cell_methods', None) != 'time: maximum':
                    raise ValueError('Explicit daily maximum cell_methods required')
                units = getattr(v, 'units', None)
                history = str(getattr(ds, 'history', ''))
                if units not in (None, 'K', 'kelvin', 'Kelvin'):
                    raise ValueError('Daily maximum units conflict with Kelvin')
                if units is None and '-addc,273.15' not in history:
                    raise ValueError('Missing units require the source Kelvin conversion history')
                units_received.add(units or 'absent_in_original')
                history_hashes[m.filename] = hashlib.sha256(history.encode()).hexdigest()
                when, support = times_and_bounds(ds)
                if len(when) != a.shape[0]:
                    raise ValueError('Daily time and field shapes differ')
                a = a[:, [list(dlat).index(y) for y in lat], :][:, :, [list(dlon).index(x) for x in lon]]
                for i, stamp in enumerate(when):
                    day = date(stamp.year, stamp.month, stamp.day)
                    if day.year != year or day in dates:
                        raise ValueError('Duplicate daily date or date outside selected year')
                    if (label(support[i, 0]) != (day.year, day.month, day.day, 0, 0, 0, 0)
                            or label(support[i, 1]) != (day.year, day.month, day.day, 23, 0, 0, 0)
                            or not support[i, 0] <= stamp <= support[i, 1]):
                        raise ValueError('Daily support must retain the source 00:00 to 23:00 convention')
                    dates.add(day)
                    values = np.asarray(a[i].data)
                    valid = ~np.ma.getmaskarray(a[i]) & np.isfinite(values)
                    if np.any(valid & ((values < 100) | (values > 400))):
                        raise ValueError('Values conflict with the reviewed Kelvin representation')
                    valid_days += valid
                    for t in THRESHOLDS:
                        counts[t] += valid & (values > t + 273.15)
                        inclusive[t] += valid & (values >= t + 273.15)
    expected = {date(year, 1, 1) + timedelta(days=i) for i in range(expected_days)}
    missing = sorted(expected - dates)
    complete = (valid_days == expected_days) & (not missing)
    issues, records = [], []
    if not complete.all():
        issues.append('incomplete_daily_coverage')
    for t in THRESHOLDS:
        original = annual_values[t]
        annual_valid = ~np.ma.getmaskarray(original) & np.isfinite(original.data)
        matches = annual_valid & complete & (original.data == counts[t])
        if not annual_valid.all():
            issues.append(f'annual_{t}_missing_or_nonfinite')
        if not matches.all():
            issues.append(f'annual_{t}_not_fully_reproduced')
        records.append({
            'threshold_celsius': str(t), 'threshold_kelvin': str(t + 273.15),
            'annual_field': f'utci_days_above_{t}_daily_max',
            'annual_units_as_received': annual_units[t],
            'annual_counts': [[int(original.data[i, j]) if annual_valid[i, j] else None
                               for j in range(len(lon))] for i in range(len(lat))],
            'replayed_strict_counts': counts[t].tolist(),
            'replayed_inclusive_counts': inclusive[t].tolist(),
            'fully_reproduced_cells': int(matches.sum()),
            'strict_inclusive_difference_cells': int(np.count_nonzero(counts[t] != inclusive[t])),
        })
    if before != {'annual_sha256': digest(annual), 'daily_zip_sha256': digest(daily_zip)}:
        raise ValueError('Source bytes changed during inspection')
    return {
        'schema_version': '0.5-utci-heat-source-audit-1',
        'status': 'technical_draft_do_not_publish',
        'result': 'blocked' if issues else 'daily_replay_matches_annual',
        'scientific_approval': False, 'publication_allowed': False,
        'municipal_aggregation_performed': False,
        'reference_year': year, 'operator_replayed': '>',
        'threshold_semantics_approved': False,
        'unit_basis_url': CATALOGUE, 'daily_units_as_received': sorted(units_received),
        'latitudes': lat.tolist(), 'longitudes': lon.tolist(),
        'days_expected': expected_days, 'distinct_daily_dates': len(dates),
        'missing_calendar_dates': [d.isoformat() for d in missing],
        'valid_days_per_cell': valid_days.tolist(), 'fields': records,
        'issues': issues, 'provenance': {**before, 'daily_member_sha256': member_hashes,
                                      'daily_history_sha256': history_hashes},
        'source_unchanged': True,
        'limitations': [
            'Daily maxima replayed; original hourly contributions not independently reconstructed.',
            'Equal strict and inclusive counts do not determine producer boundary semantics.',
            'No municipal weights, aggregation, scientific approval or publication authorization.',
            'Cumulative thresholds remain separate; do not sum their counts.',
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--annual', required=True, type=Path)
    parser.add_argument('--daily-zip', required=True, type=Path)
    parser.add_argument('--year', type=int, default=2025)
    parser.add_argument('--json-out', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.json_out.exists() or args.json_out.is_symlink():
            raise ValueError('Output must be a new file')
        report = inspect(args.annual, args.daily_zip, year=args.year)
        serialized = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
        with args.json_out.open('x', encoding='utf-8') as stream:
            stream.write(serialized)
    except (ValueError, OSError, KeyError, RuntimeError, BadZipFile) as exc:
        print(f'BLOCKED: {exc}')
        return 2
    print(report['result'])
    return 2 if report['issues'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
