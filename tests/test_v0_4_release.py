"""Synthetic release regressions: software distribution cannot approve territory."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import re
import textwrap

import pytest

from bash_syntax import check_bash_syntax

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("release_v04", ROOT / "scripts/check_v0_4_release.py")
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


@pytest.fixture
def project(tmp_path):
    destination = tmp_path / "project"
    shutil.copytree(ROOT, destination, ignore=shutil.ignore_patterns(
        ".git", ".venv", "outputs", "data", "artifacts", "__pycache__",
        ".pytest_cache", "EPAH_v*_technical_partial_*"))
    from release_fixtures import restore_version
    restore_version(destination, "0.4.0")
    return destination


def test_historical_v04_release_remains_source_only(project):
    record = GATE.check(project)
    assert record["source_only"] is True
    assert record["publication_authorized"] is False
    assert record["scientific_approval"] is False
    assert record["attached_private_data"] is False
    assert record["candidates_promoted_to_canonical"] == 0


@pytest.mark.parametrize("key,value", [
    ("publish_territorial_outputs", True), ("publish_pdf_or_data_assets", True),
    ("institutional_approval", "approved"), ("candidates_promoted_to_canonical", 1),
    ("territorial_snapshot_complete", True),
    ("allowed_release_assets", ["territorial.zip"]),
    ("v05_proposals", {"contracts": 18, "municipal_series_added": 1, "scientific_approval": False}),
    ("documented_local_snapshot", {"available_series": 16, "pending": [], "scientific_approval": True}),
])
def test_rejects_scope_drift(project, key, value):
    path = project / "docs/releases/v0.4.0.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    record[key] = value
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError, match="scope or approval"):
        GATE.check(project)


@pytest.mark.parametrize("before,after", [
    ("workflow_dispatch:", "push:"),
    ("refs/heads/main", "refs/heads/other"),
    ('test "$EXPECTED_SHA" = "$GITHUB_SHA"', "true"),
    ('test "$tag_sha" = "$GITHUB_SHA"', "true"),
    ("actions/checkout@11d5960a326750d5838078e36cf38b85af677262", "actions/checkout@main"),
    ('gh release create "$TAG" source_only_v0.4.0_attestation.json', 'gh release create "$TAG" territorial.zip'),
])
def test_rejects_unsafe_release_workflow(project, before, after):
    path = project / GATE.WORKFLOW
    text = path.read_text(encoding="utf-8")
    assert before in text
    path.write_text(text.replace(before, after), encoding="utf-8")
    with pytest.raises(ValueError):
        GATE.check(project)


def test_version_mismatch_blocks_release(project):
    path = project / "src/epah_diagnosis/__init__.py"
    path.write_text('__version__ = "0.4.1"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="versions"):
        GATE.check(project)


def test_historical_gate_is_not_relaxed():
    spec = importlib.util.spec_from_file_location("historical", ROOT / "scripts/check_v0_3_release.py")
    historical = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(historical)
    with pytest.raises(ValueError, match="versions disagree"):
        historical.check(ROOT)


def test_attestation_requires_commit_and_never_overwrites(tmp_path, project):
    out = tmp_path / "attestation.json"
    assert GATE.main(["--root", str(project), "--json-out", str(out)]) == 1
    assert not out.exists()
    assert GATE.main(["--root", str(project), "--commit-sha", "bad", "--json-out", str(out)]) == 1
    sha = "a" * 40
    assert GATE.main(["--root", str(project), "--commit-sha", sha, "--json-out", str(out)]) == 0
    before = out.read_bytes()
    assert json.loads(before)["git_commit_sha"] == sha
    assert GATE.main(["--root", str(project), "--commit-sha", "b" * 40, "--json-out", str(out)]) == 1
    assert out.read_bytes() == before


def test_manual_workflow_syntax_and_privilege_boundary():
    workflow = (ROOT / GATE.WORKFLOW).read_text(encoding="utf-8")
    assert "\npermissions:\n  contents: read\n" in workflow
    assert "\n    permissions:\n      contents: write\n" in workflow
    blocks = re.findall(r"        run: \|\n((?:          .*\n|\n)+)", workflow)
    assert len(blocks) == 3
    for block in blocks:
        check_bash_syntax(textwrap.dedent(block), label="v0.4 release")
    script = textwrap.dedent(blocks[-1])
    compile(script.split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0], "release-verification", "exec")


def test_cli_version_matches_installed_package():
    from epah_diagnosis import __version__
    result = subprocess.run([sys.executable, "-c",
                             "from epah_diagnosis.workflow_cli import main; main()", "--version"],
                            capture_output=True, text=True, check=True)
    assert result.stdout.strip() == f"epah {__version__}"
