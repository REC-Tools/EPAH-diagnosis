"""Regression tests for the metadata-only EPAH v0.3 evidence intake."""
from __future__ import annotations

import csv
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / 'data/reference'
FILES = (
    'epah_v0_3_mapping.csv', 'epah_v0_3_sources.csv',
    'epah_v0_3_priorities.csv', 'epah_v0_3_crosswalk.csv',
)


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def check(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / 'scripts/check_v0_3_evidence.py'), '--root', str(root)],
        capture_output=True, text=True, check=False,
    )


def prepared(tmp_path: Path) -> Path:
    dest = tmp_path / 'data/reference'
    dest.mkdir(parents=True)
    for filename in FILES:
        shutil.copy2(REFERENCE / filename, dest / filename)
    (tmp_path / 'config').mkdir()
    shutil.copy2(ROOT / 'config/indicators.json', tmp_path / 'config/indicators.json')
    return tmp_path


def update(path: Path, modify) -> None:
    with path.open(encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        records = list(reader)
    assert headers
    modify(records)
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers, lineterminator='\n')
        writer.writeheader()
        writer.writerows(records)


def test_registry_has_expected_rows_and_no_promoted_evidence() -> None:
    counts = dict(zip(FILES, (56, 35, 12, 9)))
    for filename, expected in counts.items():
        assert len(rows(REFERENCE / filename)) == expected
    indicators = rows(REFERENCE / FILES[0])
    sources = rows(REFERENCE / FILES[1])
    assert {r['ID interno'] for r in indicators} == {f'H{i:02}' for i in range(1, 57)}
    assert {r['ID fonte'] for r in sources} == {f'F{i:02}' for i in range(1, 36)}
    for filename in FILES[:3]:
        assert {r['stato_evidenza'] for r in rows(REFERENCE / filename)} == {'source_identified'}
    assert {r['verification_status'] for r in rows(REFERENCE / FILES[3])} == {
        'conceptual_mapping_pending_review'
    }
    assert {r['correspondence'] for r in rows(REFERENCE / FILES[3])} <= {
        'partial_proxy', 'related_not_equivalent', 'no_counterpart'
    }


def test_offline_validator_accepts_intact_registry() -> None:
    result = check(ROOT)
    assert result.returncode == 0, result.stdout + result.stderr


def test_duplicate_source_id_is_rejected(tmp_path: Path) -> None:
    root = prepared(tmp_path)
    update(root / 'data/reference' / FILES[1], lambda rs: rs[1].__setitem__('ID fonte', 'F01'))
    assert 'duplicate source ID' in check(root).stdout


def test_unknown_source_link_is_rejected(tmp_path: Path) -> None:
    root = prepared(tmp_path)
    update(root / 'data/reference' / FILES[0], lambda rs: rs[0].__setitem__('Fonti', 'F99'))
    assert 'unknown source F99' in check(root).stdout


def test_source_identified_cannot_be_promoted_by_editing_csv(tmp_path: Path) -> None:
    root = prepared(tmp_path)
    update(root / 'data/reference' / FILES[1], lambda rs: rs[0].__setitem__('stato_evidenza', 'human_approved'))
    result = check(root)
    assert result.returncode != 0
    assert 'not authorized for this intake' in result.stdout


def test_missing_provenance_is_rejected(tmp_path: Path) -> None:
    root = prepared(tmp_path)
    update(root / 'data/reference' / FILES[0], lambda rs: rs[0].__setitem__('workbook_sha256', ''))
    assert 'missing workbook_sha256' in check(root).stdout


def test_invalid_priority_range_reference_is_rejected(tmp_path: Path) -> None:
    root = prepared(tmp_path)
    update(root / 'data/reference' / FILES[2], lambda rs: rs[0].__setitem__('ID matrice', 'H55–H57'))
    assert 'unknown H reference H57' in check(root).stdout


def test_crosswalk_cannot_claim_exact_match(tmp_path: Path) -> None:
    root = prepared(tmp_path)
    update(root / 'data/reference' / FILES[3], lambda rs: rs[0].__setitem__('correspondence', 'direct_match'))
    assert 'invalid correspondence' in check(root).stdout


def test_crosswalk_matches_current_source_registry(tmp_path: Path) -> None:
    root = prepared(tmp_path)
    update(root / 'data/reference' / FILES[3], lambda rs: rs[0].__setitem__('repository_source_ids', 'nonexistent_source'))
    assert 'sources differ from config/indicators.json' in check(root).stdout
