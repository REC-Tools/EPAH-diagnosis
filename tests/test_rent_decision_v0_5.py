from copy import deepcopy
import hashlib
import json
import pytest
from test_rent_preview_v0_5 import pack
from test_indicator_dashboard_v0_5 import CATALOGS
from epah_diagnosis.indicator_dashboard_v0_5 import build, load_catalogs, encode
from epah_diagnosis.rent_decision_v0_5 import fingerprint, validate_decision, RESERVATIONS


@pytest.fixture
def decision_inputs(pack, monkeypatch):
    module, path, snapshot = pack
    snapshot.update(input_kind='unclassified_local_sources', utci=None)
    for row in snapshot['municipalities']:
        row.update(tenure=None, atc=None)
    (path/'snapshot.json').write_bytes(encode(snapshot))
    import epah_diagnosis.source_review_hub_audit_v0_5 as audit
    monkeypatch.setattr(audit, 'audit_hub', lambda _: None)
    contract = load_catalogs(CATALOGS)[0]['V05-19']
    _, preview = module.derive(path, snapshot, contract['source']['url'])
    record = dict(schema_version='0.5-rent-decision-1', indicator_id='V05-19', period='2021',
                  decision='definition_and_calculation_approved_with_reservations',
                  approved_by='Revisore sintetico', role='Responsabile fittizio', decided_on='2026-11-24',
                  publication_allowed=True, publication_scope='V05-19_2021_only_with_limitations',
                  full_statistical_validation=False, evidence_sha256=fingerprint(preview, contract),
                  review_dossier_manifest_sha256='a'*64, reservations=list(RESERVATIONS),
                  user_statement='Dichiarazione sintetica di approvazione limitata e pubblicazione.',
                  authorization_provenance='explicit_user_statement_in_chat')
    return path, contract, preview, record


def test_evidence_bound_decision_exports_only_the_authorized_subset(decision_inputs, tmp_path_factory):
    path, contract, preview, record = decision_inputs
    decision = path/'decision.json'; decision.write_bytes(encode(record))
    out = tmp_path_factory.mktemp('rent-destinations')/'approved'
    snapshot = build(CATALOGS, out, source_pack=path, rent_preview=True, decision=decision)
    assert snapshot['scientific_approval'] is False and snapshot['publication_allowed'] is False
    assert snapshot['publication_subset_allowed'] is True
    assert snapshot['rent_decision']['approved_by'] == 'Revisore sintetico'
    public = out/'rent_publication'
    assert {p.name for p in public.iterdir()} == {'index.html','snapshot.json','rent_decision.json','rent_preview.csv','manifest.json'}
    doc = json.loads((public/'snapshot.json').read_bytes())
    assert doc['publication_allowed'] is True and doc['full_statistical_validation'] is False
    assert doc['scientific_approval_scope'] == 'definition_and_calculation_only'
    assert 'approvati con riserve' in doc['rent_preview']['authorization_scope']
    page = (public/'index.html').read_text(encoding='utf-8')
    assert 'Revisore sintetico' in page and page.count('<circle ')==27
    assert page.count('id="rent-decision"')==1
    assert 'Sei residui originali' in page and 'famiglie senza tetto escluse' in page
    assert 'non risposte' in page and 'precisione locale' in page
    assert 'V05-21' not in page and 'source_review/' not in page
    assert 'Pubblicazione: <strong>autorizzata' in page
    for name, digest in json.loads((public/'manifest.json').read_bytes())['files_sha256'].items():
        assert hashlib.sha256((public/name).read_bytes()).hexdigest() == digest


def test_no_publication_without_explicit_permission(decision_inputs, tmp_path_factory):
    path, contract, preview, record = decision_inputs
    record['publication_allowed'] = False
    decision = path/'decision.json'; decision.write_bytes(encode(record))
    out = tmp_path_factory.mktemp('rent-no-publication')/'approved'
    snapshot = build(CATALOGS, out, source_pack=path, rent_preview=True, decision=decision)
    assert snapshot['rent_decision'] is not None and snapshot['publication_subset_allowed'] is False
    assert not (out/'rent_publication').exists()
    assert 'non autorizzata' in (out/'index.html').read_text(encoding='utf-8')


@pytest.mark.parametrize('change', ['values','source','universe','formula','contract'])
def test_decision_cannot_be_reused_after_evidence_change(decision_inputs, change):
    path, contract, preview, record = decision_inputs
    preview, contract = deepcopy(preview), deepcopy(contract)
    if change=='values': preview['rows'][0]['rent']='99'
    elif change=='source': preview['source_sha256']['sources/tenure/raw/001091.xml']='b'*64
    elif change=='universe': preview['universe']['id']='another_universe'
    elif change=='formula': preview['formula']='100 - OWN / ALL'
    else: contract['unit']='another_unit'
    with pytest.raises(ValueError, match='does not cover'):
        validate_decision(record, preview, contract)


@pytest.mark.parametrize('field,value', [('full_statistical_validation', True), ('indicator_id','V05-21'),
 ('period','2025'), ('publication_scope','all_indicators'), ('reservations',[]), ('publication_allowed',1)])
def test_approval_scope_cannot_expand_or_drop_reservations(decision_inputs, field, value):
    path, contract, preview, record = decision_inputs
    record[field]=value
    with pytest.raises(ValueError): validate_decision(record, preview, contract)


def test_decision_needs_real_preview_before_output(decision_inputs, tmp_path_factory):
    path, contract, preview, record = decision_inputs
    decision=path/'decision.json'; decision.write_bytes(encode(record))
    out=tmp_path_factory.mktemp('rent-invalid-decision')/'missing'
    with pytest.raises(ValueError, match='requires --rent-preview'):
        build(CATALOGS,out,decision=decision)
    assert not out.exists()
