"""Selected delivery preserves scale, approvals and deferred contracts."""
import csv
import hashlib
import io
import json

import pytest
from test_utci_heat_source_audit import sources
from test_rent_preview_v0_5 import pack
from test_rent_decision_v0_5 import decision_inputs
from test_indicator_dashboard_v0_5 import CATALOGS
from epah_diagnosis.indicator_dashboard_v0_5 import build, encode, CLOSEOUT_PROFILE
from epah_diagnosis.heat_grid_v0_5 import review, rows, panel, csv_bytes


def heat_sources(tmp_path):
    target = tmp_path / 'heat'
    target.mkdir()
    return sources(target)


def test_selected_delivery_has_only_rent_and_verified_grid_without_mutating_catalogs(decision_inputs, tmp_path_factory):
    path, contract, preview, decision = decision_inputs
    record = path / 'decision.json'
    record.write_bytes(encode(decision))
    destination = tmp_path_factory.mktemp('selected')
    annual, daily = heat_sources(destination)
    before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in CATALOGS]
    result = build(CATALOGS, destination / 'dashboard', source_pack=path, rent_preview=True,
                   decision=record, profile=CLOSEOUT_PROFILE, heat_annual=annual, heat_daily=daily)
    assert {i['id'] for i in result['indicators']} == {'V05-03', 'V05-19'}
    assert len(result['deferred_indicators']) == 21
    assert result['numeric_indicator_count'] == 2
    assert len(result['observations']) == 27
    assert all(r['indicator_id'] == 'V05-19' and r['period'] == '2021' for r in result['observations'])
    assert result['scientific_approval'] is False and result['publication_allowed'] is False
    assert result['heat_grid']['municipal_aggregation_performed'] is False
    assert result['heat_grid']['publication_allowed'] is False
    assert before == [hashlib.sha256(p.read_bytes()).hexdigest() for p in CATALOGS]
    out = destination / 'dashboard'
    page = (out / 'index.html').read_text(encoding='utf-8')
    assert page.count('<article ') == 2 and page.count('<svg ') == 5
    assert '<b>2</b>indicatori consultabili' in page
    assert '<b>0</b>senza valori numerici' in page
    assert 'Celle originali: adattamento locale separato' in page
    assert 'pubblicazione' in page and 'non sommarle' in page
    heat = list(csv.DictReader((out / 'heat_grid.csv').open(encoding='utf-8-sig')))
    assert len(heat) == 16 and {r['scope'] for r in heat} == {'source_grid_cell'}
    assert not any('geo_code' in row for row in heat)
    readiness = {r['indicator_id']: r for r in csv.DictReader((out / 'readiness.csv').open(encoding='utf-8-sig'))}
    assert readiness['V05-03']['numeric_values_supplied'] == '0'
    assert readiness['V05-03']['local_grid_values'] == '16'
    public = json.loads((out / 'rent_publication/snapshot.json').read_bytes())
    assert public['publication_allowed'] is True and 'heat_grid' not in public
    manifest = json.loads((out / 'manifest.json').read_bytes())['files_sha256']
    assert all(hashlib.sha256((out / name).read_bytes()).hexdigest() == digest for name, digest in manifest.items())


@pytest.mark.parametrize('kwargs', [dict(profile=CLOSEOUT_PROFILE), dict(profile='unknown'),
                                    dict(heat_annual='annual'), dict(heat_daily='daily')])
def test_incomplete_profile_or_heat_inputs_never_publish(tmp_path, kwargs):
    out = tmp_path / 'absent'
    with pytest.raises(ValueError):
        build(CATALOGS, out, **kwargs)
    assert not out.exists()


def test_incomplete_or_disagreeing_heat_is_blocked(tmp_path):
    annual, daily = sources(tmp_path, annual_delta=-1)
    with pytest.raises(ValueError, match='all four annual replays'):
        review(annual, daily)


def test_grid_values_orientation_and_genuine_zero(tmp_path):
    annual, daily = sources(tmp_path)
    report = review(annual, daily)
    values = rows(report)
    assert len(values) == 16
    assert {r['value'] for r in values} == {0, 365}
    assert {r['threshold_celsius'] for r in values} == {'26', '32', '38', '46'}
    assert all(r['scope'] == 'source_grid_cell' and r['period'] == 2025 for r in values)
    assert len(list(csv.DictReader(io.StringIO(csv_bytes(report).decode('utf-8-sig'))))) == 16
    page = panel(report)
    assert page.count('<svg ') == 4
    assert page.count('fill="hsl(28 75% 97.00%)"') == 12
    assert page.index('45.25° N') < page.index('45° N')
    assert 'confini comunali' in page and 'aree esterne' in page


def test_heat_without_source_portal_has_no_broken_portal_link(tmp_path):
    annual, daily = heat_sources(tmp_path)
    result = build(CATALOGS, tmp_path / 'heat-only', heat_annual=annual, heat_daily=daily)
    assert result['local_grid_observations_added'] == 16
    assert result['calculation_performed'] is True
    assert result['calculated_indicator_ids'] == ['LOCAL-UTCI-HEAT-GRID-2025']
    assert result['observations'] == []
    page = (tmp_path / 'heat-only/index.html').read_text(encoding='utf-8')
    assert 'source_review/index.html' not in page
    assert 'heat_grid.csv' in page
