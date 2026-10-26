from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .model import INDICATORS, VerificationStatus


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
    return municipalities


def build_matrix(municipalities: list[str]) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for municipality in municipalities:
        for indicator in INDICATORS:
            records.append(
                {
                    "municipality": municipality,
                    "indicator_id": indicator.id,
                    "indicator_name": indicator.name,
                    "macro_area": indicator.macro_area,
                    "status": VerificationStatus.TO_VERIFY.value,
                    "source_priority": indicator.preferred_source,
                    "year": "",
                    "territorial_level": "Comune",
                    "unit": indicator.unit,
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

    validate_parser = subparsers.add_parser("validate-matrix", help="Validate an existing matrix")
    validate_parser.add_argument("matrix", type=Path)
    validate_parser.add_argument("--catalog", type=Path, help="Validate against the complete methodology catalog")

    args = parser.parse_args()

    if args.command == "init-matrix":
        municipalities = read_municipalities(args.municipalities)
        records = build_matrix(municipalities)
        write_matrix(records, args.output)
        print(
            f"Created {len(records)} checks "
            f"({len(municipalities)} municipalities × {len(INDICATORS)} indicators)."
        )
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
