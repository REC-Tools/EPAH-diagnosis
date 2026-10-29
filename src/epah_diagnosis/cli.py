from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

from .model import INDICATORS, VerificationStatus

REPO_ROOT = Path(__file__).resolve().parents[2]


MATRIX_FIELDS = [
    "municipality",
    "indicator_id",
    "indicator_name",
    "macro_area",
    "status",
    "source_priority",
    "year",
    "territorial_level",
    "unit",
    "source_url",
    "value",
    "quality",
    "limitations",
    "notes",
]


def read_municipalities(path: Path) -> list[str]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(handle)
        municipalities = [row["municipality"].strip() for row in rows if row["municipality"].strip()]
    if len(municipalities) != len(set(municipalities)):
        raise ValueError("Municipality list contains duplicates.")
    with path.open(encoding="utf-8", newline="") as handle:
        has_codes = "istat_code" in (csv.DictReader(handle).fieldnames or [])
    if has_codes:
        read_municipality_codes(path)
    return municipalities


def read_municipality_codes(path: Path) -> dict[str, str]:
    """Read the canonical, versioned name -> six-digit ISTAT code mapping."""
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not {"municipality", "istat_code"} <= set(reader.fieldnames):
            raise ValueError("Municipality registry requires municipality and istat_code columns")
        records = list(reader)
    if not records:
        raise ValueError("Municipality registry is empty")
    mapping: dict[str, str] = {}
    used_codes: set[str] = set()
    for line, record in enumerate(records, start=2):
        name = (record.get("municipality") or "").strip()
        code = (record.get("istat_code") or "").strip()
        if not name or not re.fullmatch(r"[0-9]{6}", code):
            raise ValueError(f"Invalid municipality name or six-digit ISTAT code at line {line}")
        if name.casefold() in {key.casefold() for key in mapping} or code in used_codes:
            raise ValueError(f"Duplicate municipality name or ISTAT code at line {line}")
        mapping[name] = code
        used_codes.add(code)
    return mapping


def read_catalog_items(path: Path) -> list[dict]:
    """Return unique, complete indicator definitions from the canonical catalog."""
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data["indicators"]
    ids = [item["id"] for item in items]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError("Catalog must contain distinct indicator IDs.")
    for item in items:
        if not all(item.get(field) for field in ("id", "name", "dimension", "unit")):
            raise ValueError("Catalog indicator requires id, name, dimension and unit")
    return items


def build_matrix(municipalities: list[str], catalog: Path | None = None) -> list[dict[str, str]]:
    """Build a fresh matrix. Legacy 3-indicator mode is kept for existing API callers.

    CLI initialization uses the full canonical catalog by default.
    """
    if catalog is None:
        descriptors = [
            {
                "id": item.id, "name": item.name, "dimension": item.macro_area,
                "source_priority": item.preferred_source, "unit": item.unit,
            }
            for item in INDICATORS
        ]
    else:
        descriptors = [
            {
                "id": item["id"], "name": item["name"], "dimension": item["dimension"],
                "source_priority": " / ".join(item.get("source_ids", [])),
                "unit": {
                    "m": "m s.l.m.", "minutes": "minuti", "class": "classe A-F"
                }.get(item["unit"], item["unit"]),
            }
            for item in read_catalog_items(catalog)
        ]
    records: list[dict[str, str]] = []
    for municipality in municipalities:
        for descriptor in descriptors:
            records.append(
                {
                    "municipality": municipality,
                    "indicator_id": descriptor["id"],
                    "indicator_name": descriptor["name"],
                    "macro_area": descriptor["dimension"],
                    "status": VerificationStatus.TO_VERIFY.value,
                    "source_priority": descriptor["source_priority"],
                    "year": "",
                    "territorial_level": "Comune",
                    "unit": descriptor["unit"],
                    "source_url": "",
                    "value": "",
                    "quality": "",
                    "limitations": "",
                    "notes": "",
                }
            )
    return records


def write_matrix(records: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MATRIX_FIELDS)
        writer.writeheader()
        writer.writerows(records)


def read_catalog_ids(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data["indicators"]
    ids = [item["id"] for item in items]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError("Catalog must contain distinct indicator IDs.")
    return ids


def validate_matrix(path: Path, catalog_path: Path | None = None) -> tuple[int, int, list[str]]:
    allowed_statuses = {status.value for status in VerificationStatus}
    errors: list[str] = []
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    ids = read_catalog_ids(catalog_path) if catalog_path else [i.id for i in INDICATORS]
    valid_ids = set(ids)
    municipalities = {row["municipality"] for row in rows}
    expected = len(municipalities) * len(ids)
    seen: set[tuple[str, str]] = set()

    for line_number, row in enumerate(rows, start=2):
        key = (row["municipality"], row["indicator_id"])
        if not key[0] or not key[1]:
            errors.append(f"line {line_number}: missing municipality or indicator")
        if key in seen:
            errors.append(f"line {line_number}: duplicate municipality-indicator {key}")
        seen.add(key)
        if row["status"] not in allowed_statuses:
            errors.append(f"line {line_number}: invalid status '{row['status']}'")
        if row["indicator_id"] not in valid_ids:
            errors.append(f"line {line_number}: unknown indicator '{row['indicator_id']}'")

    if len(rows) != expected:
        errors.append(f"expected {expected} municipality-indicator rows, found {len(rows)}")
    missing = {(name, iid) for name in municipalities for iid in ids} - seen
    if missing:
        errors.append(f"missing {len(missing)} municipality-indicator combinations")

    return len(municipalities), len(rows), errors


def main() -> None:
    parser = argparse.ArgumentParser(description="EPAH diagnosis data utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init-matrix", help="Create a verification matrix")
    init_parser.add_argument("--municipalities", type=Path, required=True)
    init_parser.add_argument("--output", type=Path, required=True)
    init_parser.add_argument("--catalog", type=Path, help="Canonical catalog (default: config/indicators.json)")
    init_parser.add_argument("--legacy-three-indicators", action="store_true", help="Explicitly use the old 3-indicator schema")

    validate_parser = subparsers.add_parser("validate-matrix", help="Validate an existing matrix")
    validate_parser.add_argument("matrix", type=Path)
    validate_parser.add_argument("--catalog", type=Path, help="Validate against the complete methodology catalog")

    args = parser.parse_args()

    if args.command == "init-matrix":
        if args.output.exists():
            parser.error(f"Refusing to overwrite existing matrix: {args.output}")
        if args.legacy_three_indicators and args.catalog:
            parser.error("--legacy-three-indicators cannot be combined with --catalog")
        try:
            municipalities = read_municipalities(args.municipalities)
            selected_catalog = (
                None if args.legacy_three_indicators
                else (args.catalog or REPO_ROOT / "config" / "indicators.json")
            )
            records = build_matrix(municipalities, selected_catalog)
            write_matrix(records, args.output)
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            parser.error(str(exc))
        indicators = len(records) // len(municipalities)
        print(f"Created {len(records)} checks ({len(municipalities)} municipalities x {indicators} indicators).")
        return

    try:
        municipalities, checks, errors = validate_matrix(args.matrix, args.catalog)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)

    print(f"Matrix valid: {municipalities} municipalities, {checks} checks.")


if __name__ == "__main__":
    main()
