"""v0.3.0 stable SOFTWARE-only release contract: never asserts data approval."""
from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("stable_v03_gate", ROOT / "scripts/check_v0_3_release.py")
assert SPEC and SPEC.loader
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)

COPY_IGNORE = shutil.ignore_patterns(".git", ".venv", "outputs", "data", "artifacts",
                                     ".pytest_cache", "__pycache__", "uv-cache")


@pytest.fixture
def project(tmp_path: Path) -> Path:
    copy = tmp_path / "project"
    shutil.copytree(ROOT, copy, ignore=COPY_IGNORE)
    return copy


def edit_json(path: Path, **changes) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    for key, value in changes.items():
        if value is None:
            data.pop(key, None)
        else:
            data[key] = value
    path.write_text(json.dumps(data), encoding="utf-8")


def test_repository_passes_and_attestation_is_unapproved():
    data = GATE.check(ROOT)
    assert data["version"] == "0.3.0" and data["tag"] == "v0.3.0"
    assert data["stable_software"] is True and data["source_only"] is True
    assert data["publication_authorized"] is False
    assert data["attached_private_data"] is False
    assert data["candidates_promoted_to_canonical"] == 0
    assert set(data["candidates"]) == {"H47", "H50", "H46", "H03", "H04", "H05", "ADD-HOUSING-01"}


@pytest.mark.parametrize("key, value", [
    ("institutional_approval", "approved"),
    ("scientific_validation", "validated"),
    ("publish_v03_previews_or_atlas", True),
    ("candidates_promoted_to_canonical", 1),
    ("household_inference", True),
])
def test_rejects_approval_or_publication_claims(project, key, value):
    edit_json(project / "docs/releases/v0.3.0.json", **{key: value})
    with pytest.raises(ValueError, match="cannot assert"):
        GATE.check(project)


def test_rejects_candidate_marked_as_approved(project):
    path = project / "docs/releases/v0.3.0.json"
    candidates = json.loads(path.read_text(encoding="utf-8"))["candidates"]
    edit_json(path, candidates=dict(candidates, H46="human_approved"))
    with pytest.raises(ValueError, match="non-releasable status"):
        GATE.check(project)


def test_rejects_missing_candidate_listing(project):
    path = project / "docs/releases/v0.3.0.json"
    candidates = json.loads(path.read_text(encoding="utf-8"))["candidates"]
    candidates.pop("H03")
    edit_json(path, candidates=candidates)
    with pytest.raises(ValueError, match="exactly the candidates"):
        GATE.check(project)


def test_rejects_candidate_promoted_into_canonical_catalog(project):
    path = project / "config/indicators.json"
    catalog = json.loads(path.read_text(encoding="utf-8"))
    catalog["indicators"][0]["id"] = "H46"
    path.write_text(json.dumps(catalog), encoding="utf-8")
    with pytest.raises(ValueError, match="promoted into the canonical catalog"):
        GATE.check(project)


def test_rejects_missing_pipeline_script(project):
    (project / "scripts/audit_h50_istat_independent_v0_3.py").unlink()
    with pytest.raises(ValueError, match="audit_h50_istat_independent_v0_3.py"):
        GATE.check(project)


def test_rejects_unsynchronized_version(project):
    init = project / "src/epah_diagnosis/__init__.py"
    init.write_text(init.read_text(encoding="utf-8").replace("0.3.0", "0.3.1"), encoding="utf-8")
    with pytest.raises(ValueError, match="versions disagree"):
        GATE.check(project)


def test_rejects_automatic_publication_on_push(project):
    workflow = project / GATE.WORKFLOW
    workflow.write_text(workflow.read_text(encoding="utf-8").replace(
        "on:\n  workflow_dispatch:\n", "on:\n  workflow_dispatch:\n  push:\n    branches: [main]\n"),
        encoding="utf-8")
    with pytest.raises(ValueError, match="manual dispatch"):
        GATE.check(project)


def test_rejects_notes_without_scope_disclosure(project):
    notes = project / "docs/releases/v0.3.0.md"
    notes.write_text(notes.read_text(encoding="utf-8").replace("CIT", "C.I.T."), encoding="utf-8")
    with pytest.raises(ValueError, match="disclose scope: CIT"):
        GATE.check(project)


def test_cli_writes_attestation_once(tmp_path):
    out = tmp_path / "attestation.json"
    sha = "a" * 40
    assert GATE.main(["--commit-sha", sha, "--json-out", str(out)]) == 0
    record = json.loads(out.read_text(encoding="utf-8"))
    assert record["git_commit_sha"] == sha and record["publication_authorized"] is False
    assert GATE.main(["--commit-sha", sha, "--json-out", str(out)]) == 1  # never overwrite
    assert GATE.main(["--commit-sha", "not-a-sha"]) == 1


def test_workflow_is_manual_main_only_and_verifies_release():
    s = (ROOT / GATE.WORKFLOW).read_text(encoding="utf-8")
    assert "workflow_dispatch:" in s
    assert "\n  push:" not in s and "\n  pull_request:" not in s
    assert "github.ref == 'refs/heads/main'" in s
    assert "uv run --locked pytest -q" in s
    assert "scripts/check_v0_3_evidence.py" in s
    assert "scripts/check_v0_3_release.py" in s
    assert "gh release create" in s and "--prerelease" not in s
    assert "gh release download" in s and "git_commit_sha" in s
    assert "source_only_v0.3.0_attestation.json" in s
