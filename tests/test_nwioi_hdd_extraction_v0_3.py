"""NetCDF-to-H03 candidate tests: synthetic fields, no downloads or real-data claims."""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
MODULE = ROOT / 'scripts/extract_nwioi_hdd_2025_v0_3.py'
SPEC = importlib.util.spec_from_file_location('extract_nwioi_hdd_2025_v0_3', MODULE)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


def build_fixture(tmp_path: Path, *, days=365, kelvin=False, mask_all_zero=False,
                  no_inside=False, bad_date=False, wrong_grid=False):
    """27 little polygons, mostly centred exactly on distinct 0.125-degree cells."""
    lat = np.array([45.0 + i * .125 for i in range(6)], dtype=float)
    lon = np.array([7.0 + j * .125 for j in range(6)], dtype=float)
    times = pd.date_range('2025-01-01', periods=days, freq='D')
    if bad_date:
        times = times[:-1].append(pd.DatetimeIndex([times[-2]]))
    temp = np.empty((days, 6, 6), dtype=float)
    temp[:] = 12.0 + (273.15 if kelvin else 0)
    tmin = tmp_path / 'tmin.nc'
    tmax = tmp_path / 'tmax.nc'
    mask = tmp_path / 'mask.nc'
    nclon = lon + .125 if wrong_grid else lon
    data = {'time': times, 'lat': lat, 'lon': lon}
    xr.Dataset({'TN': (('time', 'lat', 'lon'), temp, {'units':'kelvin' if kelvin else 'C'})},coords=data).to_netcdf(tmin)
    xr.Dataset({'TX': (('time', 'lat', 'lon'), temp + 4, {'units':'K' if kelvin else 'degrees_Celsius'})},coords={**data, 'lon': nclon}).to_netcdf(tmax)
    mask_values = np.zeros((6,6),dtype=float) if mask_all_zero else np.ones((6,6),dtype=float)
    xr.Dataset({'region': (('lat','lon'), mask_values)},coords={'lat':lat,'lon':lon}).to_netcdf(mask)
    registry = tmp_path / 'registry.csv'
    with registry.open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['municipality','istat_code'])
        w.writerows((f'Comune {i}', f'001{i:03d}') for i in range(1,28))
    shapes=[]
    for i in range(1,28):
        yi=(i-1)//6;xi=(i-1)%6
        x,y=lon[xi],lat[yi]
        if no_inside and i==1:
            x += .055; y += .055
        d=.025 if not no_inside or i!=1 else .006
        ring=[[x-d,y-d],[x+d,y-d],[x+d,y+d],[x-d,y+d],[x-d,y-d]]
        shapes.append({'type':'Feature','properties':{'municipality':f'Comune {i}',
                'municipality_code':f'001{i:03d}','boundary_year':2026},
                'geometry':{'type':'Polygon','coordinates':[ring]}})
    geography=tmp_path/'geo.json'
    geography.write_text(json.dumps({'type':'FeatureCollection',
        'crs':{'type':'name','properties':{'name':'urn:ogc:def:crs:OGC:1.3:CRS84'}},
        'features':shapes}),encoding='utf-8')
    return tmin,tmax,mask,geography,registry


def run_extract(fixture, **overrides):
    return mod.extract(*fixture,2025,**overrides)


def test_happy_path_27_municipalities_365_days_and_mask(tmp_path):
    records,qa=run_extract(build_fixture(tmp_path))
    assert len(records)==27*365
    assert qa['masked_cells_only'] is True
    assert qa['scientific_approval'] is False
    assert qa['municipality_count']==27
    assert qa['unique_masked_cells']==27
    assert all(x['selection']=='masked_grid_center_inside_polygon' for x in qa['municipality_assignments'])
    assert records[0]['date']=='2025-01-01'
    assert records[-1]['date']=='2025-12-31'
    assert records[0]['tmin_c']=='12.000000'
    assert records[0]['tmax_c']=='16.000000'


def test_kelvin_converted_into_celsius(tmp_path):
    records,qa=run_extract(build_fixture(tmp_path,kelvin=True))
    assert records[0]['tmin_c']=='12.000000'
    assert qa['temperature_units_tmin']=='kelvin'


def test_reject_incomplete_year(tmp_path):
    with pytest.raises(ValueError,match='Incomplete year'):
        run_extract(build_fixture(tmp_path,days=364))


def test_reject_duplicate_calendar_date(tmp_path):
    with pytest.raises(ValueError,match='Duplicate source date'):
        run_extract(build_fixture(tmp_path,bad_date=True))


