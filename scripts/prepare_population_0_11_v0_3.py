"""Prepare a *technical-only* EPAH H47 (age 0-11) extract from local ISTAT POSAS ZIP.

No automatic download; no canonical indicator, matrix, or release modification.
Designed to fail closed on inconsistent totals and incomplete child-age data.
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
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "data" / "municipalities.csv"
SOURCE_URL = "https://demo.istat.it/data/posas/POSAS_2026_it_Comuni.zip"
REFERENCE_PAGE = "https://demo.istat.it/app/?i=POS"
STATUS = "technical_draft_do_not_publish"
# ISTAT POSAS 2026: single ages 0-99, terminal 100+ bin coded 100, and 999 total.
# Confirm original archive schema before treating any result as scientifically reviewed.
AGE_DOMAIN = frozenset(range(101))
TOTAL_AGE = 999


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalized(value: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", value.casefold())
        if c.isalnum() and not unicodedata.combining(c)
    )


def read_registry(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not {"municipality", "istat_code"} <= set(reader.fieldnames):
            raise ValueError("Registry needs municipality and istat_code columns")
        registry: dict[str, str] = {}
        names: set[str] = set()
        for row in reader:
            code = (row.get("istat_code") or "").strip()
            name = (row.get("municipality") or "").strip()
            if not re.fullmatch(r"\d{6}", code) or not name or code in registry or normalized(name) in names:
                raise ValueError(f"Invalid or duplicate registry code/name: {code!r}, {name!r}")
            registry[code] = name
            names.add(normalized(name))
    if not registry:
        raise ValueError("Empty municipality registry")
    return registry


def read_csv_from_zip(path: Path, member: str | None = None) -> tuple[str, str, str]:
    with zipfile.ZipFile(path) as archive:
        names = sorted(n for n in archive.namelist() if n.lower().endswith(".csv") and not n.endswith("/"))
        if not names:
            raise ValueError("POSAS archive has no CSV")
        if member is None:
            if len(names) != 1:
                raise ValueError(f"Archive has {len(names)} CSVs; pass --member explicitly")
            member = names[0]
        if member not in names:
            raise ValueError(f"CSV member {member!r} not present in ZIP")
        info = archive.getinfo(member)
        # Reject unexpectedly large decompression, not merely the compressed file size.
        if info.file_size > 600 * 1024 * 1024:
            raise ValueError("Unexpectedly large CSV member")
        raw = archive.read(member)
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    return text, member, sha256_bytes(raw)


def find_table(text: str) -> csv.DictReader:
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines[:50]):
        for sep in (";", ",", "\t"):
            cells = [c.strip().strip('"').casefold() for c in line.split(sep)]
            if len(cells) >= 4 and any("comune" in x for x in cells) and any(x in ("età", "eta") for x in cells) and any(x in ("totale", "tot_p", "tot") for x in cells):
                return csv.DictReader(io.StringIO("".join(lines[index:])), delimiter=sep)
    raise ValueError("Unable to find POSAS header (Comune, Età, Totale)")


def pick(fields: list[str], choices: tuple[str, ...]) -> str:
    normalized_fields = {x.strip().casefold(): x for x in fields if x}
    for item in choices:
        if item.casefold() in normalized_fields:
            return normalized_fields[item.casefold()]
    raise ValueError(f"Missing POSAS column {choices}; found {fields}")


def parse_population_count(value: str, municipality_code: str) -> int:
    # Dot grouping is allowed only as thousands; never turn 12.3 into 123.
    if not re.fullmatch(r"(?:\d+|\d{1,3}(?:\.\d{3})+)", value):
        raise ValueError(f"Invalid POSAS population count for {municipality_code}: {value!r}")
    return int(value.replace(".", ""))


def compute_child_shares(text: str, registry: dict[str, str]) -> list[dict[str, object]]:
    reader = find_table(text)
    fields = reader.fieldnames or []
    code_col = pick(fields, ("codice comune", "codice_comune", "codice", "pro_com_t"))
    name_col = pick(fields, ("comune", "denominazione", "nome comune"))
    age_col = pick(fields, ("età", "eta"))
    count_col = pick(fields, ("totale", "tot_p", "tot"))
    # Where both sexes are in the extract, independently reconcile each row.
    lookup = {field.strip().casefold(): field for field in fields if field}
    male_col = lookup.get("maschi")
    female_col = lookup.get("femmine")
    if bool(male_col) != bool(female_col):
        raise ValueError("POSAS sex columns incomplete: expected both Maschi and Femmine")
    observed: dict[str, dict[int, int]] = {code: {} for code in registry}
    source_names: dict[str, str] = {}
    for row in reader:
        if None in row:
            # The input may contain non-tabular lines; for a target code, reject ambiguity.
            raw_code = (row.get(code_col) or "").strip()
            if raw_code.isdigit() and raw_code.zfill(6) in registry:
                raise ValueError(f"Malformed POSAS row for {raw_code}")
            continue
        raw_code = (row.get(code_col) or "").strip()
        if not raw_code.isdigit():
            continue
        code = raw_code.zfill(6)
        if code not in registry:
            continue
        name = (row.get(name_col) or "").strip()
        if not name or normalized(name) != normalized(registry[code]):
            raise ValueError(f"Municipality mismatch for {code}: {name!r} vs registry {registry[code]!r}")
        age_text = (row.get(age_col) or "").strip()
        count_text = (row.get(count_col) or "").strip()
        if not re.fullmatch(r"\d+", age_text):
            raise ValueError(f"Invalid POSAS age for {code}: {age_text!r}")
        age = int(age_text)
        if age != TOTAL_AGE and age not in AGE_DOMAIN:
            raise ValueError(f"Unsupported POSAS age {age} for {code}; expected 0..100, 999")
        count = parse_population_count(count_text, code)
        if male_col and female_col:
            male = parse_population_count((row.get(male_col) or "").strip(), code)
            female = parse_population_count((row.get(female_col) or "").strip(), code)
            if male + female != count:
                raise ValueError(f"POSAS sex-total mismatch for {code}, age {age}")
        if age in observed[code]:
            raise ValueError(f"Duplicate age {age} for {code}")
        observed[code][age] = count
        source_names[code] = name
    result: list[dict[str, object]] = []
    for code, registry_name in sorted(registry.items()):
        ages = observed[code]
        missing = AGE_DOMAIN - ages.keys()
        if missing:
            child_missing = sorted(age for age in missing if age < 12)
            if child_missing:
                raise ValueError(f"Missing age 0-11 rows for {code}: {child_missing}")
            raise ValueError(f"Missing adult/older age rows for {code}: {sorted(missing)}")
        if TOTAL_AGE not in ages:
            raise ValueError(f"Missing explicit POSAS total (age 999) for {code}")
        population_total = sum(ages[age] for age in AGE_DOMAIN)
        if population_total == 0 or ages[TOTAL_AGE] != population_total:
            raise ValueError(f"POSAS total mismatch/zero for {code}: rows={population_total}, 999={ages[TOTAL_AGE]}")
        children = sum(ages[age] for age in range(12))
        result.append({
            "municipality_code": code,
            "municipality": registry_name,
            "population_total": population_total,
            "population_0_11": children,
            "share_0_11_pct": f"{children / population_total * 100:.2f}",
        })
    return result


def write_outputs(out_dir: Path, results: list[dict[str, object]], input_path: Path, registry_path: Path,
                  member: str, member_sha: str, reference_date: str) -> None:
    if out_dir.exists():
        raise FileExistsError(f"Preserve prior QA evidence; choose a new --out-dir: {out_dir}")
    # Do not claim 27-Comune completeness from a smaller or modified local registry.
    if len(results) != 27:
        raise ValueError(f"Expected 27 municipalities, found {len(results)}")
    total = sum(int(r["population_total"]) for r in results)
    children = sum(int(r["population_0_11"]) for r in results)
    out_dir.mkdir(parents=True)
    csv_path = out_dir / "population_0_11_preview.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=(
            "municipality_code", "municipality", "reference_date", "population_total",
            "population_0_11", "share_0_11_pct", "source_url", "status"
        ), lineterminator="\n")
        writer.writeheader()
        for row in results:
            writer.writerow({**row, "reference_date": reference_date, "source_url": SOURCE_URL, "status": STATUS})
    qa = {
        "status": STATUS,
        "epah_inventory_id": "H47",
        "indicator_id_proposed": "population_0_11",
        "indicator_role": "sociodemographic_vulnerability_proxy",
        "municipality_count": 27,
        "coverage": "27/27",
        "resident_0_11_total": children,
        "resident_population_total": total,
        "green_community_weighted_share_pct": f"{children / total * 100:.2f}",
        "checks": ["unique_istat_codes", "name_code_match", "complete_ages_0_to_100_inclusive",
                   "age_100_plus_group_checked", "unique_age_rows",
                   "total_999_equals_age_sum", "sex_totals_if_available", "nonzero_denominator"],
        "limitations": "2026 POSAS is provisional/estimated; proxy, not household energy poverty. Local ZIP provenance and scientific review still needed.",
    }
    qa_path = out_dir / "qa.json"
    qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "status": STATUS,
        "source_page": REFERENCE_PAGE,
        "source_url": SOURCE_URL,
        "reference_date": reference_date,
        "input_original_zip_sha256": sha256_file(input_path),
        "input_zip_member": member,
        "input_member_sha256": member_sha,
        "municipality_registry_sha256": sha256_file(registry_path),
        "outputs_sha256": {p.name: sha256_file(p) for p in (csv_path, qa_path)},
        "canonical_registry_modified": False,
        "scientific_approval": False,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-zip", type=Path, required=True, help="Official POSAS ZIP already downloaded locally")
    parser.add_argument("--out-dir", type=Path, required=True, help="New output folder; existing folders are preserved")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--member", help="Exact CSV member name if ZIP contains multiple CSVs")
    parser.add_argument("--reference-date", default="2026-01-01")
    parser.add_argument("--expected-sha256", help="Known SHA-256 of the source ZIP, if independently available")
    args = parser.parse_args()
    try:
        date.fromisoformat(args.reference_date)
    except ValueError:
        parser.error("--reference-date must be a valid ISO date")
    if args.reference_date != "2026-01-01":
        parser.error("This source URL is POSAS 2026; --reference-date must be 2026-01-01")
    if args.out_dir.exists():
        parser.error("Output directory already exists (non-overwrite policy)")
    if args.expected_sha256 and sha256_file(args.source_zip) != args.expected_sha256.lower():
        parser.error("Source ZIP hash mismatch")
    registry = read_registry(args.registry)
    if len(registry) != 27:
        parser.error(f"Expected exactly 27 municipality registry entries; found {len(registry)}")
    text, member, member_sha = read_csv_from_zip(args.source_zip, args.member)
    results = compute_child_shares(text, registry)
    write_outputs(args.out_dir, results, args.source_zip, args.registry, member, member_sha, args.reference_date)
    print(f"Prepared {len(results)} POSAS 0-11 municipal previews in {args.out_dir}")
    print("Status: technical_draft_do_not_publish (no canonical validation or promotion)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
