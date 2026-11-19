"""Inventory a local ISTAT section workbook; no indicator values or approval."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from zipfile import BadZipFile
from xml.etree.ElementTree import ParseError

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from .cli import read_municipality_codes


def _digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _identifier(value, width=None):
    if type(value) is int:
        text = str(value)
    elif isinstance(value, str):
        text = value.strip()
    else:
        raise ValueError("Municipal and section identifiers must be integer or digit text")
    if not re.fullmatch(r"[0-9]+", text) or (width and len(text) > width):
        raise ValueError("Invalid municipal or section identifier")
    return text.zfill(width) if width else text


def audit_source(data: Path, layout: Path, registry: Path, reference_year: int) -> dict:
    """Read field definitions and identity-row coverage, never housing measurements.

    reference_year is a caller declaration, not inferred or validated from a filename.
    Presence of section rows says nothing about indicator completeness.
    """
    if type(reference_year) is not int or not 1000 <= reference_year <= 9999:
        raise ValueError("Declare a four-digit reference year")
    inputs = {"data": data, "layout": layout, "registry": registry}
    before = {name: _digest(path) for name, path in inputs.items()}
    mapping = read_municipality_codes(registry)
    book = load_workbook(layout, read_only=True, data_only=False)
    try:
        if len(book.worksheets) != 1:
            raise ValueError("Expected a single layout worksheet; select a reviewed source")
        book.active.reset_dimensions()
        rows = book.active.iter_rows(values_only=True)
        if next(rows, None) != ("NOME_CAMPO", "DEFINIZIONE"):
            raise ValueError("Unexpected ISTAT layout headers")
        definitions = {}
        for row in rows:
            if all(value is None for value in row):
                continue
            if (len(row) != 2 or any(not isinstance(value, str) or not value.strip() for value in row)
                    or row[0] in definitions or any(value.startswith("=") for value in row)):
                raise ValueError("Missing, duplicate or formula-based field definition")
            definitions[row[0]] = row[1]
    finally:
        book.close()
    counts = Counter()
    seen = set()
    total = 0
    book = load_workbook(data, read_only=True, data_only=False)
    try:
        if len(book.worksheets) != 1:
            raise ValueError("Expected a single section worksheet")
        sheet = book.active
        # Ignore cached worksheet dimensions: inspect the actual XML rows.
        sheet.reset_dimensions()
        header = next(sheet.iter_rows(values_only=True), ())
        if (not header or any(not isinstance(field, str) or not field for field in header)
                or len(set(header)) != len(header) or set(header) != set(definitions)
                or not {"PROCOM", "SEZ21_ID"} <= set(header)):
            raise ValueError("Section columns must match the layout exactly, including identity fields")
        code_col, section_col = header.index("PROCOM"), header.index("SEZ21_ID")
        for row in sheet.iter_rows(min_row=2, max_col=max(code_col, section_col) + 1, values_only=True):
            if all(value is None for value in row):
                raise ValueError("Blank identity row; review the workbook rather than dropping it")
            code = _identifier(row[code_col], 6)
            section = _identifier(row[section_col])
            if (code, section) in seen:
                raise ValueError("Repeated municipal/section identity; do not deduplicate implicitly")
            seen.add((code, section))
            counts[code] += 1
            total += 1
    finally:
        book.close()
    if total == 0:
        raise ValueError("Section source has no identity rows")
    if any(_digest(path) != before[name] for name, path in inputs.items()):
        raise ValueError("An input changed during review")
    return {
        "schema_version": "0.5-istat-section-source-review-1",
        "status": "technical_draft_do_not_publish", "result": "source_inventory_requires_review",
        "declared_reference_year": reference_year, "reference_year_verified": False,
        "input_sha256": before, "field_count": len(header),
        "fields": [{"name": field, "definition": definitions[field]} for field in header],
        "source_identity_rows": total, "matched_identity_rows": sum(counts[code] for code in mapping.values()),
        "municipalities": [{"municipality": name, "istat_code": code,
                            "source_section_rows": counts[code],
                            "row_presence": "present" if counts[code] else "not_observed"}
                           for name, code in mapping.items()],
        "indicator_values_checked": False, "territorial_compatibility_verified": False,
        "indicators_calculated": False, "municipal_series_added": 0,
        "scientific_approval": False, "publication_allowed": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--layout", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--reference-year", type=int, required=True)
    parser.add_argument("--json-out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.json_out.exists() or args.json_out.is_symlink():
            raise FileExistsError("Choose a new report; preserve earlier evidence")
        result = audit_source(args.data, args.layout, args.registry, args.reference_year)
        payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        with args.json_out.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
    except (ValueError, OSError, TypeError, BadZipFile, KeyError, ParseError, InvalidFileException) as exc:
        parser.exit(2, f"BLOCKED: {exc}\n")
    print("ISTAT field inventory completed; indicator availability and scientific review remain open.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
