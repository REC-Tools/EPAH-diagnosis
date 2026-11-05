"""Safety and orchestration regression tests (all inputs are synthetic)."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pytest

from epah_diagnosis import pipeline


def _args(profile: str, destination: Path, **overrides):
    values = {
        "profile": profile, "out_dir": destination,
        "fuel_source": None, "age_source": None, "as_of": None,
        "sources": None, "road_zip": None, "boundaries_zip": None,
        "school_registry": None, "school_pathways": None,
        "download": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def _root(tmp_path: Path) -> Path:
    (tmp_path / "data").mkdir()
    (tmp_path / "data/municipalities.csv").write_text(
        "municipality,istat_code\nA,001001\n", encoding="utf-8"
    )
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for name in (
        "prepare_piemonte_cit_wide.py",
        "build_v0_2_cit_quarantine_comparison.py",
        "acquire_accessibility_inputs.py",
    ):
        (scripts / name).write_text("# synthetic fixture\n", encoding="utf-8")
    return tmp_path


def _cit_args(tmp_path, monkeypatch):
    root = _root(tmp_path)
    raw = root / "data/downloads"
    raw.mkdir()
    fuel = raw / "fuel.csv"
    age = raw / "age.csv"
    fuel.write_bytes(b"synthetic fuel data\n")
    age.write_bytes(b"synthetic age data\n")
    monkeypatch.setattr(pipeline, "CIT_HASHES", {
        "fuel": hashlib.sha256(fuel.read_bytes()).hexdigest(),
        "age": hashlib.sha256(age.read_bytes()).hexdigest(),
    })
    args = _args(
        "cit-quarantine", Path("outputs/quality/cit_qa_run_01"),
        fuel_source=fuel, age_source=age, as_of="2026-10-30",
    )
    return root, args


def test_cit_plan_does_not_create_any_output(tmp_path, monkeypatch):
    root, args = _cit_args(tmp_path, monkeypatch)
    plan = pipeline.make_plan(args, root)
    assert plan["review_status"] == pipeline.STATUS_CIT
    assert [s["name"] for s in plan["steps"]] == [
        "prepare_fuel", "prepare_age", "qa_compare"
    ]
    assert plan["publication_allowed"] is False
    assert plan["network_download"] is False
    assert not Path(plan["destination"]).exists()
    assert all("finalize" not in " ".join(s["command"])
               for s in plan["steps"])
    assert all("build_v0_2_cit_preview" not in " ".join(s["command"])
               for s in plan["steps"])


def test_cit_hash_mismatch_blocks_before_any_files_written(tmp_path, monkeypatch):
    root, args = _cit_args(tmp_path, monkeypatch)
    monkeypatch.setattr(pipeline, "CIT_HASHES", {"fuel": "0" * 64, "age": "1" * 64})
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        pipeline.make_plan(args, root)
    assert not (root / "outputs").exists()


def test_nonnew_output_and_outside_quality_refused(tmp_path, monkeypatch):
    root, args = _cit_args(tmp_path, monkeypatch)
    args.out_dir = Path("data/derived/unsafe")
    with pytest.raises(ValueError, match="outputs/quality"):
        pipeline.make_plan(args, root)
    args.out_dir = Path("outputs/quality/reused")
    (root / args.out_dir).mkdir(parents=True)
    with pytest.raises(FileExistsError, match="fresh"):
        pipeline.make_plan(args, root)


def test_cit_run_creates_qa_only_report_and_preserves_originals(tmp_path, monkeypatch):
    root, args = _cit_args(tmp_path, monkeypatch)
    plan = pipeline.make_plan(args, root)
    before = [(root / "data/downloads/fuel.csv").read_bytes(),
              (root / "data/downloads/age.csv").read_bytes(),
              (root / "data/municipalities.csv").read_bytes()]
    called = []
    def synthetic_runner(command, cwd):
        called.append(command)
        if "build_v0_2_cit_quarantine_comparison.py" in command[1]:
            review = Path(plan["review_file"])
            review.parent.mkdir(parents=True, exist_ok=True)
            review.write_text(json.dumps({
                "status": "technical_QA_only_incomplete_do_not_publish",
                "valid_municipalities": 26, "municipalities_expected": 27,
                "excluded": [{"istat_code": "001199", "municipality": "Pont Canavese"}],
            }), encoding="utf-8")
        return 0
    monkeypatch.setattr(pipeline, "_execute_command", synthetic_runner)
    assert pipeline.execute(plan, root) == 0
    assert len(called) == 3
    report = json.loads((Path(plan["destination"]) /
                         "pipeline_run_report.json").read_text(encoding="utf-8"))
    assert report["run_status"] == pipeline.STATUS_CIT
    assert report["publication_allowed"] is False
    assert report["automatic_promotions"] == 0
    assert report["review"]["excluded_istat_codes"] == ["001199"]
    after = [(root / "data/downloads/fuel.csv").read_bytes(),
             (root / "data/downloads/age.csv").read_bytes(),
             (root / "data/municipalities.csv").read_bytes()]
    assert before == after


def test_failure_stops_following_stages_and_records_blocker(tmp_path, monkeypatch):
    root, args = _cit_args(tmp_path, monkeypatch)
    plan = pipeline.make_plan(args, root)
    called = []
    monkeypatch.setattr(pipeline, "_execute_command",
                        lambda command, cwd: called.append(command) or 3)
    assert pipeline.execute(plan, root) == 1
    assert len(called) == 1
    report = json.loads((Path(plan["destination"]) /
                         "pipeline_run_report.json").read_text(encoding="utf-8"))
    assert report["run_status"] == "blocked"
    assert report["steps"] == [{"name": "prepare_fuel", "return_code": 3}]
    assert "prepare_fuel" in report["blocked_reason"]


def test_cit_never_downloads_or_accepts_accessibility_flags(tmp_path, monkeypatch):
    root, args = _cit_args(tmp_path, monkeypatch)
    args.download = True
    with pytest.raises(ValueError, match="no downloads"):
        pipeline.make_plan(args, root)


def test_accessibility_offline_requires_explicit_originals(tmp_path):
    root = _root(tmp_path)
    args = _args("accessibility-intake", Path("outputs/quality/intake_01"))
    with pytest.raises(ValueError, match="supply a local"):
        pipeline.make_plan(args, root)


def test_accessibility_intake_only_executes_the_source_audit(tmp_path, monkeypatch):
    root = _root(tmp_path)
    road = root / "downloaded_road.zip"
    boundaries = root / "downloaded_istat.zip"
    road.write_bytes(b"synthetic\n")
    boundaries.write_bytes(b"synthetic\n")
    args = _args("accessibility-intake", Path("outputs/quality/intake_01"),
                 road_zip=road, boundaries_zip=boundaries)
    plan = pipeline.make_plan(args, root)
    assert len(plan["steps"]) == 1
    assert plan["steps"][0]["name"] == "official_source_intake"
    assert "--strict" in plan["steps"][0]["command"]
    assert "--download" not in plan["steps"][0]["command"]
    def fake_runner(command, cwd):
        audit = Path(plan["review_file"])
        audit.parent.mkdir(parents=True, exist_ok=True)
        audit.write_text(json.dumps({
            "all_selected_inputs_available": True, "selected_source_count": 2,
            "validated_for_release": False, "automatic_promotions": 0,
        }), encoding="utf-8")
        return 0
    monkeypatch.setattr(pipeline, "_execute_command", fake_runner)
    assert pipeline.execute(plan, root) == 0
    report = json.loads((Path(plan["destination"]) /
                         "pipeline_run_report.json").read_text(encoding="utf-8"))
    assert report["run_status"] == pipeline.STATUS_ACCESS
    assert report["scientific_approval"] == "not_assessed"


def test_accessibility_network_download_requires_explicit_flag(tmp_path):
    root = _root(tmp_path)
    args = _args("accessibility-intake", Path("outputs/quality/acq_run_01"),
                 sources="road,boundaries", download=True)
    plan = pipeline.make_plan(args, root)
    assert plan["network_download"] is True
    assert "--download" in plan["steps"][0]["command"]
    assert not Path(plan["destination"]).exists()


def test_accessibility_cannot_claim_success_on_incomplete_audit(tmp_path, monkeypatch):
    root = _root(tmp_path)
    args = _args("accessibility-intake", Path("outputs/quality/acq_run_01"),
                 sources="road", download=True)
    plan = pipeline.make_plan(args, root)
    def bad_runner(command, cwd):
        audit = Path(plan["review_file"])
        audit.parent.mkdir(parents=True, exist_ok=True)
        audit.write_text(json.dumps({
            "all_selected_inputs_available": False, "selected_source_count": 1,
            "validated_for_release": False, "automatic_promotions": 0,
        }), encoding="utf-8")
        return 0
    monkeypatch.setattr(pipeline, "_execute_command", bad_runner)
    assert pipeline.execute(plan, root) == 1
    report = json.loads((Path(plan["destination"]) /
                         "pipeline_run_report.json").read_text(encoding="utf-8"))
    assert report["run_status"] == "blocked"


def test_input_source_flags_are_not_accepted_when_unselected(tmp_path):
    root = _root(tmp_path)
    road = root / "road.zip"
    road.write_bytes(b"synthetic")
    args = _args("accessibility-intake", Path("outputs/quality/acq_run_01"),
                 sources="boundaries", road_zip=road)
    with pytest.raises(ValueError, match="add source"):
        pipeline.make_plan(args, root)


def test_cit_plan_uses_same_verified_sha_values_as_original_parser(monkeypatch):
    import importlib.util
    parser_file = ROOT / "scripts/prepare_piemonte_cit_wide.py"
    spec = importlib.util.spec_from_file_location("cit_source_hashes_qa", parser_file)
    assert spec and spec.loader
    parser_module = importlib.util.module_from_spec(spec)
    # Original preparer depends on a same-directory sibling script.
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    spec.loader.exec_module(parser_module)
    assert pipeline.CIT_HASHES == parser_module.EXPECTED_SOURCE_HASHES
