"""Read-only, conservative inventory of tracked scripts and data artifacts.

A missing static reference is a REVIEW candidate, never evidence of safe removal.
Never follows ignored/untracked paths or deletes, moves, or rewrites inputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_SUFFIXES = frozenset({'.py', '.md', '.rst', '.toml', '.json', '.yaml', '.yml', '.sh', '.ps1', '.bat', '.txt'})
TRACKED_GENERATED = ('outputs/', 'artifacts/', 'data/derived/', 'data/downloads/', 'data/cache/', 'data/raw/')
# Avoid circular/self-advertising evidence: this guide will necessarily mention candidate script names.
AUDIT_META_FILES = frozenset({'docs/repository_hygiene.md', 'scripts/audit_repository_hygiene.py', 'tests/test_repository_hygiene.py'})


def tracked_files(root: Path) -> list[str]:
    result = subprocess.run(['git', '-C', str(root), 'ls-files', '-z', '--cached'],
                            capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError('git ls-files failed: ' + result.stderr.decode('utf-8', 'replace'))
    names = result.stdout.decode('utf-8', 'surrogateescape').split('\0')
    return sorted(name.replace('\\', '/') for name in names if name)


def ref_kind(path: str) -> str:
    if path.startswith('.github/workflows/'):
        return 'workflow'
    if path.startswith('src/'):
        return 'production_code'
    if path.startswith('scripts/'):
        return 'script_code'
    if path.startswith('tests/'):
        return 'test'
    if path.startswith('docs/archive/') or path.startswith('docs/releases/'):
        return 'historical_docs'
    if path.startswith('docs/') or path == 'README.md':
        return 'current_docs'
    if path.startswith('config/') or path == 'pyproject.toml':
        return 'configuration'
    return 'other_text'


def search_pattern(script_path: str) -> re.Pattern[str]:
    stem = Path(script_path).stem
    file_name = re.escape(Path(script_path).name)
    module = re.escape(stem)
    # Direct script name/path and Python module import are the static evidence we can audit.
    # Word boundaries reject suffix collisions, e.g. build.py vs build.py.backup.
    return re.compile(
        rf'(?<![\w.]){file_name}(?![\w.])|'
        rf'\b(?:from|import)\s+scripts\.{module}(?![\w.])'
    )


def data_group(path: str) -> str:
    if path.startswith(TRACKED_GENERATED):
        return 'generated_tracked_not_expected'
    if path == 'data/verification_matrix.csv' or path == 'data/municipalities.csv':
        return 'canonical_data_do_not_delete'
    if path.startswith('data/quality/'):
        return 'review_evidence_do_not_delete'
    if path.startswith('data/reference/'):
        return 'reference_or_archived_evidence_do_not_delete'
    if path.startswith('data/indicators/'):
        return 'indicator_data_do_not_delete'
    return 'other_tracked_data_review'


def audit(root: Path) -> dict:
    names = tracked_files(root)
    scripts = [p for p in names if p.startswith('scripts/') and p.endswith('.py')]
    documents = [p for p in names if p.endswith('.md')]
    tracked_generated = [p for p in names if p.startswith(TRACKED_GENERATED)]
    text = {}
    missing = []
    for name in names:
        if name in AUDIT_META_FILES or Path(name).suffix.lower() not in SCAN_SUFFIXES:
            continue
        path = root / name
        try:
            # Only scan files already tracked by Git; excluded local/private inputs are never scanned.
            text[name] = path.read_text(encoding='utf-8')
        except (UnicodeError, OSError):
            missing.append(name)

    summary = defaultdict(int)
    inventory = []
    for path in scripts:
        pattern = search_pattern(path)
        references = defaultdict(list)
        for source, body in text.items():
            if source == path or not pattern.search(body):
                continue
            references[ref_kind(source)].append(source)
        references = {k: sorted(set(v)) for k, v in sorted(references.items())}
        if references.get('workflow') or references.get('production_code') or references.get('configuration'):
            disposition = 'wired_or_production_referenced'
        elif references.get('script_code'):
            disposition = 'referenced_by_other_script'
        elif references.get('test'):
            disposition = 'test_referenced'
        elif references.get('current_docs'):
            disposition = 'documented_manual_entrypoint'
        elif references.get('historical_docs'):
            disposition = 'archival_only_review_candidate'
        elif references.get('other_text'):
            disposition = 'other_text_review_candidate'
        else:
            disposition = 'no_static_reference_review_candidate'
        summary[disposition] += 1
        inventory.append({
            'path': path,
            'disposition': disposition,
            'references': references,
            'safe_to_delete': False,
        })

    sha_groups = defaultdict(list)
    data_files = []
    for name in names:
        if not name.startswith('data/'):
            continue
        kind = data_group(name)
        data_files.append({'path': name, 'category': kind})
        file = root / name
        if file.is_file():
            try:
                # SHA-256 is only computed for the versioned data files, never ignored archives.
                sha = hashlib.sha256(file.read_bytes()).hexdigest()
                sha_groups[sha].append(name)
            except OSError:
                missing.append(name)
    duplicate_groups = [
        {'sha256': sha, 'paths': sorted(paths), 'retain_for_provenance': True}
        for sha, paths in sorted(sha_groups.items()) if len(paths) > 1
    ]
    duplicate_groups.sort(key=lambda group: group['paths'])
    review_candidates = [item['path'] for item in inventory
                         if item['disposition'].endswith('_review_candidate')]
    return {
        'schema_version': '1.0',
        'analysis': 'static tracked-file reference scan; not a runtime reachability proof',
        'changes_made': False,
        'deletion_authorized': False,
        'summary': {
            'tracked_scripts': len(scripts),
            'tracked_markdown': len(documents),
            'tracked_generated_paths': len(tracked_generated),
            'identical_tracked_data_groups': len(duplicate_groups),
            'review_candidates': len(review_candidates),
            'script_categories': dict(sorted(summary.items())),
        },
        'tracked_generated_paths': tracked_generated,
        'review_candidates': review_candidates,
        'script_inventory': inventory,
        'tracked_data': data_files,
        'identical_tracked_data_groups': duplicate_groups,
        'missing_or_unreadable_tracked_files': sorted(set(missing)),
        'cautions': [
            'No static reference does not prove a Python script is unused: CLI, manual invocations, and external users may exist.',
            'Archived snapshots can intentionally have identical bytes to reviewed indicator or QA files.',
            'data/indicators, data/reference and data/quality are not disposable cache directories.',
            'This tool has no deletion/move/promotion capability and does not inspect ignored/untracked original downloads.',
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT, help='Git working-tree root')
    parser.add_argument('--json-out', type=Path, help='Write a NEW machine-readable report; never overwrite')
    parser.add_argument('--check', action='store_true', help='Fail on tracked generated artifacts or inaccessible tracked files')
    args = parser.parse_args(argv)
    try:
        result = audit(args.root)
        summary = result['summary']
        print('EPAH repository hygiene (read-only; no deletion approved):')
        for key in ('tracked_scripts', 'tracked_markdown', 'tracked_generated_paths',
                    'identical_tracked_data_groups', 'review_candidates'):
            print(f"  {key}: {summary[key]}")
        print('  Script dispositions:')
        for name, count in summary['script_categories'].items():
            print(f'    {name}: {count}')
        for script in result['review_candidates']:
            print(f'  REVIEW candidate (not approved for deletion): {script}')
        for group in result['identical_tracked_data_groups']:
            print('  PRESERVE identical evidence: ' + ' | '.join(group['paths']))
        if args.json_out:
            # A caller chooses an existing directory; no arbitrary directory creation.
            with args.json_out.open('x', encoding='utf-8') as out:
                json.dump(result, out, ensure_ascii=False, indent=2, sort_keys=True)
                out.write('\n')
            print(f'  Report: {args.json_out}')
        if args.check and (result['tracked_generated_paths'] or result['missing_or_unreadable_tracked_files']):
            print('ERROR: unexpected tracked generated files or missing tracked files', file=sys.stderr)
            return 1
        return 0
    except (OSError, RuntimeError, ValueError, FileExistsError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
