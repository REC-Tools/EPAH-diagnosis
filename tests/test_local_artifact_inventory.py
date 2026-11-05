"""Offline tests for safe local data / artifact Git inventory."""
from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "local_artifact_inventory", ROOT / "scripts/audit_local_artifacts.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _write(root: Path, relative: str, content: str = "test") -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def test_categories_do_not_claim_approval():
    assert MODULE.category("data/indicators/new.csv") == "indicator_needs_source_review"
    assert MODULE.category("data/geography/new.geojson") == "geography_needs_source_review"
    assert MODULE.category("data/raw/source.zip") == "local_originals_keep_private"
    assert MODULE.category("epah_priority_validation.zip") == "archive_review_before_publication"
    assert MODULE.category("data/verification_matrix.pre_indicator_id_migration.csv") == (
        "migration_backup_keep_local"
    )


def test_parse_status_supports_spaces_and_renames():
    raw = b"?? data/indicators/with spaces.csv\x00!! artifacts/\x00"
    assert MODULE.parse_porcelain(raw) == [
        ("??", "data/indicators/with spaces.csv"), ("!!", "artifacts/")
    ]
    renamed = b"R  data/geography/new.geojson\x00data/geography/old.geojson\x00"
    assert MODULE.parse_porcelain(renamed) == [
        ("R ", "data/geography/new.geojson")
    ]


def test_git_inventory_includes_ignored_directories_and_untracked_sources(tmp_path):
    _git("init", "-q", cwd=tmp_path)
    _write(tmp_path, ".gitignore", "artifacts/\ndata/raw/\noutputs/\n")
    _write(tmp_path, "data/raw/source.txt")
    _write(tmp_path, "artifacts/report.pdf")
    _write(tmp_path, "outputs/map.png")
    _write(tmp_path, "data/indicators/new_draft.csv")
    _write(tmp_path, "data/geography/local.geojson")
    _write(tmp_path, "epah_priority_validation.zip")
    result = MODULE.inventory(tmp_path)
    assert result["changes_made"] is False
    assert result["approval_for_publication"] == "not_assessed"
    matching = {x["path"]: x for x in result["entries"]}
    assert matching["data/raw/"]["tracking"] == "ignored"
    assert matching["artifacts/"]["tracking"] == "ignored"
    assert matching["outputs/"]["tracking"] == "ignored"
    assert matching["data/indicators/new_draft.csv"]["tracking"] == "untracked"
    assert matching["data/geography/local.geojson"]["tracking"] == "untracked"
    assert matching["epah_priority_validation.zip"]["tracking"] == "untracked"
    assert (tmp_path / "data/raw/source.txt").read_text() == "test"


def test_modified_tracked_file_is_listed_without_rewriting(tmp_path):
    _git("init", "-q", cwd=tmp_path)
    file = _write(tmp_path, "data/verification_matrix.csv", "first\n")
    _git("add", "data/verification_matrix.csv", cwd=tmp_path)
    file.write_text("second\n", encoding="utf-8")
    result = MODULE.inventory(tmp_path)
    assert any(e["path"] == "data/verification_matrix.csv"
               and e["tracking"] == "tracked_change"
               for e in result["entries"])
    assert file.read_text() == "second\n"


def test_repo_ignore_rules_are_narrow():
    rules = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "data/raw/" in rules
    assert "data/cache/" in rules
    assert "artifacts/" in rules
    assert "data/derived/" not in rules
    assert "data/geography/" not in rules
    assert "data/indicators/" not in rules
    assert "data/reference/" not in rules


def test_non_git_directory_fails_closed(tmp_path):
    with pytest.raises(ValueError, match="Cannot inspect Git"):
        MODULE.inventory(tmp_path)
