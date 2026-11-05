"""Read-only, offline preflight for the v0.1 owner-accepted pilot.

This checks presence/readability and records content digests; it does not
validate the scientific meaning of the inputs or authorize publication.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUTS = {
    "matrix": "data/verification_matrix.csv",
    "catalog": "config/indicators.json",
    "registry": "data/municipalities.csv",
    "release_config": "config/release_v0_1.json",
    "dea_csv": "outputs/quality/dea_accessibility_2025_v03/dea_accessibility_minutes.csv",
    "dea_qa": "outputs/quality/dea_accessibility_2025_v03/dea_accessibility_qa.json",
    "rail_csv": "outputs/quality/rail_accessibility_v01/rail_accessibility_minutes.csv",
    "rail_qa": "outputs/quality/rail_accessibility_v01/rail_accessibility_qa.json",
    "school_csv": "outputs/quality/upper_secondary_accessibility_v01/upper_secondary_accessibility_minutes.csv",
    "school_qa": "outputs/quality/upper_secondary_accessibility_v01/upper_secondary_accessibility_qa.json",
    "route_samples": "outputs/quality/v0_1_pilot_route_samples_v01/samples.json",
    "boundaries_zip": "data/downloads/Limiti01012026_g.zip",
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def inspect(root: Path) -> dict:
    entries = {}
    for name, relative in INPUTS.items():
        path = root / relative
        entry = {"path": relative}
        if not path.is_file():
            entry["status"] = "missing"
        else:
            try:
                entry["bytes"] = path.stat().st_size
                entry["sha256"] = digest(path)
                entry["status"] = "present"
            except OSError as exc:
                entry["status"] = "unreadable"
                entry["error"] = type(exc).__name__
        entries[name] = entry
    ready = all(e["status"] == "present" for e in entries.values())
    return {
        "schema_version": "1.0",
        "release_track": "owner_accepted_technical_pilot",
        "preflight_status": "inputs_present" if ready else "blocked",
        "scientific_validation": "not_assessed",
        "publication_approval": "not_assessed",
        "inputs": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline read-only v0.1 pilot input inventory")
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root")
    parser.add_argument("--json-out", type=Path, help="Optional report path; never overwrite")
    args = parser.parse_args()
    result = inspect(args.root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.json_out is not None:
        if args.json_out.exists():
            parser.error("Report already exists: refusing overwrite")
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        with args.json_out.open("x", encoding="utf-8") as out:
            json.dump(result, out, indent=2, ensure_ascii=False)
            out.write("\n")
    return 0 if result["preflight_status"] == "inputs_present" else 1


if __name__ == "__main__":
    raise SystemExit(main())
