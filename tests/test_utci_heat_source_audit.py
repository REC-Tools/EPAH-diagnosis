"""Synthetic source regressions: no real territorial data or approval."""
import json
from pathlib import Path
import sys
from zipfile import ZipFile

import numpy as np
from netCDF4 import Dataset
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import audit_utci_heat_source as audit


def sources(tmp_path, *, days=365, values=None, units='K', history='',
            cell_methods='time: maximum', reversed_grid=False, transpose=False,
            duplicate_date=False, bad_bounds=False, annual_delta=0, annual_missing=False):
    a = np.full((days, 2, 2), 300., dtype=float) if values is None else values.copy()
    annual = tmp_path / 'annual.nc'
    daily = tmp_path / 'daily.nc'
    zipped = tmp_path / 'daily.zip'

    def setup(path, length, reversed_coordinates=False):
        ds = Dataset(path, 'w')
        for name, size in [('time', length), ('lat', 2), ('lon', 2), ('bnds', 2)]:
            ds.createDimension(name, size)
        for name, coords, unit in [('lat', [45., 45.25], 'degrees_north'),
                                   ('lon', [7., 7.25], 'degrees_east')]:
            v = ds.createVariable(name, 'f8', (name,))
            v.units = unit
            v[:] = coords[::-1] if reversed_coordinates else coords
        t = ds.createVariable('time', 'f8', ('time',))
        t.units = 'hours since 2025-01-01 00:00:00'
        t.calendar = 'proleptic_gregorian'
        t.bounds = 'time_bnds'
        b = ds.createVariable('time_bnds', 'f8', ('time', 'bnds'))
        return ds, t, b

    with setup(annual, 1)[0] as ds:
        ds.variables['time'][:] = [4379.5]
        ds.variables['time_bnds'][:] = [[0, 8759]]
        for threshold in audit.THRESHOLDS:
            v = ds.createVariable(f'utci_days_above_{threshold}_daily_max', 'f8',
                                  ('time', 'lat', 'lon'), fill_value=-9999.)
            v.units = 'days'
            count = np.sum(np.isfinite(a) & (a > threshold + 273.15), axis=0)
            v[:] = count[None, :, :] + (annual_delta if threshold == 26 else 0)
            if annual_missing and threshold == 26:
                v[0, 0, 0] = -9999.
    with setup(daily, days, reversed_grid)[0] as ds:
        timestamps = np.arange(days) * 24 + 11.5
        if duplicate_date:
            timestamps[-1] = timestamps[-2]
        ds.variables['time'][:] = timestamps
        starts = (timestamps // 24) * 24
        ds.variables['time_bnds'][:] = np.column_stack((starts, starts + 23))
        if bad_bounds:
            ds.variables['time_bnds'][0, 1] = 24
        dims = ('lon', 'time', 'lat') if transpose else ('time', 'lat', 'lon')
        v = ds.createVariable('utci_daily_max', 'f8', dims, fill_value=-9999.)
        v.cell_methods = cell_methods
        if units is not None:
            v.units = units
        ds.history = history
        written = a[:, ::-1, ::-1] if reversed_grid else a
        v[:] = written.transpose(2, 0, 1) if transpose else written
        # The lower daily-minimum series must never be selected for this replay.
        minimum = ds.createVariable('utci_daily_min', 'f8', ('time', 'lat', 'lon'))
        minimum[:] = 270.
    with ZipFile(zipped, 'w') as archive:
        archive.write(daily, 'daily.nc')
    return annual, zipped


def test_complete_replay_uses_maxima_and_keeps_all_thresholds(tmp_path):
    annual, daily = sources(tmp_path)
    before = [audit.digest(p) for p in (annual, daily)]
    report = audit.inspect(annual, daily)
    assert report['result'] == 'daily_replay_matches_annual'
    assert report['valid_days_per_cell'] == [[365, 365], [365, 365]]
    assert [r['replayed_strict_counts'][0][0] for r in report['fields']] == [365, 0, 0, 0]
    assert [audit.digest(p) for p in (annual, daily)] == before
    assert not report['scientific_approval'] and not report['publication_allowed']
    assert not report['municipal_aggregation_performed']
    assert str(tmp_path) not in json.dumps(report)


def test_exact_threshold_is_excluded_and_inclusive_count_is_preserved(tmp_path):
    values = np.full((365, 2, 2), 299.15)
    values[0, 0, 0] = np.nextafter(299.15, np.inf)
    annual, daily = sources(tmp_path, values=values)
    report = audit.inspect(annual, daily)
    assert report['fields'][0]['replayed_strict_counts'] == [[1, 0], [0, 0]]
    assert report['fields'][0]['replayed_inclusive_counts'] == [[365, 365], [365, 365]]
    assert report['fields'][0]['strict_inclusive_difference_cells'] == 4
    assert not report['threshold_semantics_approved']


def test_exact_coordinate_reordering_and_dimension_transposition(tmp_path):
    values = np.full((365, 2, 2), 280.)
    values[:, 0, 1] = 310.
    annual, daily = sources(tmp_path, values=values, reversed_grid=True, transpose=True)
    report = audit.inspect(annual, daily)
    assert report['result'] == 'daily_replay_matches_annual'
    assert report['fields'][0]['replayed_strict_counts'] == [[0, 365], [0, 0]]


def test_missing_calendar_date_blocks_instead_of_imputing(tmp_path):
    report = audit.inspect(*sources(tmp_path, days=364))
    assert report['result'] == 'blocked'
    assert report['missing_calendar_dates'] == ['2025-12-31']
    assert report['fields'][0]['fully_reproduced_cells'] == 0


@pytest.mark.parametrize('missing', [np.nan, -9999.])
def test_missing_cell_blocks_only_its_full_reproduction(tmp_path, missing):
    values = np.full((365, 2, 2), 300.)
    values[10, 0, 0] = missing
    report = audit.inspect(*sources(tmp_path, values=values))
    assert report['result'] == 'blocked'
    assert report['valid_days_per_cell'] == [[364, 365], [365, 365]]
    assert report['fields'][0]['fully_reproduced_cells'] == 3


def test_annual_mismatch_is_reported(tmp_path):
    report = audit.inspect(*sources(tmp_path, annual_delta=-1))
    assert report['result'] == 'blocked'
    assert 'annual_26_not_fully_reproduced' in report['issues']


def test_missing_annual_cell_is_not_zero(tmp_path):
    report = audit.inspect(*sources(tmp_path, annual_missing=True))
    assert report['result'] == 'blocked'
    assert report['fields'][0]['annual_counts'][0][0] is None


@pytest.mark.parametrize('options, message', [
    ({'units': 'C'}, 'Kelvin'),
    ({'units': None}, 'conversion history'),
    ({'cell_methods': 'time: minimum'}, 'maximum'),
    ({'duplicate_date': True}, 'Duplicate daily date'),
    ({'bad_bounds': True}, '00:00 to 23:00'),
])
def test_conflicting_or_ambiguous_source_metadata_rejected(tmp_path, options, message):
    with pytest.raises(ValueError, match=message):
        audit.inspect(*sources(tmp_path, **options))


def test_missing_units_preserved_with_conversion_evidence(tmp_path):
    report = audit.inspect(*sources(tmp_path, units=None, history='cdo -addc,273.15 input output'))
    assert report['daily_units_as_received'] == ['absent_in_original']
    assert report['result'] == 'daily_replay_matches_annual'


def test_cli_refuses_existing_output_and_preserves_sources(tmp_path):
    annual, daily = sources(tmp_path)
    output = tmp_path / 'report.json'
    output.write_text('existing evidence', encoding='utf-8')
    assert audit.main(['--annual', str(annual), '--daily-zip', str(daily), '--json-out', str(output)]) == 2
    assert output.read_text(encoding='utf-8') == 'existing evidence'


def test_cli_writes_blocked_report_for_incomplete_source(tmp_path):
    annual, daily = sources(tmp_path, days=364)
    output = tmp_path / 'report.json'
    assert audit.main(['--annual', str(annual), '--daily-zip', str(daily), '--json-out', str(output)]) == 2
    assert json.loads(output.read_text(encoding='utf-8'))['result'] == 'blocked'


def test_cli_handles_corrupt_archive_without_creating_report(tmp_path):
    annual, daily = sources(tmp_path)
    daily.write_bytes(b'not a ZIP file')
    output = tmp_path / 'report.json'
    assert audit.main(['--annual', str(annual), '--daily-zip', str(daily), '--json-out', str(output)]) == 2
    assert not output.exists()
