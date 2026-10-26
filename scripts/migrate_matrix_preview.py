"""Non-destructive preview of catalog/matrix alignment; no changes to the production matrix."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

FIELDS = ["municipality", "indicator_id", "indicator_name", "macro_area", "status",
          "source_priority", "year", "territorial_level", "unit", "source_url",
          "value", "quality", "limitations", "notes"]


def preview(matrix_path: Path, municipalities_path: Path, catalog_path: Path,
            output_path: Path) -> tuple[int, int]:
    if output_path.resolve() == matrix_path.resolve():
        raise ValueError("Refusing to overwrite the source verification matrix.")
    if output_path.exists():
        raise ValueError("Output already exists: choose a fresh preview path.")
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    indicators = catalog["indicators"]
    ids = [item["id"] for item in indicators]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate indicator ids in catalog.")
    with municipalities_path.open(encoding="utf-8", newline="") as file:
        municipalities = [x["municipality"].strip() for x in csv.DictReader(file)]
    if not municipalities or any(not name for name in municipalities) or len(set(municipalities)) != len(municipalities):
        raise ValueError("Empty or duplicate municipality in canonical list.")
    with matrix_path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != FIELDS:
            raise ValueError("Unexpected matrix schema; refusing migration.")
        original = list(reader)
    expected_names = set(municipalities)
    valid_ids = set(ids)
    seen = set()
    for row in original:
        key = (row["municipality"], row["indicator_id"])
        if key in seen:
            raise ValueError(f"Duplicate existing observation: {key}")
        seen.add(key)
        if key[0] not in expected_names or key[1] not in valid_ids:
            raise ValueError(f"Unknown existing municipality or indicator: {key}")
    generated = []
    for municipality in municipalities:
        for item in indicators:
            key = (municipality, item["id"])
            if key in seen:
                continue
            generated.append({
                "municipality": municipality,
                "indicator_id": item["id"],
                "indicator_name": item["name"],
                "macro_area": item["dimension"],
                "status": "Da verificare",
                "source_priority": ", ".join(item["source_ids"]),
                "year": "", "territorial_level": "Comune",
                "unit": item["unit"], "source_url": "", "value": "",
                "quality": "", "limitations": item["caveat"], "notes": "",
            })
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(original + generated)
    return len(original), len(generated)


def main() -> None:
    p = argparse.ArgumentParser(description="Generate additive verification matrix preview")
    p.add_argument("--matrix", type=Path, default=Path("data/verification_matrix.csv"))
    p.add_argument("--municipalities", type=Path, default=Path("data/municipalities.csv"))
    p.add_argument("--catalog", type=Path, default=Path("config/indicators.json"))
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    unchanged, added = preview(a.matrix, a.municipalities, a.catalog, a.output)
    print(f"Preserved {unchanged} existing rows; added {added}; preview: {a.output}")


if __name__ == "__main__":
    main()
