"""Promote a prepared CPA 2011 draft only after documented independent review.

No download, no synthetic approval, no change to other indicators.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from epah_diagnosis.building_stock_qa import prepare
from epah_diagnosis.matrix_update import upsert_indicator_rows

ROOT = Path(__file__).resolve().parents[1]
INDICATOR_ID = "old_building_stock"
SOURCE_PAGE = "https://www.istat.it/notizia/basi-territoriali-e-variabili-censuarie/"


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _https(value: object) -> bool:
    return isinstance(value, str) and urlsplit(value).scheme == "https" and bool(urlsplit(value).netloc)


def validate_approval(approval: dict, qa: dict, stock: Path, benchmarks: Path,
                      registry: Path, source_zip: Path) -> None:
    exact = {
        "indicator_id": INDICATOR_ID,
        "reference_year": "2011",
        "decision": "approved",
        "archive_sha256": qa["archive_sha256"],
        "registry_sha256": qa["registry_sha256"],
        "building_csv_sha256": qa["building_csv_sha256"],
        "benchmark_csv_sha256": qa["benchmark_csv_sha256"],
    }
    if any(approval.get(key) != value for key, value in exact.items()):
        raise ValueError("Approval metadata does not match the prepared source and outputs")
    if checksum(source_zip) != qa["archive_sha256"]:
        raise ValueError("Original archive hash changed")
    if checksum(registry) != qa["registry_sha256"]:
        raise ValueError("Municipality registry hash changed")
    if checksum(stock) != qa["building_csv_sha256"] or checksum(benchmarks) != qa["benchmark_csv_sha256"]:
        raise ValueError("Prepared data hashes differ from approved content")
    if not isinstance(approval.get("reviewed_by"), str) or not approval["reviewed_by"].strip():
        raise ValueError("Actual reviewer name is mandatory")
    try:
        reviewed_on = date.fromisoformat(approval["reviewed_on"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("An ISO-8601 review date is mandatory") from exc
    if reviewed_on > date.today():
        raise ValueError("Review date cannot be in the future")
    if not _https(approval.get("review_evidence_url")):
        raise ValueError("Durable HTTPS review evidence is mandatory")
    for field in ("source_authenticity_reviewed", "historical_geography_reviewed",
                  "license_reviewed", "independent_sample_reviewed"):
        if approval.get(field) is not True:
            raise ValueError(f"Independent review evidence not confirmed: {field}")
    if not isinstance(approval.get("review_notes"), str) or not approval["review_notes"].strip():
        raise ValueError("Document method, limitations and sample check in review_notes")


def promote(source_zip: Path, registry: Path, draft_dir: Path, approval_file: Path,
            matrix: Path, indicator_dir: Path) -> int:
    qa_file = draft_dir / "building_stock_qa.json"
    stock = draft_dir / "building_stock_2011.csv"
    benchmarks = draft_dir / "building_stock_benchmarks_2011.csv"
    qa = json.loads(qa_file.read_text(encoding="utf-8"))
    approval = json.loads(approval_file.read_text(encoding="utf-8"))
    validate_approval(approval, qa, stock, benchmarks, registry, source_zip)

    # Recompute from the actual archive, not only a manually edited draft CSV.
    expected_rows, expected_benchmarks, expected_qa = prepare(source_zip.read_bytes(), registry)
    if expected_qa["archive_sha256"] != qa["archive_sha256"] or expected_qa["coverage"] != 27:
        raise ValueError("Source file or municipality coverage changed")
    with stock.open(encoding="utf-8", newline="") as stream:
        draft_rows = list(csv.DictReader(stream))
    with benchmarks.open(encoding="utf-8", newline="") as stream:
        draft_benchmarks = list(csv.DictReader(stream))
    if draft_rows != expected_rows or draft_benchmarks != expected_benchmarks:
        raise ValueError("Draft does not match regenerated census counts")
    if len(draft_rows) != 27:
        raise ValueError("Expected exactly 27 rows")

    with matrix.open(encoding="utf-8", newline="") as stream:
        existing = list(csv.DictReader(stream))
    matches = [row for row in existing if row["indicator_id"] == INDICATOR_ID]
    if len(matches) != 27 or len({row["municipality"] for row in matches}) != 27:
        raise ValueError("Verification matrix must have exactly 27 unique building rows")
    by_name = {row["municipality"]: row for row in draft_rows}
    if {row["municipality"] for row in matches} != set(by_name):
        raise ValueError("Prepared and matrix municipality names differ")
    changes = []
    for row in matches:
        observation = by_name[row["municipality"]]
        next_row = dict(row)
        next_row.update({
            "status": "Dato validato",
            "year": "2011",
            "territorial_level": "Comune",
            "unit": "%",
            "source_url": SOURCE_PAGE,
            "value": observation["share_pre_1981_pct"],
            "quality": "ISTAT CPA 2011; count-based aggregation; independent review documented",
            "limitations": "Historical building-age proxy, not current energy performance or renovation",
            "notes": (
                f"ISTAT code {observation['municipality_code']}; "
                f"E8-E12={observation['buildings_pre_1981']}; "
                f"E3={observation['residential_buildings_total']}; "
                f"QA review: {approval['review_evidence_url']}"
            ),
        })
        changes.append(next_row)

    indicator_dir.mkdir(parents=True, exist_ok=True)
    published = [
        indicator_dir / "building_stock_2011.csv",
        indicator_dir / "building_stock_benchmarks_2011.csv",
    ]
    if any(path.exists() for path in published):
        raise FileExistsError("Published indicator output exists; refusing overwrite")
    created = []
    try:
        for src, dst in zip((stock, benchmarks), published):
            with dst.open("xb") as handle:
                handle.write(src.read_bytes())
            created.append(dst)
        upsert_indicator_rows(matrix, INDICATOR_ID, changes)
    except Exception:
        for dst in created:
            dst.unlink(missing_ok=True)
        raise
    return len(changes)


def main() -> None:
    parser = argparse.ArgumentParser(description="Review-gated CPA 2011 building-stock promotion")
    parser.add_argument("--source-zip", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--draft-dir", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=ROOT / "data/municipalities.csv")
    parser.add_argument("--matrix", type=Path, default=ROOT / "data/verification_matrix.csv")
    parser.add_argument("--indicator-dir", type=Path, default=ROOT / "data/indicators")
    args = parser.parse_args()
    updated = promote(args.source_zip, args.registry, args.draft_dir, args.approval,
                      args.matrix, args.indicator_dir)
    print(f"Promoted {updated} reviewed CPA 2011 observations; other indicators preserved")


if __name__ == "__main__":
    main()
