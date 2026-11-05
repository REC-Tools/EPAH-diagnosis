"""Offline schema/provenance checks for the v0.3 evidence registry, not scientific approval."""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DATA = Path('data/reference')
FILES = {
    'mapping': ('epah_v0_3_mapping.csv', 56, 'Matrice_EPAH'),
    'sources': ('epah_v0_3_sources.csv', 35, 'Fonti'),
    'priorities': ('epah_v0_3_priorities.csv', 12, 'Priorita_v03'),
}
CROSSWALK = 'epah_v0_3_crosswalk.csv'
ALLOWED_EVIDENCE_STATES = frozenset({
    'source_identified', 'source_reviewed', 'data_acquired',
    'data_qa_passed', 'human_approved',
})
# This intake has only identified sources: all later states require a separate review.
INTAKE_STATE = 'source_identified'
ALLOWED_CORRESPONDENCE = frozenset({'partial_proxy', 'related_not_equivalent', 'no_counterpart'})
PROVENANCE = ('stato_evidenza', 'workbook_sha256', 'foglio_origine', 'riga_origine')
REF = re.compile(r'^(H|F)(\d{2})(?:\s*[–-]\s*(?:H|F)?(\d{2}))?$')
SHA = re.compile(r'^[0-9a-f]{64}$')


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str], list[str]]:
    if not path.is_file():
        return [], [], [f'Missing {path}']
    try:
        with path.open('r', encoding='utf-8', newline='') as handle:
            reader = csv.DictReader(handle)
            headers = reader.fieldnames or []
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error) as exc:
        return [], [], [f'{path}: {exc}']
    errors = []
    if len(headers) != len(set(headers)) or not headers:
        errors.append(f'{path}: duplicate or missing headers')
    if any(None in row or any(v is None for v in row.values()) for row in rows):
        errors.append(f'{path}: malformed rows')
    return rows, headers, errors


def references(value: str, prefix: str, location: str, errors: list[str]) -> list[str]:
    found = []
    for item in value.split(';'):
        item = item.strip()
        if not item:
            continue
        m = REF.fullmatch(item)
        if not m or m.group(1) != prefix:
            errors.append(f'{location}: invalid {prefix} reference {item!r}')
            continue
        start = int(m.group(2))
        end = int(m.group(3) or m.group(2))
        if not 1 <= start <= end <= 99:
            errors.append(f'{location}: invalid range {item!r}')
            continue
        found.extend(f'{prefix}{n:02}' for n in range(start, end + 1))
    return found


def require(row: dict[str, str], keys: tuple[str, ...], location: str, errors: list[str]) -> None:
    for key in keys:
        if not row.get(key, '').strip():
            errors.append(f'{location}: missing {key}')


