from copy import deepcopy
from decimal import Decimal, localcontext
import pytest
from epah_diagnosis.rent_preview_v0_5 import calculate_review
from epah_diagnosis.indicator_dashboard_v0_5 import build
from test_indicator_dashboard_v0_5 import CATALOGS


def review():
    return {'source_periods': ['2021'], 'denominator_note_present': True,
            'denominator_universe': {'id': 'TIT_POSSESSO__ALL_N1'},
            'review_issues': ['partition_not_exact_no_tolerance_applied'],
            'partition_difference_as_received': '0.000001',
            'observations': [{'source_key': {'TENURE_STATUS_HOU': k}, 'period': '2021',
                              'value_as_received': v}
                             for k, v in [('ALL', '3'), ('RENT', '1.000000'),
                                          ('OWN', '1.000000'), ('OTH_OR', '0.999999')]]}


def test_original_denominator_and_residual_preserved():
    source = review(); before = deepcopy(source)
    result = calculate_review(source)
    assert source == before
    assert result['rent'] == '1.000000' and result['all'] == '3'
    assert result['residual'] == '0.000001' and result['has_residual'] is True
    with localcontext() as ctx:
        ctx.prec = 50
        assert result['value'] == str(Decimal(100) / 3)
        assert result['value'] != str(Decimal(100) / Decimal('2.999999'))


@pytest.mark.parametrize('mutate', [
    lambda r: r.update(source_periods=['2025']),
    lambda r: r.update(denominator_note_present=False),
    lambda r: r['review_issues'].append('source_flag_requires_review:RENT'),
    lambda r: r['observations'][0].update(value_as_received='0'),
    lambda r: r['observations'][1].update(value_as_received=None),
    lambda r: r['observations'][1].update(period='2025'),
    lambda r: r['observations'][1].update(value_as_received='NaN'),
    lambda r: r.update(partition_difference_as_received='0'),
])
def test_unreviewed_inputs_fail(mutate):
    source = review(); mutate(source)
    with pytest.raises(ValueError): calculate_review(source)


def test_preview_requires_source_and_fails_before_publication(tmp_path):
    with pytest.raises(ValueError, match='requires a real'):
        build(CATALOGS, tmp_path/'absent', rent_preview=True)
    assert not (tmp_path/'absent').exists()


@pytest.fixture
def pack(tmp_path, monkeypatch):
    import hashlib
    import epah_diagnosis.rent_preview_v0_5 as module
    codes = list(module.EXPECTED_RESIDUALS) + [f"009{i:03}" for i in range(21)]
    snapshot = {'source_sha256': {}, 'municipalities': [
        {'istat_code': c, 'municipality': 'Comune sintetico ' + c} for c in codes]}
    for name in ['sources/tenure/inputs/metadata.xml'] + [f'sources/tenure/raw/{c}.xml' for c in codes]:
        path = tmp_path/name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'synthetic test placeholder')
        snapshot['source_sha256'][name] = hashlib.sha256(path.read_bytes()).hexdigest()
    monkeypatch.setattr(module, 'metadata_profile', lambda raw: {'denominator_note': {'id': 'TIT_POSSESSO__ALL_N1'}})
    def inspect(raw, code, profile):
        result = review()
        delta = module.EXPECTED_RESIDUALS.get(code, '0.000000')
        result['partition_difference_as_received'] = delta
        result['observations'][-1]['value_as_received'] = str(Decimal(1) - Decimal(delta))
        return result
    monkeypatch.setattr(module, 'inspect_response', inspect)
    return module, tmp_path, snapshot


def test_full_preview_has_27_rows_and_exactly_six_preserved_residuals(pack):
    module, path, snapshot = pack
    rows, diagnostics = module.derive(path, snapshot, 'https://example.org/synthetic')
    assert len(rows) == 27 and diagnostics['residual_count'] == 6
    assert {r['geo_code']: r['residual'] for r in diagnostics['rows'] if r['has_residual']} == module.EXPECTED_RESIDUALS
    assert all(r['period'] == '2021' for r in rows)
    assert len(diagnostics['source_sha256']) == 28


def test_changed_residual_pattern_requires_new_review(pack, monkeypatch):
    module, path, snapshot = pack
    original = module.inspect_response
    def changed(raw, code, profile):
        result = original(raw, code, profile)
        if code == '001091':
            result['observations'][-1]['value_as_received'] = '1'
            result['partition_difference_as_received'] = '0'
        return result
    monkeypatch.setattr(module, 'inspect_response', changed)
    with pytest.raises(ValueError, match='Residual pattern changed'):
        module.derive(path, snapshot, 'https://example.org/synthetic')


def test_original_hash_change_blocks_calculation(pack):
    module, path, snapshot = pack
    (path/'sources/tenure/raw/001091.xml').write_bytes(b'changed')
    with pytest.raises(ValueError, match='changed since source audit'):
        module.derive(path, snapshot, 'https://example.org/synthetic')
