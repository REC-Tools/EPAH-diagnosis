"""Synthetic tests for Pont Canavese CIT review packet evidence and safeguards."""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from test_build_v0_2_cit_quarantine_comparison import MOD, REGISTRY, make_sources


SPEC = importlib.util.spec_from_file_location(
    "cit_source_packet", ROOT / "scripts/build_cit_source_review_packet.py"
)
assert SPEC and SPEC.loader
PACKET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACKET)


def make_complete_run(tmp_path: Path):
    source_fuel, source_age = make_sources(tmp_path)
    run = tmp_path / "run"
    run.mkdir()
    shutil.copytree(source_fuel, run / "cit_fuel")
    shutil.copytree(source_age, run / "cit_age")
    # Enrich the minimal synthetic conflict fixture with native line/total
    # evidence; keep its two QA documents exactly consistent.
    for mode in ("fuel", "age"):
        folder = run / ("cit_" + mode)
        qa_file = folder / "cit_qa.json"
        review_file = folder / "cit_conflicts_for_review.json"
        qa = json.loads(qa_file.read_text(encoding="utf-8"))
        review = json.loads(review_file.read_text(encoding="utf-8"))
        conflict = review["conflicts"][0]
        conflict["differing_count_fields"] = ["gasolio" if mode == "fuel" else "numero_2006_2010"]
        for i, row in enumerate(conflict["source_records"]):
            row["line"] = i + 10
            row["row_total"] = sum(row["counts"].values())
            row["observed_key"] = "001199"
            row["observed_name"] = "Pont Canavese"
        qa["source_schema"]["quarantined_duplicate_conflicts"] = review["conflicts"]
        qa_file.write_text(json.dumps(qa), encoding="utf-8")
        review_file.write_text(json.dumps(review), encoding="utf-8")
    MOD.create_review(run / "cit_fuel", run / "cit_age", REGISTRY,
                      run / "cit_review")
    report = {
        "profile": "cit-quarantine",
        "run_status": "technical_incomplete_do_not_publish",
        "publication_allowed": False,
        "scientific_approval": "not_assessed",
        "automatic_promotions": 0,
        "source_inputs": [
            {"name": mode, "sha256": digest}
            for mode, digest in MOD.EXPECTED_SOURCE_HASHES.items()
        ],
        "steps": [
            {"name": name, "return_code": 0}
            for name in ("prepare_fuel", "prepare_age", "qa_compare")
        ],
    }
    (run / "pipeline_run_report.json").write_text(
        json.dumps(report), encoding="utf-8")
    return run


def test_verified_run_generates_unapproved_packet_without_modifying_sources(tmp_path):
    run = make_complete_run(tmp_path)
    raw_before = (run / "cit_fuel/cit_fuel_27.csv").read_bytes()
    dest = tmp_path / "outputs/quality/packet_01"
    result = PACKET.build_packet(run, dest, REGISTRY, tmp_path / "outputs/quality")
    assert result == dest
    data = json.loads((dest / "cit_pont_evidence.json").read_text(encoding="utf-8"))
    assert data["publication_allowed"] is False
    assert data["approved_for_release"] is False
    assert data["decision"] is None
    assert data["istat_code"] == "001199"
    assert data["ambiguous_age_groups_26_towns"] == 52
    assert set(data["conflicts"]) == {"fuel", "age"}
    assert data["original_source_sha256"] == MOD.EXPECTED_SOURCE_HASHES
    draft = (dest / "request_to_region_draft.md").read_text(encoding="utf-8")
    assert "Pont Canavese" in draft and "BOZZA NON INVIATA" in draft
    assert "001199" in draft
    assert "Combustibili" in draft and "Età generatori" in draft
    checklist = (dest / "human_review_checklist.md").read_text(encoding="utf-8")
    assert "nessuna approvazione automatica" in checklist
    assert (run / "cit_fuel/cit_fuel_27.csv").read_bytes() == raw_before
    assert not (dest / "approved.json").exists()


def test_packet_refuses_to_overwrite_previous_review(tmp_path):
    run = make_complete_run(tmp_path)
    dest = tmp_path / "outputs/quality/packet_02"
    PACKET.build_packet(run, dest, REGISTRY, tmp_path / "outputs/quality")
    before = (dest / "cit_pont_evidence.json").read_bytes()
    with pytest.raises(FileExistsError, match="exists"):
        PACKET.build_packet(run, dest, REGISTRY, tmp_path / "outputs/quality")
    assert (dest / "cit_pont_evidence.json").read_bytes() == before


def test_tampered_comparison_summary_blocks_before_any_output(tmp_path):
    run = make_complete_run(tmp_path)
    summary_file = run / "cit_review/cit_26_qa_summary.json"
    summary = json.loads(summary_file.read_text(encoding="utf-8"))
    summary["output_csv_sha256"] = "0" * 64
    summary_file.write_text(json.dumps(summary), encoding="utf-8")
    dest = tmp_path / "outputs/quality/packet_03"
    with pytest.raises(ValueError, match="QA evidence"):
        PACKET.build_packet(run, dest, REGISTRY, tmp_path / "outputs/quality")
    assert not dest.exists()


def test_source_record_tampering_blocks_packet(tmp_path):
    run = make_complete_run(tmp_path)
    path = run / "cit_fuel/cit_conflicts_for_review.json"
    review = json.loads(path.read_text(encoding="utf-8"))
    review["conflicts"][0]["source_records"][0]["counts"]["gasolio"] = 999999
    path.write_text(json.dumps(review), encoding="utf-8")
    dest = tmp_path / "outputs/quality/packet_04"
    with pytest.raises(ValueError):
        PACKET.build_packet(run, dest, REGISTRY, tmp_path / "outputs/quality")
    assert not dest.exists()


def test_incomplete_pipeline_run_cannot_generate_packet(tmp_path):
    run = make_complete_run(tmp_path)
    path = run / "pipeline_run_report.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    report["run_status"] = "blocked"
    path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="completed CIT"):
        PACKET.inspect_run(run, REGISTRY)


def test_outside_quality_directory_refused(tmp_path):
    run = make_complete_run(tmp_path)
    with pytest.raises(ValueError, match="outputs/quality"):
        PACKET.build_packet(run, tmp_path / "data/indicators/invalid", REGISTRY,
                            tmp_path / "outputs/quality")
    assert not (tmp_path / "data/indicators/invalid").exists()


def test_packet_refuses_to_claim_publication_in_prose(tmp_path):
    run = make_complete_run(tmp_path)
    evidence = PACKET.inspect_run(run, REGISTRY)
    content = PACKET.draft_request(evidence)
    assert "BOZZA NON INVIATA" in content
    assert "Non abbiamo selezionato" in content
    assert "aggiornamento ufficiale" in content
