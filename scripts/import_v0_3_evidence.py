"""Deterministic import of the reviewed EPAH v0.3 workbook (no data promotion)."""
from __future__ import annotations

import argparse
import csv
import hashlib
from datetime import date, datetime
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
SHEETS = {
    "Matrice_EPAH": ("epah_v0_3_mapping.csv", 56),
    "Fonti": ("epah_v0_3_sources.csv", 35),
    "Priorita_v03": ("epah_v0_3_priorities.csv", 12),
}
EXTRA_FIELDS = ("stato_evidenza", "workbook_sha256", "foglio_origine", "riga_origine")


def as_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def import_workbook(workbook_path: Path, destination: Path) -> None:
    digest = hashlib.sha256(workbook_path.read_bytes()).hexdigest()
    workbook = load_workbook(workbook_path, read_only=True, data_only=True)
    try:
        if not set(SHEETS).issubset(workbook.sheetnames):
            raise ValueError(f"Missing sheets: {set(SHEETS) - set(workbook.sheetnames)}")
        staged: dict[str, tuple[list[str], list[list[str]]]] = {}
        for sheet_name, (filename, expected) in SHEETS.items():
            sheet = workbook[sheet_name]
            sheet.reset_dimensions()
            indexed_rows = list(enumerate(sheet.iter_rows(values_only=True), 1))
            header_index = 6 if sheet_name == "Priorita_v03" else 1
            headers = [as_text(cell) for cell in indexed_rows[header_index - 1][1]]
            while headers and not headers[-1]:
                headers.pop()
            if not headers or any(not cell for cell in headers) or len(headers) != len(set(headers)):
                raise ValueError(f"Invalid column labels in {sheet_name}")
            records = []
            for row_num, raw in indexed_rows[header_index:]:
                row = [as_text(value) for value in raw[: len(headers)]]
                if not any(row):
                    continue
                if not row[0].strip():
                    raise ValueError(f"Missing first field in {sheet_name}:{row_num}")
                row += ["source_identified", digest, sheet_name, str(row_num)]
                records.append(row)
            if len(records) != expected:
                raise ValueError(f"{sheet_name}: expected {expected}, found {len(records)}")
            staged[filename] = (headers + list(EXTRA_FIELDS), records)
        destination.mkdir(parents=True, exist_ok=True)
        for filename, (headers, records) in staged.items():
            with (destination / filename).open("w", encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream, lineterminator="\n")
                writer.writerow(headers)
                writer.writerows(records)
    finally:
        workbook.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", type=Path, required=True, help="Original EPAH_fonti_online_v03(1).xlsx")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "data/reference")
    args = parser.parse_args()
    import_workbook(args.workbook, args.out_dir)
    print(f"Imported 56 indicators, 35 sources, 12 priorities into {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
