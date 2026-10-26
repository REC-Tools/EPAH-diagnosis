"""Offline, read-only completeness report for the canonical municipality/indicator matrix."""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from epah_diagnosis.cli import validate_matrix, read_municipalities


def generate(matrix: Path, municipalities: Path, catalog: Path) -> dict:
    names = read_municipalities(municipalities)
    indicators = json.loads(catalog.read_text(encoding="utf-8"))["indicators"]
    ids = [x["id"] for x in indicators]
    count, checks, errors = validate_matrix(matrix, catalog)
    if errors or count != len(names) or checks != len(names) * len(ids):
        raise ValueError("Matrix structural validation failed: " + "; ".join(errors))
    with matrix.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    indexed = {(r["municipality"], r["indicator_id"]): r for r in rows}
    if set(r["municipality"] for r in rows) != set(names):
        raise ValueError("Matrix municipality set differs from canonical registry")
    status_totals = Counter(r["status"] for r in rows)
    by_indicator = []
    for item in indicators:
        group = [indexed[(n, item["id"])] for n in names]
        by_indicator.append({
            "indicator_id": item["id"], "role": item["role"],
            "status_counts": dict(sorted(Counter(r["status"] for r in group).items())),
            "nonempty_values": sum(bool(r["value"].strip()) for r in group),
        })
    by_municipality = []
    for name in names:
        group = [indexed[(name, iid)] for iid in ids]
        by_municipality.append({
            "municipality": name,
            "validated": sum(r["status"] == "Dato validato" for r in group),
            "acquired": sum(r["status"] == "Dato acquisito" for r in group),
            "missing_or_unvalidated": sum(r["status"] != "Dato validato" for r in group),
            "nonempty_values": sum(bool(r["value"].strip()) for r in group),
        })
    return {"municipalities": len(names), "indicators": len(ids), "checks": len(rows),
            "status_counts": dict(sorted(status_totals.items())),
            "by_indicator": by_indicator, "by_municipality": by_municipality}


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only completeness inventory")
    parser.add_argument("--matrix", type=Path, default=Path("data/verification_matrix.csv"))
    parser.add_argument("--municipalities", type=Path, default=Path("data/municipalities.csv"))
    parser.add_argument("--catalog", type=Path, default=Path("config/indicators.json"))
    parser.add_argument("--output", type=Path, default=Path("outputs/quality/completeness.json"))
    args = parser.parse_args()
    inputs = {args.matrix.resolve(), args.municipalities.resolve(), args.catalog.resolve()}
    if args.output.resolve() in inputs:
        parser.error("Output must not overwrite an input")
    result = generate(args.matrix, args.municipalities, args.catalog)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Completeness report: {result['checks']} checks; {result['status_counts']}")
    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()
