"""V0.2.0-rc1 must be explicitly source-only and unapproved."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "v02_rc_gate", ROOT / "scripts/check_v0_2_source_release.py"
)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def test_v02_rc1_source_contract_matches_locked_project():
    report = MOD.check(ROOT)
    assert report["source_only"] is True
    assert report["prerelease"] is True
    assert report["publication_authorized"] is False
    assert report["core_municipalities"] == 27
    assert report["core_indicators"] == 9


def test_reject_any_attempt_to_claim_approval(tmp_path):
    import shutil
    shutil.copytree(ROOT, tmp_path / "repo",
                    ignore=shutil.ignore_patterns(".git", ".venv", "outputs", "data"))
    r = tmp_path / "repo"
    metadata = r / "docs/releases/v0.2.0-rc1.json"
    value = json.loads(metadata.read_text(encoding="utf-8"))
    value["institutional_approval"] = "approved"
    metadata.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="institutional publication"):
        MOD.check(r)


def test_release_workflow_is_prerelease_source_only_with_explicit_gate():
    content = (ROOT / ".github/workflows/v02-technical-prerelease.yml").read_text(
        encoding="utf-8"
    )
    assert "workflow_dispatch:" in content
    assert '"main"' in content
    assert "--prerelease --latest=false" in content
    assert "scripts/check_v0_2_source_release.py" in content
    assert "uv run --locked pytest -q" in content
    assert "v0_2_technical_review_only.zip" not in content
    assert "source_only_v0.2.0-rc1_attestation.json" in content
    assert not (ROOT / ".github/workflows/v02-ci-diagnostics.yml").exists()
    assert '--commit-sha "$GITHUB_SHA"' in content
