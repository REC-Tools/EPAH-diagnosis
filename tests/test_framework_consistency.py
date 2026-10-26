import json
from pathlib import Path

from scripts.check_framework import validate


def fixture(tmp_path: Path):
    (tmp_path / "config").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/indicator_01_example.md").write_text("Example", encoding="utf-8")
    source = {"sources": [{"id": "official_source"}]}
    indicator = {"id": "example", "name": "Example", "role": "context", "dimension": "territorial",
                 "unit": "%", "interpretation_direction": "contextual",
                 "source_ids": ["official_source"], "source_registry_coverage": "registered",
                 "methodological_maturity": "EXPERIMENTAL", "definition": "Example formula",
                 "territorial_level": "municipality", "documentation": "docs/indicator_01_example.md",
                 "caveat": "Not a direct energy poverty measure."}
    (tmp_path / "config/sources.json").write_text(json.dumps(source), encoding="utf-8")
    (tmp_path / "config/indicators.json").write_text(
        json.dumps({"indicators": [indicator]}), encoding="utf-8")
    return indicator


def test_valid_fixture(tmp_path):
    fixture(tmp_path)
    errors, warnings = validate(tmp_path)
    assert not errors
    assert not warnings


def test_unknown_source_fails(tmp_path):
    indicator = fixture(tmp_path)
    indicator["source_ids"] = ["unknown"]
    (tmp_path / "config/indicators.json").write_text(
        json.dumps({"indicators": [indicator]}), encoding="utf-8")
    errors, _ = validate(tmp_path)
    assert any("unknown source" in error for error in errors)


def test_duplicate_indicator_fails(tmp_path):
    indicator = fixture(tmp_path)
    (tmp_path / "config/indicators.json").write_text(
        json.dumps({"indicators": [indicator, indicator]}), encoding="utf-8")
    errors, _ = validate(tmp_path)
    assert any("duplicate id" in error for error in errors)


def test_pending_sources_warn(tmp_path):
    indicator = fixture(tmp_path)
    indicator["source_ids"] = []
    indicator["source_registry_coverage"] = "pending"
    (tmp_path / "config/indicators.json").write_text(
        json.dumps({"indicators": [indicator]}), encoding="utf-8")
    errors, warnings = validate(tmp_path)
    assert not errors
    assert any("registration pending" in warning for warning in warnings)


def test_missing_documentation_fails(tmp_path):
    fixture(tmp_path)
    (tmp_path / "docs/indicator_01_example.md").unlink()
    errors, _ = validate(tmp_path)
    assert any("missing documentation" in error for error in errors)
