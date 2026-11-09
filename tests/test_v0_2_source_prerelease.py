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


def v0_2_0_snapshot(tmp_path):
    """Project copy with the historical 0.2.0 version restored (tree is now 0.3.0)."""
    import shutil

    copy = tmp_path / "repo"
    shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(
        ".git", ".venv", "outputs", "data", "artifacts", ".pytest_cache"))
    lock_old = 'name = "epah-diagnosis"' + chr(10) + 'version = "0.3.0"'
    for rel, old, new in (
        ("pyproject.toml", 'version = "0.3.0"', 'version = "0.2.0"'),
        ("src/epah_diagnosis/__init__.py", '"0.3.0"', '"0.2.0"'),
        ("uv.lock", lock_old, lock_old.replace("0.3.0", "0.2.0")),
    ):
        path = copy / rel
        text = path.read_text(encoding="utf-8")
        assert text.count(old) == 1, rel
        path.write_text(text.replace(old, new), encoding="utf-8")
    return copy


def test_v02_rc1_source_contract_matches_locked_project(tmp_path):
    report = MOD.check(v0_2_0_snapshot(tmp_path))
    assert report["source_only"] is True
    assert report["prerelease"] is True
    assert report["publication_authorized"] is False
    assert report["core_municipalities"] == 27
    assert report["core_indicators"] == 9


def test_reject_any_attempt_to_claim_approval(tmp_path):
    r = v0_2_0_snapshot(tmp_path)
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
    assert "isLatest" not in content.split("--json ")[-1]  # no unsupported CLI fields
    assert "--json tagName,isPrerelease,isDraft,assets" in content
    assert "gh release download" in content
    assert "tag_sha=" in content
    assert "Published prerelease attestation/tag disagree" in content
    assert "without republishing" in content
    assert '".github/workflows/v02-technical-prerelease.yml"' in content


def test_rc1_gate_refuses_current_0_3_0_tree():
    with pytest.raises(ValueError, match="must all agree"):
        MOD.check(ROOT)