def validate_registry(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    tables: dict[str, list[dict[str, str]]] = {}
    hashes: set[str] = set()
    for key, (filename, expected, sheet) in FILES.items():
        rows, headers, read_errors = read_csv(root / DATA / filename)
        errors.extend(read_errors)
        tables[key] = rows
        if len(rows) != expected:
            errors.append(f'{filename}: expected {expected} records, found {len(rows)}')
        for field in PROVENANCE:
            if field not in headers:
                errors.append(f'{filename}: missing column {field}')
        seen_rows: set[str] = set()
        for i, row in enumerate(rows, 2):
            loc = f'{filename}:{i}'
            require(row, PROVENANCE, loc, errors)
            state = row.get('stato_evidenza', '')
            if state not in ALLOWED_EVIDENCE_STATES or state != INTAKE_STATE:
                errors.append(f'{loc}: evidence {state!r} not authorized for this intake')
            digest = row.get('workbook_sha256', '')
            if not SHA.fullmatch(digest):
                errors.append(f'{loc}: invalid workbook SHA-256')
            else:
                hashes.add(digest)
            if row.get('foglio_origine') != sheet:
                errors.append(f'{loc}: wrong sheet provenance')
            raw_row = row.get('riga_origine', '')
            if not raw_row.isdigit() or int(raw_row) < (7 if key == 'priorities' else 2):
                errors.append(f'{loc}: invalid original row')
            if raw_row in seen_rows:
                errors.append(f'{loc}: repeated original row')
            seen_rows.add(raw_row)
    if len(hashes) != 1:
        errors.append('Intake CSVs must share one workbook SHA-256')

    source_ids = {f'F{i:02}' for i in range(1, 36)}
    indicator_ids = {f'H{i:02}' for i in range(1, 57)}
    sources = tables['sources']
    mapping = tables['mapping']
    if {r.get('ID fonte') for r in sources} != source_ids:
        errors.append('Sources: F01-F35 must occur exactly once')
    if len({r.get('ID fonte') for r in sources}) != len(sources):
        errors.append('Sources: duplicate source ID')
    if {r.get('ID interno') for r in mapping} != indicator_ids:
        errors.append('Mapping: H01-H56 must occur exactly once')
    if len({r.get('ID interno') for r in mapping}) != len(mapping):
        errors.append('Mapping: duplicate indicator ID')
    for row in sources:
        loc = f"source {row.get('ID fonte', '?')}"
        require(row, ('Ente', 'Dataset / punto di accesso', 'Scala',
                      'Periodo / aggiornamento', 'Verifica svolta', 'URL fonte',
                      'Limiti e istruzioni d’uso', 'Consultato il'), loc, errors)
        for field in ('URL fonte', 'URL dati / metadati'):
            link = row.get(field, '').strip()
            if link and (urlsplit(link).scheme not in ('http', 'https') or not urlsplit(link).netloc):
                errors.append(f'{loc}: invalid {field}')
    for row in mapping:
        loc = f"indicator {row.get('ID interno', '?')}"
        require(row, ('Area', 'Indicatore della guida (sintesi)', 'Pagina guida',
                      'Ruolo nella diagnosi', 'Fonti', 'Reperibilità per il progetto',
                      'Dati individuati', 'Limiti e verifica successiva'), loc, errors)
        for ref in references(row.get('Fonti', ''), 'F', loc, errors):
            if ref not in source_ids:
                errors.append(f'{loc}: unknown source {ref}')
    for row in tables['priorities']:
        loc = f"priority {row.get('Indicatore / gruppo', '?')}"
        require(row, ('Fase proposta', 'Indicatore / gruppo', 'ID matrice',
                      'Fonti', 'Dato da produrre', 'Condizione prima dell’integrazione'), loc, errors)
        for field, prefix, allowed in (('ID matrice', 'H', indicator_ids), ('Fonti', 'F', source_ids)):
            for ref in references(row.get(field, ''), prefix, loc, errors):
                if ref not in allowed:
                    errors.append(f'{loc}: unknown {prefix} reference {ref}')

    try:
        catalog = json.loads((root / 'config/indicators.json').read_text(encoding='utf-8'))
        existing = {x['id']: x for x in catalog['indicators']}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return errors + [f'Invalid canonical indicator catalog: {exc}']
    crosswalk, headers, read_errors = read_csv(root / DATA / CROSSWALK)
    errors.extend(read_errors)
    necessary = ('repository_indicator_id', 'epah_reference_ids', 'correspondence',
                 'definition_completeness', 'repository_universe', 'repository_denominator',
                 'epah_universe', 'epah_denominator', 'universe_and_denominator_difference',
                 'municipality_coverage', 'repository_source_ids', 'epah_source_ids',
                 'repository_reference_period', 'epah_reference_period',
                 'verification_status', 'methodological_note')
    for field in necessary:
        if field not in headers:
            errors.append(f'{CROSSWALK}: missing column {field}')
    if len(crosswalk) != len(existing) or {r.get('repository_indicator_id') for r in crosswalk} != set(existing):
        errors.append('Crosswalk must contain exactly the nine canonical indicator IDs')
    if len({r.get('repository_indicator_id') for r in crosswalk}) != len(crosswalk):
        errors.append('Crosswalk: duplicate indicator ID')
    for row in crosswalk:
        loc = f"crosswalk {row.get('repository_indicator_id', '?')}"
        require(row, tuple(k for k in necessary if k not in ('epah_reference_ids', 'epah_source_ids')), loc, errors)
        relation = row.get('correspondence')
        if relation not in ALLOWED_CORRESPONDENCE:
            errors.append(f'{loc}: invalid correspondence {relation!r}')
        if row.get('verification_status') != 'conceptual_mapping_pending_review':
            errors.append(f'{loc}: conceptual mapping must remain pending review')
        refs = references(row.get('epah_reference_ids', ''), 'H', loc, errors)
        if (relation == 'no_counterpart') != (not refs):
            errors.append(f'{loc}: counterpart/reference mismatch')
        for ref in refs:
            if ref not in indicator_ids:
                errors.append(f'{loc}: unknown EPAH {ref}')
        for ref in references(row.get('epah_source_ids', ''), 'F', loc, errors):
            if ref not in source_ids:
                errors.append(f'{loc}: unknown source {ref}')
        indicator = existing.get(row.get('repository_indicator_id'))
        if indicator:
            actual_sources = {part.strip() for part in row.get('repository_source_ids', '').split(';') if part.strip()}
            if actual_sources != set(indicator['source_ids']):
                errors.append(f'{loc}: repository sources differ from config/indicators.json')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    errors = validate_registry(args.root)
    if errors:
        for issue in errors:
            print('ERROR:', issue)
        return 1
    print('EPAH v0.3 evidence intake OK: 56 indicators, 35 sources, 12 priorities, 9 conceptual crosswalk rows; zero data promotions.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
