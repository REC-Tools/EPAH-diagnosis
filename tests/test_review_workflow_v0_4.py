"""Synthetic orchestration regressions; no territorial approval is exercised."""
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from epah_diagnosis.review_workflow_v0_4 import CANDIDATES, ReviewInputs, make_plan, run


def setup(tmp_path, complete=True):
    root = tmp_path / "checkout"
    (root / "scripts").mkdir(parents=True)
    for name in ("build_v0_4_visual_atlas.py", "build_v0_4_review_pack.py",
                 "build_v0_4_output_hub.py", "audit_v0_4_output_quality.py"):
        (root / "scripts" / name).write_text("# synthetic reviewed command\n")
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "pilot").mkdir()
    for name in ("registry.csv", "release.json", "h47.zip"):
        (sources / name).write_text("synthetic")
    optional = {}
    if complete:
        for name in CANDIDATES:
            path = sources / name
            if name.endswith("_dir"):
                path.mkdir()
            else:
                path.write_text("synthetic")
            optional[name] = path
    inputs = ReviewInputs(sources / "pilot", sources / "registry.csv", sources / "release.json", **optional)
    return root, inputs, tmp_path / "new-run"


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def successful_runner(target, *, incomplete=False, bad_audit=False):
    def runner(command, **kwargs):
        script = Path(command[2]).name
        if script == "build_v0_4_visual_atlas.py":
            write(target / "atlas/atlas_manifest.json", {
                "synthetic_fixture": True, "status": "technical_draft_do_not_publish",
                "municipalities": 27, "indicator_slots": 16, "publication_allowed": False,
                "indicators_available": [f"synthetic_{i}" for i in range(15 if incomplete else 16)],
                "indicators_pending": ["synthetic_15"] if incomplete else [],
            })
        elif script == "build_v0_4_review_pack.py":
            write(target / "review/manifest.json", {"synthetic_fixture": True})
        elif script == "build_v0_4_output_hub.py":
            write(target / "hub/manifest.json", {"synthetic_fixture": True})
        else:
            pack = "--pack" in command
            write(target / "qa" / ("pack.json" if pack else "hub.json"), {
                "status": "failed" if bad_audit else ("technical_output_consistency_passed" if pack
                                                       else "technical_bundle_consistency_passed"),
                "scientific_approval": False, "publication_allowed": False,
            })
        return SimpleNamespace(returncode=0)
    return runner


def test_plan_is_read_only_and_preserves_candidate_count_inputs(tmp_path):
    root, inputs, target = setup(tmp_path)
    plan = make_plan(inputs, target, root=root)
    assert not target.exists() and plan["can_run"]
    assert plan["network_download"] is plan["scientific_approval"] is False
    atlas, review = [s["command"] for s in plan["steps"][:2]]
    for name in CANDIDATES[:3]:
        flag = "--" + name.replace("_", "-")
        assert atlas[atlas.index(flag) + 1] == review[review.index(flag) + 1]
    assert [s["name"] for s in plan["steps"]] == ["atlas", "review", "hub", "audit_pack", "audit_hub"]


def test_incomplete_run_requires_explicit_opt_in_before_any_write(tmp_path):
    root, inputs, target = setup(tmp_path, complete=False)
    assert not make_plan(inputs, target, root=root)["can_run"]
    with pytest.raises(ValueError, match="Incomplete"):
        run(inputs, target, root=root)
    assert not target.exists()


def test_review_with_absences_cannot_be_reported_as_complete(tmp_path):
    root, inputs, target = setup(tmp_path, complete=False)
    receipt = run(inputs, target, root=root, allow_incomplete=True,
                  runner=successful_runner(target, incomplete=True))
    assert receipt["status"] == "technical_review_incomplete"
    assert receipt["complete_snapshot"] is receipt["scientific_approval"] is False
    assert len(receipt["artifacts_sha256"]) == 5


def test_successful_snapshot_is_still_not_scientifically_approved(tmp_path):
    root, inputs, target = setup(tmp_path)
    receipt = run(inputs, target, root=root, runner=successful_runner(target))
    assert receipt["status"] == "technical_review_ready" and receipt["complete_snapshot"]
    assert receipt["publication_allowed"] is receipt["scientific_approval"] is False
    assert receipt["visual_review_completed"] is False


def test_failure_stops_the_chain_and_retains_logs_and_receipt(tmp_path):
    root, inputs, target = setup(tmp_path)
    calls = []
    def fail(command, **kwargs):
        calls.append(command)
        kwargs["stdout"].write("synthetic input gate failure")
        return SimpleNamespace(returncode=2)
    with pytest.raises(RuntimeError, match="atlas failed"):
        run(inputs, target, root=root, runner=fail)
    assert len(calls) == 1
    assert json.loads((target / "run.json").read_text())["status"] == "failed"
    assert "synthetic input gate" in (target / "logs/atlas.log").read_text()
    assert not (target / "review").exists()


def test_zero_exit_code_cannot_hide_unsuccessful_audit(tmp_path):
    root, inputs, target = setup(tmp_path)
    with pytest.raises(ValueError, match="unsuccessful independent audit"):
        run(inputs, target, root=root, runner=successful_runner(target, bad_audit=True))
    assert json.loads((target / "run.json").read_text())["status"] == "failed"


def test_full_request_rejects_observations_missing_despite_supplied_directories(tmp_path):
    root, inputs, target = setup(tmp_path)
    with pytest.raises(ValueError, match="Missing indicator observations"):
        run(inputs, target, root=root, runner=successful_runner(target, incomplete=True))


def test_prior_run_is_never_touched(tmp_path):
    root, inputs, target = setup(tmp_path)
    target.mkdir()
    (target / "prior.txt").write_bytes(b"keep")
    with pytest.raises(FileExistsError):
        run(inputs, target, root=root)
    assert (target / "prior.txt").read_bytes() == b"keep"


def test_protected_output_and_source_overlap_are_rejected(tmp_path):
    root, inputs, _ = setup(tmp_path)
    with pytest.raises(ValueError, match="protected"):
        make_plan(inputs, root / "data/new", root=root)
    with pytest.raises(ValueError, match="overlap"):
        make_plan(inputs, inputs.bundle / "new", root=root)


def test_climate_pair_is_not_silently_separated(tmp_path):
    root, inputs, target = setup(tmp_path)
    with pytest.raises(ValueError, match="H03 and H04 together"):
        make_plan(replace(inputs, h04_dir=None), target, root=root, allow_incomplete=True)
