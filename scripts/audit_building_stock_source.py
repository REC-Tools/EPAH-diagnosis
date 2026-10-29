"""Download, draft and independently audit the original ISTAT CPA 2011 dataset.

Unlike the reviewed finalizer, this command never writes to data/indicators,
verification_matrix.csv, config/indicators.json or human review records.

Run from project root:
  python scripts/audit_building_stock_source.py --download
  python scripts/audit_building_stock_source.py --source-zip C:\Dati\dati-cpa_2011.zip
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from epah_diagnosis.building_stock_source_audit import (
    download_official_cpa, verify_draft_independently,
)

from prepare_building_stock import prepare_files

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data/municipalities.csv"
OUTPUT = ROOT / "outputs/quality/istat_building_stock_2011"
ARCHIVE = ROOT / "outputs/quality/istat_building_stock_2011_original/dati-cpa_2011.zip"


def _read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def run(
    source_zip: Path, registry: Path, destination: Path,
    *, min_italy: int = 7000, min_piemonte: int = 900,
) -> dict:
    """Stage QA + independent original row-check before atomic publication.

    The optional thresholds are intended only for synthetic unit tests.
    Production CLI deliberately does not expose a bypass for completeness.
    """
    source_zip = source_zip.resolve()
    registry = registry.resolve()
    destination = destination.resolve()
    if destination.exists():
        raise FileExistsError(
            f"QA already exists: {destination}. Use a fresh --out-dir, never overwrite."
        )
    if not source_zip.is_file() or not registry.is_file():
        raise FileNotFoundError("Original source ZIP and 27-municipality registry are required")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".cpa-qa-stage-", dir=destination.parent) as td:
        staging = Path(td) / "draft"
        qa = prepare_files(
            source_zip, registry, staging,
            min_italy=min_italy, min_piemonte=min_piemonte,
        )
        raw = source_zip.read_bytes()
        independent = verify_draft_independently(
            raw, registry,
            _read_csv(staging / "building_stock_2011.csv"),
            _read_csv(staging / "building_stock_benchmarks_2011.csv"),
        )
        if not independent["technical_pass"]:
            raise ValueError(
                f"Independent raw count comparison failed: {len(independent['differences'])} "
                f"difference(s): {independent['differences'][:4]}"
            )
        if independent["raw_archive_sha256"] != qa["archive_sha256"]:
            raise ValueError("CPA original source changed between technical and independent checks")
        # Keep the 27 raw per-code numerators and denominators for human QA.
        (staging / "independent_raw_r01_audit.json").write_text(
            json.dumps(independent, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        manifest = {
            "schema_version": "1.0",
            "audit_run_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
            "indicator_id": "old_building_stock",
            "reference_year": "2011",
            "original_file_name": source_zip.name,
            "original_file_sha256": hashlib.sha256(raw).hexdigest(),
            "municipality_registry_sha256": hashlib.sha256(registry.read_bytes()).hexdigest(),
            "technical_qa": {
                "italy_municipalities": qa["national_count"],
                "piemonte_municipalities": qa["piemonte_count"],
                "target_municipalities": qa["coverage"],
                "old_building_count_weighted": True,
            },
            "independent_qa": {
                "target_municipalities": independent["municipalities_compared"],
                "unmatched_values": len(independent["differences"]),
                "passed": independent["technical_pass"],
                "green_community_buildings_pre_1981_pct": independent["weighted_share_pct"],
            },
            "files": {
                name: {
                    "sha256": hashlib.sha256((staging / name).read_bytes()).hexdigest(),
                    "bytes": (staging / name).stat().st_size,
                }
                for name in (
                    "building_stock_2011.csv",
                    "building_stock_benchmarks_2011.csv",
                    "building_stock_qa.json",
                    "independent_raw_r01_audit.json",
                )
            },
            "technical_pass": True,
            "source_authenticity_reviewed": False,
            "2011_2026_geography_reviewed": False,
            "license_reviewed": False,
            "reviewed_by": None,
            "validated_for_release": False,
            "matrix_modified": False,
            "automatic_promotions": 0,
        }
        (staging / "source_audit_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if destination.exists():
            raise FileExistsError("QA destination appeared during preparation")
        os.replace(staging, destination)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify real ISTAT CPA 2011 ZIP independently before human approval"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--download", action="store_true",
                       help="Download original ZIP from fixed official ISTAT HTTPS endpoint")
    group.add_argument("--source-zip", type=Path,
                       help="Local original ISTAT CPA 2011 ZIP")
    parser.add_argument("--raw-destination", type=Path, default=ARCHIVE,
                        help="Only used with --download; never overwrites")
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--out-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    original = args.source_zip
    if args.download:
        metadata = download_official_cpa(args.raw_destination)
        print("Official ISTAT ZIP downloaded without overwrite:")
        print(f"  file: {args.raw_destination}")
        print(f"  bytes: {metadata['bytes']}")
        print(f"  sha256: {metadata['sha256']}")
        original = args.raw_destination
    result = run(original, args.registry, args.out_dir)
    print("CPA 2011 technical + independent raw R01 verification: PASS")
    print(
        f"  Italy municipalities: {result['technical_qa']['italy_municipalities']}; "
        f"Piemonte: {result['technical_qa']['piemonte_municipalities']}; "
        f"27/27 Green Community"
    )
    print(
        f"  independent differences: {result['independent_qa']['unmatched_values']}; "
        f"GC weighted pre-1981 share: "
        f"{result['independent_qa']['green_community_buildings_pre_1981_pct']:.2f}%"
    )
    print(f"  QA report: {args.out_dir / 'source_audit_manifest.json'}")
    print("Verification matrix unchanged. Human source review and approval still required.")


if __name__ == "__main__":
    main()
