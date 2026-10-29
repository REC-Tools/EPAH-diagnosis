"""Priority official-source audit: never infer publication approval from a URL.

The HTML in these tests is a SYNTHETIC construction from existing repository
fixtures and must never be treated as a captured or authenticated legal source.
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

from epah_diagnosis.climate import load_reference
from epah_diagnosis.priority_source_audit import (
    OFFICIAL_SOURCES, compare_current_annex, source_snapshot,
)

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data/municipalities.csv"
SNAPSHOT = ROOT / "data/reference/climate_dpr412_green_community.csv"


def fake_official_html(*, changed_gg=False, changed_altitude=False, remove_last=False):
    records = load_reference(SNAPSHOT)
    if remove_last:
        records = records[:-1]
    lines = []
    for rec in records:
        gg = rec.heating_degree_days + (1 if changed_gg and rec.municipality == "Alpette" else 0)
        altitude = rec.municipal_seat_altitude_m + (
            100 if changed_altitude and rec.municipality == "Pratiglione" else 0
        )
        lines.append(
            f"<tr><td>TO</td><td>{rec.climate_zone}</td>"
            f"<td>{gg}</td><td>{altitude}</td>"
            f"<td>{rec.municipality.upper()}</td></tr>"
        )
    return (
        "<html><body><h1>Allegato A</h1>"
        "<p>In vigore dal 09/08/2016</p><table>"
        + "".join(lines) +
        "</table></body></html>"
    ).encode("utf-8")


def test_all_27_source_rows_compare_without_claiming_human_validation():
    result = compare_current_annex(fake_official_html(), SNAPSHOT, REGISTRY)
    assert result["rows_examined"] == 27
    assert not result["missing_municipalities"]
    assert not result["differences"]
    assert result["technical_crosscheck_passed"] is True
    assert result["human_source_reviewed"] is False
    assert result["validated_for_release"] is False
    assert next(x for x in result["official_readings"]
                if x["municipality"] == "Pratiglione")["municipal_seat_altitude_m"] == 611


def test_official_current_annex_numeric_discrepancies_fail_closed():
    result = compare_current_annex(fake_official_html(changed_gg=True), SNAPSHOT, REGISTRY)
    assert result["technical_crosscheck_passed"] is False
    assert result["differences"] == [{
        "municipality": "Alpette",
        "fields": {"heating_degree_days": {"snapshot": 3789, "consolidated_annex": 3790}},
    }]


def test_historical_seat_altitude_discrepancy_is_reported_when_present():
    result = compare_current_annex(
        fake_official_html(changed_altitude=True), SNAPSHOT, REGISTRY
    )
    assert result["technical_crosscheck_passed"] is False
    assert result["differences"][0]["municipality"] == "Pratiglione"
    assert result["differences"][0]["fields"]["municipal_seat_altitude_m"] == {
        "snapshot": 611, "consolidated_annex": 711,
    }


def test_missing_official_municipality_fails_completeness_check():
    result = compare_current_annex(
        fake_official_html(remove_last=True), SNAPSHOT, REGISTRY
    )
    assert result["technical_crosscheck_passed"] is False
    assert result["rows_examined"] == 26
    assert result["missing_municipalities"] == ["Valprato Soana"]


def test_fake_version_or_unreadable_source_rejected():
    payload = fake_official_html().replace(b"09/08/2016", b"01/01/2008")
    with pytest.raises(ValueError, match="version date"):
        compare_current_annex(payload, SNAPSHOT, REGISTRY)
    with pytest.raises(ValueError, match="title"):
        compare_current_annex(
            fake_official_html().replace(b"Allegato A", b"Unknown"),
            SNAPSHOT, REGISTRY,
        )


def test_incorrect_file_type_rejected_without_saving():
    with pytest.raises(ValueError, match="not an XLSX"):
        source_snapshot(b"<html>login screen</html>", "mean_altitude")
    with pytest.raises(ValueError, match="Expected HTML"):
        source_snapshot(b"PK-not-html", "heating_degree_days")


def test_audit_cli_help_and_local_no_source_report(tmp_path):
    command = ROOT / "scripts/audit_priority_sources.py"
    p = subprocess.run(
        [sys.executable, str(command), "--out-dir", str(tmp_path / "quality")],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert p.returncode == 0, p.stderr
    data = json.loads((tmp_path / "quality" / "audit.json").read_text())
    assert data["technical_pass_count"] == 0
    assert all(r["status"] == "not_acquired"
               for r in data["indicator_results"].values())
    assert data["automatic_promotions"] == 0
    assert data["matrix_before"] == data["matrix_after"]
    assert data["matrix_modified"] is False
    assert data["validated_for_release"] is False
    assert "heating_degree_days" in data["indicator_results"]


def test_audit_local_synthetic_annex_creates_nonpromotion_evidence(tmp_path):
    source = tmp_path / "fixture.html"
    source.write_bytes(fake_official_html())
    cmd = ROOT / "scripts/audit_priority_sources.py"
    out = tmp_path / "quality"
    status = subprocess.run([
        sys.executable, str(cmd), "--annex-html", str(source),
        "--out-dir", str(out), "--strict",
    ], cwd=ROOT, capture_output=True, text=True, check=False)
    assert status.returncode == 1  # other two sources not acquired
    data = json.loads((out / "audit.json").read_text())
    assert data["technical_pass_count"] == 1
    assert data["indicator_results"]["heating_degree_days"]["status"] == "technical_pass"
    assert data["matrix_before"] == data["matrix_after"]
    qa = json.loads(
        (out / "heating_degree_days" / "consolidated_annex_comparison.json").read_text()
    )
    assert qa["rows_examined"] == 27
    assert qa["validated_for_release"] is False
    assert qa["human_source_reviewed"] is False


def test_failed_audit_wont_overwrite_original_report(tmp_path):
    output = tmp_path / "qa"
    cmd = ROOT / "scripts/audit_priority_sources.py"
    base = subprocess.run([sys.executable, str(cmd), "--out-dir", str(output)],
                          cwd=ROOT, capture_output=True, text=True)
    assert base.returncode == 0
    initial = (output / "audit.json").read_bytes()
    again = subprocess.run([sys.executable, str(cmd), "--out-dir", str(output)],
                           cwd=ROOT, capture_output=True, text=True)
    assert again.returncode != 0
    assert (output / "audit.json").read_bytes() == initial


def test_current_matrix_three_indicators_not_auto_promoted():
    with (ROOT / "data/verification_matrix.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 243
    for indicator in ("heating_degree_days", "mean_altitude", "snai_classification"):
        selected = [r for r in rows if r["indicator_id"] == indicator]
        assert len(selected) == 27
        assert not any(r["status"] == "Dato validato" for r in selected)
