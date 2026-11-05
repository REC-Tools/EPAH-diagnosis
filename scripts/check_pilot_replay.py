"""Compare deterministic core outputs from two separate EPAH release builds.

A matching comparison is a *technical replay check*, not scientific validation.
PDF/PNG/XLSX and manifests can carry non-deterministic metadata and are excluded.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

CORE_FILES = (
    "municipality_profile.csv",
    "municipality_comparison.csv",
    "municipality_profile.geojson",
)


def _csv_rows(path: Path) -> dict:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or "municipality" not in reader.fieldnames:
            raise ValueError("CSV missing municipality key/header")
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("CSV has duplicate columns")
        rows = {}
        for row in reader:
            name = row.get("municipality")
            if not name or name in rows or None in row:
                raise ValueError("CSV has missing/duplicate municipality or extra columns")
            rows[name] = row
        if not rows:
            raise ValueError("CSV has no records")
        return rows


def _geo_features(path: Path) -> dict:
    content = json.loads(path.read_text(encoding="utf-8"))
    if content.get("type") != "FeatureCollection":
        raise ValueError("Expected GeoJSON FeatureCollection")
    rows = {}
    for feature in content.get("features", []):
        if feature.get("type") != "Feature":
            raise ValueError("Invalid feature")
        code = (feature.get("properties") or {}).get("municipality_code")
        if not isinstance(code, str) or not code or code in rows:
            raise ValueError("Missing/duplicate GeoJSON municipality_code")
        rows[code] = feature
    if not rows:
        raise ValueError("GeoJSON has no features")
    return rows


def compare(first: Path, second: Path) -> dict:
    checks = {}
    for relative in CORE_FILES:
        left = first / relative
        right = second / relative
        if not left.is_file() or not right.is_file():
            checks[relative] = "missing"
            continue
        try:
            read = _geo_features if relative.endswith(".geojson") else _csv_rows
            checks[relative] = "match" if read(left) == read(right) else "different"
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, csv.Error):
            checks[relative] = "invalid"
    return {
        "schema_version": "1.0",
        "check": "technical_replay_only",
        "scientific_validation": "not_assessed",
        "status": "match" if all(v == "match" for v in checks.values()) else "blocked",
        "files": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare two completed EPAH build core datasets")
    parser.add_argument("first", type=Path)
    parser.add_argument("second", type=Path)
    args = parser.parse_args()
    result = compare(args.first, args.second)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "match" else 1


if __name__ == "__main__":
    raise SystemExit(main())
