"""Prove that the hygiene inventory is conservative and never removes evidence."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from audit_repository_hygiene import audit, main, search_pattern


def fixture_repo(tmp_path: Path) -> Path:
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    fixtures = {
        'scripts/active.py': 'print("active")\n',
        'scripts/orphan.py': 'print("orphan")\n',
        'scripts/archive_only.py': 'print("historic")\n',
        'scripts/used_by_module.py': 'print("module")\n',
        'src/app.py': 'from scripts.used_by_module import main\n',
        '.github/workflows/ci.yml': 'run: python scripts/active.py\n',
        'docs/archive/old.md': 'Run archive_only.py\n',
        'docs/repository_hygiene.md': 'orphan.py, active.py\n',
        'data/quality/evidence.json': '{"approved": false}\n',
        'data/reference/evidence_copy.json': '{"approved": false}\n',
    }
    for path, contents in fixtures.items():
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(contents, encoding='utf-8')
    subprocess.run(['git', '-C', str(tmp_path), 'add', '-A'], check=True)
    return tmp_path


def test_classifies_entrypoints_and_no_reference_as_review_candidate(tmp_path):
    root = fixture_repo(tmp_path)
    result = audit(root)
    status = {item['path']: item for item in result['script_inventory']}
    assert status['scripts/active.py']['disposition'] == 'wired_or_production_referenced'
    assert status['scripts/used_by_module.py']['disposition'] == 'wired_or_production_referenced'
    assert status['scripts/archive_only.py']['disposition'] == 'archival_only_review_candidate'
    assert status['scripts/orphan.py']['disposition'] == 'no_static_reference_review_candidate'
    assert all(not item['safe_to_delete'] for item in status.values())
    assert status['scripts/orphan.py']['references'] == {}
    assert result['changes_made'] is False
    assert result['deletion_authorized'] is False


def test_duplicate_snapshots_are_preserved(tmp_path):
    root = fixture_repo(tmp_path)
    result = audit(root)
    assert len(result['identical_tracked_data_groups']) == 1
    group = result['identical_tracked_data_groups'][0]
    assert group['retain_for_provenance'] is True
    assert set(group['paths']) == {
        'data/quality/evidence.json', 'data/reference/evidence_copy.json'
    }
    assert (root / 'data/quality/evidence.json').exists()
    assert (root / 'data/reference/evidence_copy.json').exists()


def test_ignored_local_outputs_are_neither_inspected_nor_deleted(tmp_path):
    root = fixture_repo(tmp_path)
    ignored = root / 'outputs/private.csv'
    ignored.parent.mkdir()
    ignored.write_text('confidential', encoding='utf-8')
    result = audit(root)
    assert result['summary']['tracked_generated_paths'] == 0
    assert 'outputs/private.csv' not in {x['path'] for x in result['tracked_data']}
    assert ignored.read_text(encoding='utf-8') == 'confidential'


def test_check_fails_on_tracked_generated_data(tmp_path):
    root = fixture_repo(tmp_path)
    data = root / 'data/derived/produced.csv'
    data.parent.mkdir(parents=True)
    data.write_text('not canonical\n', encoding='utf-8')
    subprocess.run(['git', '-C', str(root), 'add', 'data/derived/produced.csv'], check=True)
    assert main(['--root', str(root), '--check']) == 1
    assert data.exists()


def test_read_only_default_and_json_no_overwrite(tmp_path):
    root = fixture_repo(tmp_path)
    before = subprocess.run(['git', '-C', str(root), 'status', '--porcelain'],
                            capture_output=True, text=True, check=True).stdout
    assert main(['--root', str(root), '--check']) == 0
    after = subprocess.run(['git', '-C', str(root), 'status', '--porcelain'],
                           capture_output=True, text=True, check=True).stdout
    assert after == before
    out = tmp_path / 'audit.json'
    assert main(['--root', str(root), '--json-out', str(out)]) == 0
    assert json.loads(out.read_text(encoding='utf-8'))['summary']['tracked_scripts'] == 4
    assert main(['--root', str(root), '--json-out', str(out)]) == 2
    assert json.loads(out.read_text(encoding='utf-8'))['deletion_authorized'] is False


def test_reference_regex_does_not_match_suffix_or_lookalike():
    pattern = search_pattern('scripts/build.py')
    assert pattern.search('python scripts/build.py')
    assert pattern.search('from scripts.build import main')
    assert not pattern.search('python scripts/rebuild.py')
    assert not pattern.search('build.py.backup')
    assert not pattern.search('some_build.py')


def test_current_repository_is_internally_safe_to_audit():
    # This check is an offline repository invariant, not a scientific QA assertion.
    if not (ROOT / '.git').exists():
        return
    report = audit(ROOT)
    assert report['summary']['tracked_scripts'] >= 70
    assert report['summary']['tracked_generated_paths'] == 0
    assert any(item['path'] == 'scripts/build_v0_2_territorial_report.py'
               for item in report['script_inventory'])
    assert all(not item['safe_to_delete'] for item in report['script_inventory'])
