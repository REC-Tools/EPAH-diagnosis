"""Read-only CIT CSV preflight: reveal schema, source categories and 27-town coverage.

Does not assert a downloaded file is authentic or aligned to a known vintage.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from prepare_piemonte_cit import ALIASES, norm, read_registry, sha256
from prepare_piemonte_cit_wide import FUEL_HEADERS, AGE_HEADERS, municipality_code


def _encoding(path: Path) -> str:
    with path.open("rb") as f:
        sample = f.read(131072)
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            sample.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    raise ValueError("CSV must be UTF-8 or Windows-1252 without malformed bytes")


def inspect(path: Path, registry: Path, mode: str) -> dict:
    if mode not in {"fuel", "age"}:
        raise ValueError("mode must be fuel or age")
    wanted = read_registry(registry)
    encoding = _encoding(path)
    with path.open(encoding=encoding, errors="strict", newline="") as handle:
        sample = handle.read(8192)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
        except csv.Error as exc:
            raise ValueError("Cannot determine CSV delimiter") from exc
        reader = csv.DictReader(handle, dialect=dialect)
        headers = list(reader.fieldnames or [])
        if not headers or len(headers) != len(set(headers)):
            raise ValueError("Missing or duplicate source CSV headers")
        if tuple(headers) == (FUEL_HEADERS if mode == "fuel" else AGE_HEADERS):
            registry_data = read_registry(registry)
            name_index = {norm(name): code for code, name in registry_data.items()}
            code_field = "key_classe" if mode == "fuel" else "istat_comune"
            found = set()
            samples = []
            unknown_samples = []
            source_rows = 0
            for row in reader:
                source_rows += 1
                key = str(row.get(code_field) or "").strip()
                if len(samples) < 8:
                    samples.append(key)
                code = municipality_code(key, name_index)
                if code in registry_data:
                    found.add(code)
                elif code is None and len(unknown_samples) < 8:
                    unknown_samples.append(key)
            return {
                "status": "schema_inspection_only",
                "mode": mode,
                "file": path.name,
                "source_sha256": sha256(path),
                "encoding": encoding,
                "delimiter": dialect.delimiter,
                "headers": headers,
                "layout": "wide",
                "source_rows": source_rows,
                "key_field": code_field,
                "key_examples": samples,
                "unresolved_key_examples": unknown_samples,
                "selected_27_matched": len(found),
                "selected_27_missing": [
                    {"istat_code": code, "municipality": name}
                    for code,name in registry_data.items() if code not in found
                ],
                "requires_schema_mapping": len(found) != 27,
                "meaning": "Real wide CIT source. No numeric energy-poverty data are approved."
            }
        lookup = {norm(header): header for header in headers}
        suggestions = {}
        for role, key in (("code", "code"), ("category", "category_" + mode),
                          ("count", "count")):
            matches = sorted({lookup[norm(alias)] for alias in ALIASES[key]
                              if norm(alias) in lookup})
            suggestions[role] = matches[0] if len(matches) == 1 else None
        categories = Counter()
        matched = set()
        records = 0
        for record in reader:
            records += 1
            if None in record:
                raise ValueError("Malformed CSV row with extra columns")
            if suggestions["category"] is not None:
                label = str(record[suggestions["category"]] or "").strip()
                categories[label or "[missing]"] += 1
            if suggestions["code"] is not None:
                code = str(record[suggestions["code"]] or "").strip()
                if code.isdigit() and len(code) <= 6 and code.zfill(6) in wanted:
                    matched.add(code.zfill(6))
    return {
        "status": "schema_inspection_only",
        "mode": mode, "file": path.name, "source_sha256": sha256(path),
        "encoding": encoding, "delimiter": dialect.delimiter,
        "headers": headers, "source_rows": records,
        "suggested_columns": suggestions,
        "selected_27_matched": len(matched) if suggestions["code"] else None,
        "selected_27_missing": [
            {"istat_code": code, "municipality": name}
            for code, name in sorted(wanted.items()) if code not in matched
        ] if suggestions["code"] else None,
        "category_labels_top_30": categories.most_common(30),
        "requires_schema_mapping": any(v is None for v in suggestions.values()),
        "meaning": "Header/coverage inspection ONLY. No energy-poverty indicator approved.",
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Inspect two Piemonte CIT CSV sources before preparing 27-town indicators")
    p.add_argument("--mode", required=True, choices=("fuel", "age"))
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--registry", type=Path, default=Path(__file__).resolve().parents[1] / "data/municipalities.csv")
    p.add_argument("--out", type=Path, help="Optional JSON report output; will refuse overwrite")
    args = p.parse_args()
    result = inspect(args.input, args.registry, args.mode)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.out is not None:
        if args.out.exists():
            raise FileExistsError(f"Output already exists: {args.out}")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
