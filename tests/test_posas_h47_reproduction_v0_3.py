"""Independent source-to-preview H47 QA with exclusively synthetic fixtures."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/audit_posas_h47_reproduction_v0_3.py'
SPEC = importlib.util.spec_from_file_location('h47_independent_audit', SCRIPT)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def prepare(tmp_path: Path) -> tuple[Path, Path, Path]:
    registry = tmp_path / 'municipalities.csv'
    with registry.open('w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(('municipality', 'istat_code'))
        for n in range(1, 28):
            writer.writerow((f'Comune {n}', f'001{n:03d}'))
    source_zip = tmp_path / 'POSAS_2026_it_Comuni.zip'
    lines = ['"Popolazione residente per età e sesso al 1° gennaio 2026 (stima)"',
             'Codice comune;Comune;Età;Totale maschi;Totale femmine;Totale']
    for n in range(1, 28):
        for age in range(101):
            lines.append(f'001{n:03d};Comune {n};{age};1;2;3')
        lines.append(f'001{n:03d};Comune {n};999;101;202;303')
    with zipfile.ZipFile(source_zip, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        original_csv = ('\n'.join(lines) + '\n').encode('utf-8-sig')
        z.writestr(AUDIT.SOURCE_MEMBER, original_csv)
    zip_hash = AUDIT.sha_file(source_zip)
    csv_hash = hashlib.sha256(original_csv).hexdigest()
    root = tmp_path / 'review'
    (root / 'h47_preview').mkdir(parents=True)
    preview_path = root / 'h47_preview/population_0_11_preview.csv'
    with preview_path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['municipality_code', 'municipality',
            'reference_date', 'population_total', 'population_0_11', 'share_0_11_pct',
            'source_url', 'status'], lineterminator='\n')
        writer.writeheader()
        for n in range(1, 28):
            writer.writerow({'municipality_code': f'001{n:03d}', 'municipality': f'Comune {n}',
                'reference_date': '2026-01-01', 'population_total': '303', 'population_0_11': '36',
                'share_0_11_pct': '11.88', 'source_url': AUDIT.SOURCE_URL,
                'status': AUDIT.TECHNICAL_STATUS})
    qa_path = root / 'h47_preview/qa.json'
    write_json(qa_path, {'status': AUDIT.TECHNICAL_STATUS, 'coverage': '27/27',
        'epah_inventory_id': 'H47',
        'municipality_count': 27, 'sex_totals_verified': True,
        'resident_0_11_total': 972, 'resident_population_total': 8181,
        'green_community_weighted_share_pct': '11.88'})
    write_json(root / 'source_observation.json', {
        'status': AUDIT.TECHNICAL_STATUS, 'source_url_expected': AUDIT.SOURCE_URL,
        'reference_date_proposed': '2026-01-01', 'scientific_approval': False,
        'publication_allowed': False, 'csv_member': AUDIT.SOURCE_MEMBER,
        'original_zip_sha256': zip_hash, 'csv_member_sha256': csv_hash,
        'csv_columns': list(AUDIT.REQUIRED_COLUMNS),
    })
    write_json(root / 'h47_preview/manifest.json', {
        'status': AUDIT.TECHNICAL_STATUS, 'source_url': AUDIT.SOURCE_URL,
        'reference_date': '2026-01-01', 'scientific_approval': False,
        'canonical_registry_modified': False,
        'input_original_zip_sha256': zip_hash, 'input_zip_member': AUDIT.SOURCE_MEMBER,
        'input_member_sha256': csv_hash,
        'municipality_registry_sha256': AUDIT.sha_file(registry),
        'outputs_sha256': {
            preview_path.name: AUDIT.sha_file(preview_path),
            qa_path.name: AUDIT.sha_file(qa_path),
        },
    })
    return source_zip, root, registry


def refresh_sha(root: Path, name: str) -> None:
    file = root / 'h47_preview' / name
    manifest_path = root / 'h47_preview/manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['outputs_sha256'][name] = AUDIT.sha_file(file)
    write_json(manifest_path, manifest)


def test_independent_reproduction_passes_synthetic_zip(tmp_path: Path) -> None:
    source, root, registry = prepare(tmp_path)
    result = AUDIT.audit(source, root, registry, expected_source_sha256=AUDIT.sha_file(source))
    assert result['municipality_coverage'] == '27/27'
    assert result['population_0_11'] == 972
    assert result['population_total'] == 8181
    assert result['weighted_share_0_11_pct'] == '11.88'
    assert result['source_zip_sha_pinned'] is True
    assert result['scientific_approval'] is False
    assert result['publication_allowed'] is False
    assert result['schema_version'] == '2.0'
    assert result['audited_files_sha256'] == {
        name: AUDIT.sha_file(root / name) for name in (
            'h47_preview/population_0_11_preview.csv', 'h47_preview/qa.json',
            'h47_preview/manifest.json', 'source_observation.json')}


def test_zip_source_drift_blocks(tmp_path: Path) -> None:
    source, root, registry = prepare(tmp_path)
    with pytest.raises(ValueError, match='source drift'):
        AUDIT.audit(source, root, registry, expected_source_sha256='f' * 64)


def test_tampered_preview_hash_blocks(tmp_path: Path) -> None:
    source, root, registry = prepare(tmp_path)
    path = root / 'h47_preview/population_0_11_preview.csv'
    path.write_text(path.read_text().replace('11.88', '11.89', 1))
    with pytest.raises(ValueError, match='Output hash'):
        AUDIT.audit(source, root, registry)


def test_forged_manifest_hash_cannot_hide_modified_numerator(tmp_path: Path) -> None:
    source, root, registry = prepare(tmp_path)
    path = root / 'h47_preview/population_0_11_preview.csv'
    path.write_text(path.read_text().replace('303,36,11.88', '303,37,11.88', 1))
    refresh_sha(root, path.name)
    with pytest.raises(ValueError, match='Numerator'):
        AUDIT.audit(source, root, registry)


def test_missing_adult_age_rejected_even_if_receipt_is_unchanged(tmp_path: Path) -> None:
    source, root, registry = prepare(tmp_path)
    with zipfile.ZipFile(source) as z:
        raw = z.read(AUDIT.SOURCE_MEMBER).decode('utf-8-sig')
    missing = raw.replace('001001;Comune 1;50;1;2;3\n', '')
    with zipfile.ZipFile(source, 'w') as z:
        z.writestr(AUDIT.SOURCE_MEMBER, missing.encode('utf-8-sig'))
    with pytest.raises(ValueError, match='Missing original POSAS ages'):
        AUDIT.audit(source, root, registry)


def test_source_sex_mismatch_fails_before_manifest_check(tmp_path: Path) -> None:
    source, root, registry = prepare(tmp_path)
    with zipfile.ZipFile(source) as z:
        raw = z.read(AUDIT.SOURCE_MEMBER).decode('utf-8-sig')
    mismatch = raw.replace('001001;Comune 1;5;1;2;3\n', '001001;Comune 1;5;1;2;4\n')
    with zipfile.ZipFile(source, 'w') as z:
        z.writestr(AUDIT.SOURCE_MEMBER, mismatch.encode('utf-8-sig'))
    with pytest.raises(ValueError, match='sex-total mismatch'):
        AUDIT.audit(source, root, registry)


def test_false_sex_qa_claim_rejected(tmp_path: Path) -> None:
    source, root, registry = prepare(tmp_path)
    path = root / 'h47_preview/qa.json'
    qa = json.loads(path.read_text(encoding='utf-8'))
    qa['sex_totals_verified'] = False
    write_json(path, qa)
    refresh_sha(root, path.name)
    with pytest.raises(ValueError, match='Mandatory official sex totals'):
        AUDIT.audit(source, root, registry)


def test_missing_registry_code_rejected(tmp_path: Path) -> None:
    source, root, registry = prepare(tmp_path)
    path = root / 'h47_preview/population_0_11_preview.csv'
    lines = path.read_text(encoding='utf-8').splitlines()
    path.write_text('\n'.join(lines[:-1]) + '\n', encoding='utf-8')
    refresh_sha(root, path.name)
    with pytest.raises(ValueError, match='27 rows'):
        AUDIT.audit(source, root, registry)


def test_bad_weighted_share_rejected(tmp_path: Path) -> None:
    source, root, registry = prepare(tmp_path)
    qa_path = root / 'h47_preview/qa.json'
    qa = json.loads(qa_path.read_text(encoding='utf-8'))
    qa['green_community_weighted_share_pct'] = '11.99'
    write_json(qa_path, qa)
    refresh_sha(root, qa_path.name)
    with pytest.raises(ValueError, match='weighted aggregate'):
        AUDIT.audit(source, root, registry)


def test_cli_does_not_overwrite_prior_evidence(tmp_path: Path) -> None:
    source, root, registry = prepare(tmp_path)
    out = tmp_path / 'prior.json'
    out.write_text('{"preserved":true}', encoding='utf-8')
    result = subprocess.run([sys.executable, str(SCRIPT), '--source-zip', str(source),
        '--review-root', str(root), '--registry', str(registry), '--out-file', str(out)],
        capture_output=True, text=True, check=False)
    assert result.returncode != 0
    assert out.read_text(encoding='utf-8') == '{"preserved":true}'


def test_cli_generates_reproducible_review_report(tmp_path: Path) -> None:
    source, root, registry = prepare(tmp_path)
    out = tmp_path / 'audit.json'
    result = subprocess.run([sys.executable, str(SCRIPT), '--source-zip', str(source),
        '--review-root', str(root), '--registry', str(registry), '--out-file', str(out),
        '--expected-source-sha256', AUDIT.sha_file(source)],
        capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    obj = json.loads(out.read_text(encoding='utf-8'))
    assert obj['status'] == 'independently_reproduced_technical_only'
    assert obj['scientific_approval'] is False
