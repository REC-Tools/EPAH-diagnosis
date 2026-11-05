"""H47/0-11 technical candidate: no network, no canonical data writes."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/prepare_population_0_11_v0_3.py"
SPEC = importlib.util.spec_from_file_location("prepare_population_0_11_v0_3", SCRIPT)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def make_posas(registry: dict[str, str], *, missing_age: bool = False, duplicate: bool = False,
               mismatch: bool = False, wrong_total: bool = False) -> str:
    result = ['ISTAT - POSAS descrizione tecnica\n', 'Codice Comune;Comune;Età;Totale\n']
    for code, name in registry.items():
        for age in range(13):
            if missing_age and age == 10 and code == next(iter(registry)):
                continue
            result.append(f'{code};{name};{age};1\n')
            if duplicate and age == 8 and code == next(iter(registry)):
                result.append(f'{code};{name};{age};1\n')
        result.append(f'{code};{name};999;{14 if wrong_total else 13}\n')
    return ''.join(result)


def make_registry_file(path: Path, count: int = 27) -> dict[str, str]:
    registry = {f'001{i:03d}': f'Comune {i}' for i in range(1, count + 1)}
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(['municipality', 'istat_code'])
        writer.writerows((name, code) for code, name in registry.items())
    return registry


def make_zip(path: Path, text: str, *, two_members: bool = False) -> None:
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr('POSAS_2026_it_Comuni.csv', text.encode('utf-8'))
        if two_members:
            archive.writestr('another.csv', text.encode('utf-8'))


def run_cli(tmp_path: Path, *, wrong_hash: bool = False, two_members: bool = False,
            missing_age: bool = False, output_exists: bool = False) -> tuple[subprocess.CompletedProcess[str], Path]:
    registry_path = tmp_path / 'municipalities.csv'
    registry = make_registry_file(registry_path)
    z = tmp_path / 'POSAS_2026_it_Comuni.zip'
    make_zip(z, make_posas(registry, missing_age=missing_age), two_members=two_members)
    output = tmp_path / 'output'
    if output_exists:
        output.mkdir()
        (output / 'keep.txt').write_text('preserve', encoding='utf-8')
    digest = '0' * 64 if wrong_hash else hashlib.sha256(z.read_bytes()).hexdigest()
    process = subprocess.run([sys.executable, str(SCRIPT), '--source-zip', str(z), '--out-dir',
                              str(output), '--registry', str(registry_path), '--reference-date',
                              '2026-01-01', '--expected-sha256', digest],
                             capture_output=True, text=True, check=False)
    return process, output


def test_0_11_correct_denominator_999_excluded() -> None:
    data = mod.compute_child_shares(make_posas({'001007': 'Alpette'}), {'001007': 'Alpette'})
    assert len(data) == 1
    assert data[0]['population_total'] == 13
    assert data[0]['population_0_11'] == 12
    assert data[0]['share_0_11_pct'] == '92.31'


def test_municipal_names_compare_accent_insensitively() -> None:
    data = mod.compute_child_shares(make_posas({'001098': 'Cuorgne'}), {'001098': 'Cuorgnè'})
    assert data[0]['municipality'] == 'Cuorgnè'


@pytest.mark.parametrize(('fault', 'message'), [
    ({'missing_age': True}, 'Missing age 0-11'),
    ({'duplicate': True}, 'Duplicate age'),
    ({'wrong_total': True}, 'POSAS total mismatch'),
])
def test_rejects_incomplete_duplicate_or_inconsistent_rows(fault, message) -> None:
    with pytest.raises(ValueError, match=message):
        mod.compute_child_shares(make_posas({'001007': 'Alpette'}, **fault), {'001007': 'Alpette'})


def test_code_name_mismatch_fails_closed() -> None:
    with pytest.raises(ValueError, match='Municipality mismatch'):
        mod.compute_child_shares(make_posas({'001007': 'Alpette'}), {'001007': 'Other name'})


def test_new_dir_produces_27_rows_and_provenance(tmp_path: Path) -> None:
    process, output = run_cli(tmp_path)
    assert process.returncode == 0, process.stderr
    csv_file = output / 'population_0_11_preview.csv'
    with csv_file.open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 27
    assert rows[0]['municipality_code'] == '001001'
    assert rows[0]['population_total'] == '13'
    assert rows[0]['population_0_11'] == '12'
    assert all(row['status'] == mod.STATUS for row in rows)
    qa = json.loads((output / 'qa.json').read_text(encoding='utf-8'))
    manifest = json.loads((output / 'manifest.json').read_text(encoding='utf-8'))
    assert qa['green_community_weighted_share_pct'] == '92.31'
    assert qa['status'] == mod.STATUS
    assert qa['epah_inventory_id'] == 'H47'
    assert manifest['scientific_approval'] is False
    assert manifest['outputs_sha256']['population_0_11_preview.csv'] == hashlib.sha256(csv_file.read_bytes()).hexdigest()


def test_old_output_directory_must_not_be_overwritten(tmp_path: Path) -> None:
    process, out = run_cli(tmp_path, output_exists=True)
    assert process.returncode != 0
    assert (out / 'keep.txt').read_text(encoding='utf-8') == 'preserve'


def test_wrong_original_sha_blocks_without_output(tmp_path: Path) -> None:
    process, out = run_cli(tmp_path, wrong_hash=True)
    assert process.returncode != 0
    assert 'hash mismatch' in process.stderr
    assert not out.exists()


def test_missing_age_blocks_without_output(tmp_path: Path) -> None:
    process, out = run_cli(tmp_path, missing_age=True)
    assert process.returncode != 0
    assert not out.exists()


def test_ambiguous_zip_requires_member_selection(tmp_path: Path) -> None:
    process, out = run_cli(tmp_path, two_members=True)
    assert process.returncode != 0
    assert 'pass --member' in process.stderr
    assert not out.exists()


def test_unexpected_registry_size_blocks_before_writing(tmp_path: Path) -> None:
    rfile = tmp_path / 'registry.csv'
    rows = make_registry_file(rfile, count=2)
    zfile = tmp_path / 'source.zip'
    make_zip(zfile, make_posas(rows))
    out = tmp_path / 'out'
    process = subprocess.run([sys.executable, str(SCRIPT), '--source-zip', str(zfile),
                              '--registry', str(rfile), '--out-dir', str(out)],
                             capture_output=True, text=True, check=False)
    assert process.returncode != 0
    assert 'Expected exactly 27' in process.stderr
    assert not out.exists()


def test_wrong_reference_year_rejected_for_2026_source(tmp_path: Path) -> None:
    registry_path = tmp_path / 'municipalities.csv'
    registry = make_registry_file(registry_path)
    z = tmp_path / 'source.zip'
    make_zip(z, make_posas(registry))
    out = tmp_path / 'out'
    process = subprocess.run([sys.executable, str(SCRIPT), '--source-zip', str(z),
                              '--registry', str(registry_path), '--out-dir', str(out),
                              '--reference-date', '2027-01-01'],
                             capture_output=True, text=True, check=False)
    assert process.returncode != 0
    assert 'must be 2026-01-01' in process.stderr
    assert not out.exists()