def test_fail_closed_when_mask_is_empty(tmp_path):
    with pytest.raises(ValueError,match='no valid Piemonte'):
        run_extract(build_fixture(tmp_path,mask_all_zero=True))


def test_reject_unaligned_temperature_grids(tmp_path):
    with pytest.raises(ValueError,match='grids are not aligned'):
        run_extract(build_fixture(tmp_path,wrong_grid=True))


def test_bounded_nearest_masked_fallback(tmp_path):
    _,qa=run_extract(build_fixture(tmp_path,no_inside=True))
    assert qa['municipality_assignments'][0]['selection']=='nearest_masked_cell_to_polygon_boundary'
    assert qa['municipality_assignments'][0]['boundary_distance_km_approx']>0


def test_fallback_respects_max_distance(tmp_path):
    with pytest.raises(ValueError,match='nearest ARPA masked cell'):
        run_extract(build_fixture(tmp_path,no_inside=True),max_fallback_km=.01)


def test_min_greater_than_max_blocks(tmp_path):
    fixtures=build_fixture(tmp_path)
    with xr.open_dataset(fixtures[1]) as ds:
        modified=ds.load()
    modified['TX'].values[0,0,0]=0.0
    modified.to_netcdf(fixtures[1])
    with pytest.raises(ValueError,match='Tmin exceeds Tmax'):
        run_extract(fixtures)


def test_missing_value_blocks(tmp_path):
    fixtures=build_fixture(tmp_path)
    with xr.open_dataset(fixtures[0]) as ds:
        modified=ds.load()
    modified['TN'].values[0,0,0]=float('nan')
    modified.to_netcdf(fixtures[0])
    with pytest.raises(ValueError,match='missing or non-finite'):
        run_extract(fixtures)


def test_unknown_units_fails_closed(tmp_path):
    fixtures=build_fixture(tmp_path)
    with xr.open_dataset(fixtures[0]) as ds:
        modified=ds.load()
    modified['TN'].attrs['units']='unknown'
    modified.to_netcdf(fixtures[0])
    with pytest.raises(ValueError,match='unknown units'):
        run_extract(fixtures)


def test_municipality_registry_mismatch_blocks(tmp_path):
    fixtures=build_fixture(tmp_path)
    geo=json.loads(fixtures[3].read_text())
    geo['features'][0]['properties']['municipality_code']='999999'
    fixtures[3].write_text(json.dumps(geo))
    with pytest.raises(ValueError,match='Unexpected, duplicated or inconsistent'):
        run_extract(fixtures)


def test_missing_geometry_blocks(tmp_path):
    fixtures=build_fixture(tmp_path)
    geo=json.loads(fixtures[3].read_text())
    geo['features'].pop()
    fixtures[3].write_text(json.dumps(geo))
    with pytest.raises(ValueError,match='Missing municipality polygons'):
        run_extract(fixtures)


def test_projected_crs_refused(tmp_path):
    fixtures=build_fixture(tmp_path)
    geo=json.loads(fixtures[3].read_text())
    geo['crs']['properties']['name']='EPSG:32632'
    fixtures[3].write_text(json.dumps(geo))
    with pytest.raises(ValueError,match='not CRS84'):
        run_extract(fixtures)


def test_reject_unsupported_variable_name(tmp_path):
    with pytest.raises(ValueError,match='Unknown tmin variable'):
        run_extract(build_fixture(tmp_path),tmin_variable='not_exists')


def test_reject_invalid_fallback_km(tmp_path):
    with pytest.raises(ValueError,match='max_fallback_km'):
        run_extract(build_fixture(tmp_path),max_fallback_km=float('nan'))


def test_bad_mask_values_rejected(tmp_path):
    fixtures=build_fixture(tmp_path)
    with xr.open_dataset(fixtures[2]) as ds:
        modified=ds.load()
    modified['region'].values[0,0]=2
    modified.to_netcdf(fixtures[2])
    with pytest.raises(ValueError,match='only explicit 0 and 1'):
        run_extract(fixtures)


def test_no_unmasked_cell_selected_if_only_one_allowed(tmp_path):
    fixtures=build_fixture(tmp_path)
    with xr.open_dataset(fixtures[2]) as ds:
        modified=ds.load()
    modified['region'].values[:]=0
    modified['region'].values[0,0]=1
    modified.to_netcdf(fixtures[2])
    with pytest.raises(ValueError, match='nearest ARPA masked cell'):
        run_extract(fixtures,max_fallback_km=2)


