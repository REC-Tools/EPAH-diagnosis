"""Stable software release contract: never assert institutional approval."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "stable_v02_gate", ROOT / "scripts/check_v0_2_stable_release.py"
)
assert SPEC and SPEC.loader
STABLE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STABLE)


def test_stable_version_is_synchronized_and_release_is_unapproved():
    data = STABLE.check(ROOT)
    assert data["version"] == "0.2.0"
    assert data["tag"] == "v0.2.0"
    assert data["stable_software"] is True
    assert data["source_only"] is True
    assert data["publication_authorized"] is False
    assert data["attached_private_data"] is False
    assert data["quarantined_cit_included"] is False


def test_stable_gate_rejects_false_institutional_approval(tmp_path):
    import shutil

    copy = tmp_path / "project"
    shutil.copytree(
        ROOT, copy, ignore=shutil.ignore_patterns(
            ".git", ".venv", "outputs", "data", ".pytest_cache"
        )
    )
    path = copy / "docs/releases/v0.2.0.json"
    metadata = json.loads(path.read_text(encoding="utf-8"))
    metadata["institutional_approval"] = "approved"
    path.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(ValueError, match="Stable software cannot assert"):
        STABLE.check(copy)


def test_stable_workflow_needs_manual_dispatch_not_auto_tag():
    s = (ROOT / ".github/workflows/v02-stable-software.yml").read_text(
        encoding="utf-8"
    )
    assert "workflow_dispatch:" in s
    assert "\n  push:" not in s and "\n  pull_request:" not in s
    assert "github.ref == 'refs/heads/main'" in s
    assert "uv run --locked pytest -q" in s
    assert "scripts/check_v0_2_stable_release.py" in s
    assert "gh release create" in s
    assert "--latest=false" in s
    assert "--prerelease" not in s
    assert "v0_2_technical_review_only.zip" not in s
    assert "gh release download" in s
    assert "source_only_v0.2.0_attestation.json" in s
    assert "git_commit_sha" in s
