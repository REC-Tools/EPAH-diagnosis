from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pytest
from epah_diagnosis.indicator_dashboard_v0_5 import build, example, load_catalogs, validate_observations, render
from epah_diagnosis.methodology_v0_5 import main
ROOT = Path(__file__).resolve().parents[1]
CATALOGS = [ROOT/'docs/v0_5_indicator_contracts.json', ROOT/'docs/v0_5_housing_contracts.json']

@pytest.fixture
def contracts():
    return load_catalogs(CATALOGS)[0]


def test_one_command_renders_all_23_without_inventing_real_values(tmp_path):
    out = tmp_path/'empty'
    assert main(['dashboard','--out-dir',str(out)]) == 0
    snap=json.loads((out/'snapshot.json').read_text())
    page=(out/'index.html').read_text()
    assert len(snap['indicators'])==23 and snap['numeric_indicator_count']==0
    assert page.count('<article ')==23 and '<svg ' not in page
    assert snap['municipal_series_added']==0 and snap['calculation_performed'] is False
    assert 'DATI NON DISPONIBILI' in page


def test_example_uses_production_renderer_and_manifest(tmp_path):
    out=tmp_path/'example'
    snap=build(CATALOGS,out,synthetic=True)
    assert snap['numeric_indicator_count']==23 and len(snap['observations'])==69
    assert (out/'index.html').read_text().count('<svg ')==23
    assert (out/'index.html').read_text().count('DATI SINTETICI')>=24
    manifest=json.loads((out/'manifest.json').read_text())['files_sha256']
    assert all(hashlib.sha256((out/p).read_bytes()).hexdigest()==h for p,h in manifest.items())
    assert 'False' in (out/'readiness.csv').read_text()
    with pytest.raises(FileExistsError):build(CATALOGS,out,synthetic=True)


def test_zero_missingness_periods_and_precision_are_preserved(contracts,tmp_path):
    doc=example(contracts);doc['input_kind']='precomputed_technical_review'
    doc['observations']=doc['observations'][-3:]
    for row, code in zip(doc['observations'], ['ITC11','ITC12','ITC13']):row['geo_code']=code
    a,b,c=doc['observations']
    a['value']='0';b['value']=None;b['missing_reason']='suppressed'
    c['value']='1.234567890123456789';c['period']='2024'
    path=tmp_path/'input.json';path.write_text(json.dumps(doc))
    snap=build(CATALOGS,tmp_path/'out',observations=path)
    assert [r['value'] for r in snap['observations']]==['0',None,'1.234567890123456789']
    page=(tmp_path/'out/index.html').read_text()
    assert 'suppressed' in page and '1.234567890123456789' in page
    assert page.count('<svg ')==2


@pytest.mark.parametrize('field,value',[
 ('indicator_id','V05-99'),('unit','unknown'),('scope','municipality'),
 ('source_url','javascript:alert(1)'),('source_url','https://user:secret@example.org/'),
 ('value','NaN'),('value','Infinity'),('value',True),('value',2),
])
def test_invalid_contract_or_values_fail_before_output(contracts,field,value):
    doc=example(contracts);doc['observations'][0][field]=value
    with pytest.raises((ValueError,TypeError)):validate_observations(doc,contracts)


@pytest.mark.parametrize('unit,index,bad',[('percent',3,'101'),('days_per_year',1,'367'),('price_to_income_ratio',22,'-1')])
def test_unit_domains_are_checked(contracts,unit,index,bad):
    doc=example(contracts);row=doc['observations'][index*3];assert row['unit']==unit
    row['value']=bad
    with pytest.raises(ValueError):validate_observations(doc,contracts)


def test_missing_requires_reason_and_duplicates_are_not_aggregated(contracts):
    doc=example(contracts);doc['observations'][0]['value']=None
    with pytest.raises(ValueError):validate_observations(doc,contracts)
    doc=example(contracts);doc['observations'].append(deepcopy(doc['observations'][0]))
    with pytest.raises(ValueError):validate_observations(doc,contracts)


def test_false_approval_and_input_mixing_are_rejected(contracts,tmp_path):
    doc=example(contracts);doc['scientific_approval']=True
    with pytest.raises(ValueError):validate_observations(doc,contracts)
    path=tmp_path/'obs.json';path.write_text(json.dumps(example(contracts)))
    with pytest.raises(ValueError):build(CATALOGS,tmp_path/'mixed',observations=path,synthetic=True)
    assert not (tmp_path/'mixed').exists()


def test_untrusted_labels_are_escaped_without_script_injection(contracts,tmp_path):
    doc=example(contracts);doc['observations'][0]['geo_name']='<script>evil()</script>'
    doc['observations'][0]['series']='</script><img src=x onerror=evil()>'
    path=tmp_path/'input.json';path.write_text(json.dumps(doc))
    build(CATALOGS,tmp_path/'safe',observations=path)
    page=(tmp_path/'safe/index.html').read_text()
    assert '<script>evil()' not in page and '<img src=x' not in page
    assert '&lt;script&gt;' in page


def test_output_cannot_replace_input_tree(tmp_path):
    with pytest.raises(ValueError):build(CATALOGS,ROOT/'docs'/'new-dashboard')


def test_duplicate_json_keys_and_nonfinite_numbers_fail(tmp_path):
    path=tmp_path/'bad.json';path.write_text('{"schema_version":1,"schema_version":2}')
    with pytest.raises(ValueError):build(CATALOGS,tmp_path/'bad-output',observations=path)


def test_municipal_code_cannot_label_a_national_benchmark(contracts):
    doc=example(contracts);doc['input_kind']='precomputed_technical_review'
    doc['observations']=doc['observations'][:1]
    doc['observations'][0]['geo_code']='001007'
    with pytest.raises(ValueError):validate_observations(doc,contracts)
