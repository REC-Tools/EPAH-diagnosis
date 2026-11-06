"""Independently re-derive H47 from the original POSAS 2026 ZIP and audit QA artifacts.

This is a technical evidence check, not approval or canonical data promotion.
No repository data is modified. Fail closed and refuse to overwrite evidence.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import unicodedata
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / 'data/municipalities.csv'
SOURCE_URL = 'https://demo.istat.it/data/posas/POSAS_2026_it_Comuni.zip'
SOURCE_MEMBER = 'POSAS_2026_it_Comuni.csv'
TECHNICAL_STATUS = 'technical_draft_do_not_publish'
AGE_DOMAIN = set(range(101))
REQUIRED_COLUMNS = ('Codice comune', 'Comune', 'Età', 'Totale maschi', 'Totale femmine', 'Totale')
SHA = re.compile(r'[0-9a-f]{64}\Z')


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def norm(value: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', value.casefold())
                   if c.isalnum() and not unicodedata.combining(c))


def integer(value: str, context: str) -> int:
    value = value.strip()
    if not re.fullmatch(r'(?:\d+|\d{1,3}(?:\.\d{3})+)', value):
        raise ValueError(f'{context}: invalid nonnegative population count {value!r}')
    return int(value.replace('.', ''))


def read_registry(path: Path) -> dict[str, str]:
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not {'municipality', 'istat_code'} <= set(reader.fieldnames):
            raise ValueError('Registry must contain municipality and istat_code')
        result: dict[str, str] = {}
        for row in reader:
            code = (row.get('istat_code') or '').strip()
            name = (row.get('municipality') or '').strip()
            if not re.fullmatch(r'\d{6}', code) or code in result or not name:
                raise ValueError(f'Duplicate/invalid municipality registry key: {code!r}')
            result[code] = name
    if len(result) != 27:
        raise ValueError(f'Registry must contain exactly 27 municipalities, found {len(result)}')
    return result


def source_rows(zip_path: Path, member: str, registry: dict[str, str]) -> tuple[dict[str, dict[int, tuple[int, int, int]]], str, list[str]]:
    """Stream target municipality rows directly from ZIP, independent of H47 extractor."""
    if zip_path.stat().st_size > 100 * 1024 * 1024:
        raise ValueError('Source ZIP exceeds 100 MiB safety limit')
    with zipfile.ZipFile(zip_path) as archive:
        members = [x for x in archive.infolist() if x.filename.lower().endswith('.csv') and not x.is_dir()]
        if len(members) != 1 or members[0].filename != member:
            raise ValueError('Expected exactly one named POSAS 2026 CSV member')
        info = members[0]
        if info.file_size > 600 * 1024 * 1024:
            raise ValueError('CSV uncompressed size exceeds safety limit')
        with archive.open(info) as binary:
            raw = binary.read()
    raw_hash = digest(raw)
    try:
        content = raw.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise ValueError('Unexpected original CSV encoding (expected UTF-8 BOM)') from exc
    lines = content.splitlines()
    header_index = -1
    for i, line in enumerate(lines[:50]):
        cols = next(csv.reader([line], delimiter=';'))
        if set(REQUIRED_COLUMNS) <= {x.strip() for x in cols}:
            header_index = i
            break
    if header_index < 0:
        raise ValueError('Official POSAS male/female/total columns not found')
    if not any('2026' in line and ('stima' in line.lower() or 'provvisor' in line.lower())
               for line in lines[:header_index]):
        raise ValueError('POSAS original preamble does not explicitly identify provisional 2026 data')
    reader = csv.DictReader(io.StringIO('\n'.join(lines[header_index:])), delimiter=';')
    header = [x.strip() for x in (reader.fieldnames or [])]
    if len(header) != len(set(header)) or not set(REQUIRED_COLUMNS) <= set(header):
        raise ValueError('Missing or duplicate official CSV header')
    age_rows: dict[str, dict[int, tuple[int, int, int]]] = {code: {} for code in registry}
    for row in reader:
        raw_code = (row.get('Codice comune') or '').strip()
        if not raw_code.isdecimal():
            continue
        code = raw_code.zfill(6)
        if code not in registry:
            continue
        if None in row:
            raise ValueError(f'Extra malformed fields for {code}')
        observed_name = (row.get('Comune') or '').strip()
        if norm(observed_name) != norm(registry[code]):
            raise ValueError(f'Original POSAS registry name differs for {code}')
        age_txt = (row.get('Età') or '').strip()
        if not age_txt.isdecimal():
            raise ValueError(f'Invalid age for {code}: {age_txt!r}')
        age = int(age_txt)
        if age not in AGE_DOMAIN and age != 999:
            raise ValueError(f'Unsupported age {age} for {code}')
        if age in age_rows[code]:
            raise ValueError(f'Duplicate source age {age} for {code}')
        male = integer(row.get('Totale maschi') or '', f'{code} age {age} male')
        female = integer(row.get('Totale femmine') or '', f'{code} age {age} female')
        total = integer(row.get('Totale') or '', f'{code} age {age} total')
        if male + female != total:
            raise ValueError(f'Source sex-total mismatch for {code}, age {age}')
        age_rows[code][age] = (male, female, total)
    for code, ages in age_rows.items():
        missing = AGE_DOMAIN | {999}
        missing = missing - ages.keys()
        if missing:
            raise ValueError(f'Missing original POSAS ages for {code}: {sorted(missing)}')
        for col in range(3):
            subtotal = sum(ages[age][col] for age in range(101))
            if subtotal != ages[999][col]:
                raise ValueError(f'Original source age-total mismatch for {code}, component {col}')
        if ages[999][2] <= 0:
            raise ValueError(f'Zero denominator for {code}')
    return age_rows, raw_hash, header


def require_equal(actual: object, expected: object, message: str) -> None:
    if actual != expected:
        raise ValueError(f'{message}: got {actual!r}, expected {expected!r}')


def audit(source_zip: Path, review_root: Path, registry_path: Path,
          *, expected_source_sha256: str | None = None) -> dict[str, object]:
    original_hash = sha_file(source_zip)
    if expected_source_sha256:
        if not SHA.fullmatch(expected_source_sha256):
            raise ValueError('Expected ZIP SHA-256 must have 64 lowercase hex digits')
        require_equal(original_hash, expected_source_sha256, 'Official ZIP SHA-256 source drift')
    registry = read_registry(registry_path)
    original_rows, member_hash, columns = source_rows(source_zip, SOURCE_MEMBER, registry)
    observation = json.loads((review_root / 'source_observation.json').read_text(encoding='utf-8'))
    preview_path = review_root / 'h47_preview/population_0_11_preview.csv'
    qa_path = review_root / 'h47_preview/qa.json'
    manifest_path = review_root / 'h47_preview/manifest.json'
    qa = json.loads(qa_path.read_text(encoding='utf-8'))
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    for obj, label in ((observation, 'source receipt'), (qa, 'QA'), (manifest, 'manifest')):
        require_equal(obj.get('status'), TECHNICAL_STATUS, f'{label} technical-only status')
    require_equal(observation.get('scientific_approval'), False, 'Source receipt approval')
    require_equal(observation.get('publication_allowed'), False, 'Source receipt publication')
    require_equal(manifest.get('scientific_approval'), False, 'Manifest approval')
    require_equal(qa.get('sex_totals_verified'), True, 'Mandatory official sex totals reconciliation')
    require_equal(observation.get('original_zip_sha256'), original_hash, 'Source receipt ZIP SHA')
    require_equal(manifest.get('input_original_zip_sha256'), original_hash, 'Manifest ZIP SHA')
    require_equal(observation.get('csv_member'), SOURCE_MEMBER, 'Source receipt member')
    require_equal(manifest.get('input_zip_member'), SOURCE_MEMBER, 'Manifest member')
    require_equal(observation.get('csv_member_sha256'), member_hash, 'Source receipt member SHA')
    require_equal(manifest.get('input_member_sha256'), member_hash, 'Manifest member SHA')
    require_equal(manifest.get('municipality_registry_sha256'), sha_file(registry_path), 'Registry SHA')
    require_equal(observation.get('source_url_expected'), SOURCE_URL, 'Official source URL')
    require_equal(manifest.get('source_url'), SOURCE_URL, 'Manifest URL')
    require_equal(manifest.get('reference_date'), '2026-01-01', 'Manifest reference date')
    require_equal(observation.get('reference_date_proposed'), '2026-01-01', 'Receipt reference date')
    if not set(REQUIRED_COLUMNS) <= set(observation.get('csv_columns', [])):
        raise ValueError('Source receipt does not enumerate official sex columns')
    require_equal(qa.get('coverage'), '27/27', 'QA coverage')
    require_equal(qa.get('municipality_count'), 27, 'QA municipality count')
    for path in (preview_path, qa_path):
        require_equal(manifest['outputs_sha256'].get(path.name), sha_file(path), f'Output hash {path.name}')
    with preview_path.open(encoding='utf-8-sig', newline='') as stream:
        preview = list(csv.DictReader(stream))
    if len(preview) != 27:
        raise ValueError(f'Preview needs exactly 27 rows, got {len(preview)}')
    seen: set[str] = set()
    computed_children = computed_population = 0
    for row in preview:
        code = (row.get('municipality_code') or '').strip()
        if code not in registry or code in seen:
            raise ValueError(f'Unexpected or duplicated ISTAT code in preview: {code}')
        seen.add(code)
        require_equal(row.get('municipality'), registry[code], f'Preview registry name {code}')
        require_equal(row.get('reference_date'), '2026-01-01', f'Preview reference date {code}')
        require_equal(row.get('status'), TECHNICAL_STATUS, f'Preview status {code}')
        require_equal(row.get('source_url'), SOURCE_URL, f'Preview source URL {code}')
        expected_total = original_rows[code][999][2]
        expected_child = sum(original_rows[code][age][2] for age in range(12))
        require_equal(integer(row.get('population_total', ''), code), expected_total, f'Denominator {code}')
        require_equal(integer(row.get('population_0_11', ''), code), expected_child, f'Numerator {code}')
        require_equal(row.get('share_0_11_pct'), f'{expected_child / expected_total * 100:.2f}',
                      f'Rendered percentage {code}')
        computed_children += expected_child
        computed_population += expected_total
    if set(registry) != seen:
        raise ValueError('Preview missing registry municipalities')
    require_equal(qa.get('resident_0_11_total'), computed_children, 'QA child total')
    require_equal(qa.get('resident_population_total'), computed_population, 'QA population total')
    require_equal(qa.get('green_community_weighted_share_pct'),
                  f'{computed_children / computed_population * 100:.2f}', 'QA weighted aggregate')
    return {
        'status': 'independently_reproduced_technical_only',
        'indicator_id': 'population_0_11',
        'epah_inventory_id': 'H47',
        'reference_date': '2026-01-01',
        'municipality_coverage': '27/27',
        'original_source_zip_sha256': original_hash,
        'original_source_member_sha256': member_hash,
        'original_source_registry_sha256': sha_file(registry_path),
        'source_zip_sha_pinned': bool(expected_source_sha256),
        'population_total': computed_population,
        'population_0_11': computed_children,
        'weighted_share_0_11_pct': f'{computed_children / computed_population * 100:.2f}',
        'checks_passed': [
            'official_2026_preamble', 'complete_27_istat_registry',
            'complete_ages_0_to_100_plus_999', 'per_age_male_plus_female_equals_total',
            'per_municipality_sum_of_ages_equals_999_for_both_sexes_and_total',
            'preview_27_rows_match_original_by_istat_code', 'preview_numerators_denominators_exact',
            'rounded_percentages_recomputed', 'weighted_share_recomputed',
            'output_zip_member_and_registry_sha256_cross_checked',
            'technical_only_status_preserved', 'qa_sex_totals_verified_flag',
        ],
        'scientific_approval': False,
        'publication_allowed': False,
        'limitations': 'ISTAT POSAS 2026 estimated/provisional. This QA is code-based and not source-license or institutional approval. No direct household energy-poverty measurement.',
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-zip', type=Path, required=True)
    parser.add_argument('--review-root', type=Path, required=True,
                        help='Directory containing source_observation.json and h47_preview/')
    parser.add_argument('--registry', type=Path, default=REGISTRY)
    parser.add_argument('--out-file', type=Path, required=True)
    parser.add_argument('--expected-source-sha256', help='Pinned ZIP digest observed in initial official-source QA')
    args = parser.parse_args()
    if args.out_file.exists():
        parser.error(f'Refusing to overwrite existing independent audit: {args.out_file}')
    result = audit(args.source_zip, args.review_root, args.registry,
                   expected_source_sha256=args.expected_source_sha256)
    args.out_file.parent.mkdir(parents=True, exist_ok=True)
    args.out_file.write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + '\n',
                             encoding='utf-8')
    print(f"H47 independently reproduced: {result['municipality_coverage']}, "
          f"weighted {result['weighted_share_0_11_pct']}%, technical only; not approved")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
