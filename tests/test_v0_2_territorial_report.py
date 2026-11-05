"""V0.2 report QA: independent synthetic bundle, PDF content and provenance."""
from __future__ import annotations

import csv
import importlib.util
import json
import shutil
from pathlib import Path

import pytest
from pypdf import PdfReader

from epah_diagnosis.report_v0_2 import computed_facts, verified_data
from epah_diagnosis.release_artifacts import sha256_file
from test_release_bundle import _make_fixture, bundle

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_v0_2_territorial_report", ROOT / "scripts/build_v0_2_territorial_report.py"
)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


@pytest.fixture(scope="module")
def finished_pilot(tmp_path_factory):
    root = tmp_path_factory.mktemp("v02-report-fixture")
    inputs = _make_fixture(root)
    # Entirely synthetic, with fabricated municipal values and shapes.
    output = bundle.build_bundle(**inputs)
    return inputs, output


def test_v02_technical_report_has_maps_years_and_no_false_release(finished_pilot, tmp_path):
    inputs, pilot = finished_pilot
    original_manifest = sha256_file(pilot / "release_manifest.json")
    out = tmp_path / "v0.2-technical-report"
    result = MOD.build_report(
        pilot, out, inputs["municipality_file"], inputs["release_config"]
    )
    assert result == out
    manifest = json.loads((out / "report_manifest_v0_2.json").read_text(encoding="utf-8"))
    facts = json.loads((out / "diagnostic_facts_v0_2.json").read_text(encoding="utf-8"))
    assert manifest["source_manifest_sha256"] == original_manifest
    assert manifest["cit_included"] is False
    assert manifest["no_household_attribution"] is True
    assert manifest["status"] == "technical_draft_do_not_publish"
    assert facts["municipalities"] == 27
    assert len(facts["indicators"]) == 8
    assert facts["composite_energy_poverty_score"] is False
    for name, meta in manifest["artifacts"].items():
        assert meta["sha256"] == sha256_file(out / name)
    pdf = PdfReader(str(out / MOD.REPORT_FILE))
    assert 9 <= len(pdf.pages) <= 12
    text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    for token in (
        "26-IT-Unione-TA26", "27 Comuni", "2011",
        "FERVORES", "SNAI", "NON PUBBLICARE", "Lettura incrociata",
    ):
        assert token in text
    assert "CIT Piemonte" not in text
    assert sha256_file(pilot / "release_manifest.json") == original_manifest


def test_missing_source_bundle_is_blocked_without_output(tmp_path, finished_pilot):
    inputs, _ = finished_pilot
    out = tmp_path / "absent-bundle-report"
    with pytest.raises((OSError, ValueError)):
        MOD.build_report(tmp_path / "missing", out,
                         inputs["municipality_file"], inputs["release_config"])
    assert not out.exists()


def test_existing_output_is_never_overwritten(finished_pilot, tmp_path):
    inputs, pilot = finished_pilot
    out = tmp_path / "previous-report"
    out.mkdir()
    marker = out / "keep.txt"
    marker.write_text("preserve evidence", encoding="utf-8")
    with pytest.raises(FileExistsError, match="Preserve"):
        MOD.build_report(pilot, out, inputs["municipality_file"], inputs["release_config"])
    assert marker.read_text(encoding="utf-8") == "preserve evidence"


def test_bundle_tampering_blocks_v02_without_affecting_input(finished_pilot, tmp_path):
    inputs, pilot = finished_pilot
    copy = tmp_path / "tampered-pilot"
    shutil.copytree(pilot, copy)
    source = copy / "municipality_profile.csv"
    source.write_bytes(source.read_bytes().replace(b"21", b"99", 1))
    before = source.read_bytes()
    out = tmp_path / "blocked-v02"
    with pytest.raises(ValueError, match="Manifest checksum"):
        MOD.build_report(copy, out, inputs["municipality_file"], inputs["release_config"])
    assert not out.exists()
    assert source.read_bytes() == before


def test_bad_config_cannot_claim_approval(tmp_path):
    path = tmp_path / "bad.json"
    config = json.loads(MOD.CONFIG.read_text(encoding="utf-8"))
    config["publication_status"] = "approved"
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError, match="deny institutional publication"):
        MOD.validate_config(path)


def test_separate_descriptive_dimensions_are_not_an_index(finished_pilot):
    inputs, pilot = finished_pilot
    profiles, _ = verified_data(pilot, inputs["municipality_file"], inputs["release_config"])
    facts = computed_facts(profiles)
    assert facts["descriptive_overlap"]["denominator_municipalities"] == 27
    assert 0 <= facts["descriptive_overlap"]["above_all_three_medians"] <= 27
    assert facts["descriptive_overlap"]["benchmark_years_differ"] is True
    assert "no additive index" in facts["descriptive_overlap"]["rule"]
    assert not facts["composite_energy_poverty_score"]
    assert facts["indicators"]["old_building_stock_pct"]["reference_years"] == ["2011"]
    assert facts["indicators"]["income_vulnerability_pct"]["reference_years"] == ["2024"]


def test_cli_help_is_read_only(tmp_path):
    import subprocess
    import sys
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_v0_2_territorial_report.py"), "--help"],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert result.returncode == 0
    assert "--bundle" in result.stdout and "--out-dir" in result.stdout