def test_netcdf_source_input_paths_must_be_distinct(tmp_path):
    fixtures=build_fixture(tmp_path)
    with pytest.raises(ValueError,match='Five distinct'):
        mod.extract(fixtures[0],fixtures[0],*fixtures[2:],2025)


def test_end_to_end_cli_writes_preview_and_does_not_overwrite(tmp_path,monkeypatch):
    # The CLI intentionally calls the existing H03 aggregate: this exercises the
    # integration with the unmodified numerical pipeline in the GitHub checkout.
    fixtures=build_fixture(tmp_path)
    dest=tmp_path/'out'
    args=['--tmin-netcdf',str(fixtures[0]),'--tmax-netcdf',str(fixtures[1]),
          '--mask-netcdf',str(fixtures[2]),'--boundaries-geojson',str(fixtures[3]),
          '--registry',str(fixtures[4]),'--out-dir',str(dest)]
    assert mod.main(args)==0
    assert (dest/'nwioi_2025_municipal_daily.csv').is_file()
    preview=list(csv.DictReader((dest/'h03_preview'/'hdd_eurostat_annual_preview.csv').open()))
    assert len(preview)==27
    assert preview[0]['hdd_eurostat_estimated_c_days']=='1460.00'
    receipt=json.loads((dest/'extraction_qa.json').read_text())
    assert receipt['scientific_approval'] is False
    assert set(receipt['input_hashes_sha256'])=={
        'tmin_netcdf','tmax_netcdf','mask_netcdf','boundaries_geojson','municipality_registry','normalized_daily_csv'
    }
    before=(dest/'extraction_qa.json').read_bytes()
    with pytest.raises(SystemExit):
        mod.main(args)
    assert (dest/'extraction_qa.json').read_bytes()==before


def test_expected_tmin_sha256_rejects_wrong_source_before_output(tmp_path):
    fixtures = build_fixture(tmp_path)
    dest = tmp_path / 'out'
    with pytest.raises(SystemExit):
        mod.main(['--tmin-netcdf', str(fixtures[0]), '--tmax-netcdf', str(fixtures[1]),
                  '--mask-netcdf', str(fixtures[2]), '--boundaries-geojson', str(fixtures[3]),
                  '--registry', str(fixtures[4]), '--out-dir', str(dest),
                  '--expected-tmin-sha256', '0'*64])
    assert not dest.exists()


def test_explicit_source_hashes_match_source_files(tmp_path):
    fixtures = build_fixture(tmp_path)
    dest = tmp_path / 'out'
    args = ['--tmin-netcdf', str(fixtures[0]), '--tmax-netcdf', str(fixtures[1]),
            '--mask-netcdf', str(fixtures[2]), '--boundaries-geojson', str(fixtures[3]),
            '--registry', str(fixtures[4]), '--out-dir', str(dest)]
    for flag, source in zip(['--expected-tmin-sha256','--expected-tmax-sha256',
                              '--expected-mask-sha256','--expected-boundaries-sha256'],fixtures[:4]):
        args.extend([flag,mod.digest(source)])
    assert mod.main(args)==0
    receipt=json.loads((dest/'extraction_qa.json').read_text())
    assert receipt['input_hashes_sha256']['mask_netcdf']==mod.digest(fixtures[2])


def test_mask_zero_fillvalue_does_not_get_interpreted_as_missing(tmp_path):
    fixtures=build_fixture(tmp_path)
    with xr.open_dataset(fixtures[2]) as ds:
        mask=ds.load()
    mask['region'].values[0,0]=0
    mask['region'].encoding={'_FillValue':0}
    mask.to_netcdf(fixtures[2])
    # Every other cell is valid; first municipality uses a nearby masked grid
    # cell when the exact inside-polygon cell has mask=0.
    _, qa=run_extract(fixtures)
    assert qa['municipality_count']==27
    assert qa['municipality_assignments'][0]['selection']=='nearest_masked_cell_to_polygon_boundary'


def test_grid_cell_codes_match_existing_h03_identifier_contract(tmp_path):
    records,_=run_extract(build_fixture(tmp_path))
    import re
    assert all(re.fullmatch(r'[A-Za-z0-9_.:-]{1,100}', r['grid_cell_id']) for r in records)


def test_units_celsius_degree_symbols(tmp_path):
    fixtures=build_fixture(tmp_path)
    with xr.open_dataset(fixtures[0]) as ds:
        modified=ds.load()
    modified['TN'].attrs['units']='°C'
    modified.to_netcdf(fixtures[0])
    records,_=run_extract(fixtures)
    assert records[0]['tmin_c']=='12.000000'
