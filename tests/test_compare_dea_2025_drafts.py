"""Synthetic tests for old/new DEA candidate comparison; no official data."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/compare_dea_2025_drafts.py"
SPEC = importlib.util.spec_from_file_location("compare_dea_2025_drafts", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def fixture(tmp_path, *, changed=False, stale_sha=False):
    registry = tmp_path / "registry.csv"
    registry.write_text("municipality,istat_code\nA,000001\n" + "".join(
        f"X{i},00{i:04d}\n" for i in range(2, 28)
    ), encoding="utf-8")
    hospitals = tmp_path / "hospitals.csv"
    hospitals.write_text("synthetic 2025 candidate", encoding="utf-8")
    first, second = tmp_path / "v01", tmp_path / "v02"
    for folder, is_new in ((first, False), (second, True)):
        folder.mkdir()
        rows = []
        for i in range(1, 28):
            rows.append({
                "municipality": "A" if i == 1 else f"X{i}",
                "municipality_code": f"{i:06d}",
                "nearest_dea_code": "000099" if is_new and changed and i == 1 else "000098",
                "travel_time_minutes": "10.00" if is_new and changed and i == 1 else "15.00",
                "distance_km": "8.00" if is_new and changed and i == 1 else "12.00",
            })
        csvfile = folder / "dea_accessibility_minutes.csv"
        with csvfile.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        qa = {
            "indicator_id": "dea_accessibility",
            "origin_count": 27, "route_pair_count": 621, "expected_route_pairs": 621,
            "validated_for_release": False,
            "data_csv_sha256": hashlib.sha256(csvfile.read_bytes()).hexdigest(),
        }
        if is_new:
            qa.update(
                hospital_snapshot_reference_years=["2025"],
                hospitals_csv_sha256=hashlib.sha256(hospitals.read_bytes()).hexdigest(),
                hospital_facility_count=30, eligible_dea_municipality_count=23,
            )
            if stale_sha:
                qa["hospitals_csv_sha256"] = "0" * 64
        (folder / "dea_accessibility_qa.json").write_text(json.dumps(qa), encoding="utf-8")
    return first, second, registry, hospitals


def test_unchanged_routes_are_not_artificially_modified(tmp_path):
    report = MODULE.evaluate(*fixture(tmp_path))
    assert report["technical_consistency_pass"] is True
    assert report["rows_compared"] == 27
    assert report["municipalities_with_changed_minutes"] == 0
    assert report["human_review_required"] is True


def test_changed_route_is_reported_precisely(tmp_path):
    report = MODULE.evaluate(*fixture(tmp_path, changed=True))
    assert report["technical_consistency_pass"] is True
    assert report["municipalities_with_changed_destination"] == 1
    assert report["municipalities_with_changed_minutes"] == 1
    row = report["rows"][0]
    assert row["difference_minutes"] == "-5.00"


def test_mismatched_2025_source_is_blocked(tmp_path):
    report = MODULE.evaluate(*fixture(tmp_path, stale_sha=True))
    assert report["technical_consistency_pass"] is False
    assert "reference SHA mismatch" in " ".join(report["technical_blockers"])
