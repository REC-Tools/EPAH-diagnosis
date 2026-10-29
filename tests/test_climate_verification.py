"""PR-03: historical regulatory climate comparison and fail-closed promotion."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

from epah_diagnosis.climate_verification import (
    CURRENT_ANNEX_URL, CURRENT_VERSION, approve_with_evidence, compare_reference,
)


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data/reference/climate_dpr412_green_community.csv"
HISTORICAL = ROOT / "data/reference/climate_dpr412_official_2008_transcription.csv"


def test_historical_official_27_gg_and_zone_values_match():
    result = compare_reference(SNAPSHOT, HISTORICAL)
    assert result["municipalities"] == 27
    assert result["value_mismatches"] == []
    assert result["zone_mismatches"] == []
    assert result["gg_zone_comparison_passed"] is True
    assert result["current_edition_independently_checked"] is False
    assert result["validated_for_release"] is False
    assert result["altitude_mismatches"] == [
        {"municipality": "Pratiglione", "snapshot_m": 611, "legal_table_m": 711}
    ]


def _copy_modify(source: Path, target: Path, *, name: str, field: str, value: str):
    with source.open(encoding="utf-8", newline="") as inp:
        reader = csv.DictReader(inp)
        fields, rows = reader.fieldnames, list(reader)
    for row in rows:
        if row["municipality"] == name:
            row[field] = value
    with target.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_comparison_detects_edited_degree_days(tmp_path):
    edited = tmp_path / "modified.csv"
    _copy_modify(SNAPSHOT, edited, name="Alpette", field="heating_degree_days", value="3800")
    report = compare_reference(edited, HISTORICAL)
    assert report["gg_zone_comparison_passed"] is False
    assert report["value_mismatches"][0]["municipality"] == "Alpette"


def test_comparison_detects_invalid_climate_zone(tmp_path):
    edited = tmp_path / "modified.csv"
    _copy_modify(SNAPSHOT, edited, name="Alpette", field="climate_zone", value="E")
    with pytest.raises(ValueError, match="Zone E municipality"):
        compare_reference(edited, HISTORICAL)


def test_comparison_detects_missing_municipality(tmp_path):
    with SNAPSHOT.open(encoding="utf-8", newline="") as inp:
        lines = inp.readlines()
    edited = tmp_path / "modified.csv"
    edited.write_text("".join(lines[:-1]), encoding="utf-8")
    with pytest.raises(ValueError, match="Expected 27"):
        compare_reference(edited, HISTORICAL)


def _evidence(report: dict) -> dict:
    return {
        "indicator_id": "heating_degree_days",
        "decision": "approved",
        "official_version_reviewed": CURRENT_VERSION,
        "official_url": CURRENT_ANNEX_URL,
        "snapshot_sha256": report["snapshot_sha256"],
        "historical_transcription_sha256": report["historical_transcription_sha256"],
        "reviewed_by": "Synthetic reviewer (test fixture)",
        "reviewed_on": "2026-10-28",
        "review_evidence_url": "https://example.org/qa/synthetic-fixture",
        "license_review_decision": "approved_for_use",
        "altitude_discrepancies_acknowledged": ["Pratiglione"],
        "review_notes": "Synthetic metadata for testing structure, not actual approval",
    }


def test_approval_schema_requires_review_of_current_version(tmp_path):
    report = compare_reference(SNAPSHOT, HISTORICAL)
    path = tmp_path / "fixture-review.json"
    evidence = _evidence(report)
    path.write_text(json.dumps(evidence), encoding="utf-8")
    accepted = approve_with_evidence(report, path)
    assert accepted["validated_for_release"]
    for field, value in [
        ("official_version_reviewed", "2008"),
        ("snapshot_sha256", "0" * 64),
        ("review_evidence_url", "not a URL"),
        ("reviewed_by", ""),
        ("license_review_decision", "pending"),
        ("altitude_discrepancies_acknowledged", []),
        ("review_notes", ""),
    ]:
        invalid = {**evidence, field: value}
        path.write_text(json.dumps(invalid), encoding="utf-8")
        with pytest.raises(ValueError):
            approve_with_evidence(report, path)


def test_finalizer_without_human_evidence_is_non_destructive():
    matrix = ROOT / "data/verification_matrix.csv"
    original = matrix.read_bytes()
    process = subprocess.run(
        [sys.executable, "scripts/finalize_heating_degree_days.py"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert process.returncode != 0
    assert "--approved-evidence" in process.stderr
    assert matrix.read_bytes() == original


def test_offline_comparison_command_writes_report_without_changing_matrix(tmp_path):
    matrix = ROOT / "data/verification_matrix.csv"
    original = matrix.read_bytes()
    output = tmp_path / "comparison.json"
    result = subprocess.run(
        [sys.executable, "scripts/verify_heating_degree_days.py", "--output", str(output)],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["gg_zone_comparison_passed"]
    assert not report["validated_for_release"]
    assert matrix.read_bytes() == original
