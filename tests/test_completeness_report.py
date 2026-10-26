import csv
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("completeness", ROOT / "scripts/report_completeness.py")
module = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(module)


def test_repository_completeness_counts():
    result = module.generate(ROOT / "data/verification_matrix.csv",
                             ROOT / "data/municipalities.csv", ROOT / "config/indicators.json")
    assert result["municipalities"] == 27
    assert result["indicators"] == 9
    assert result["checks"] == 243
    assert sum(result["status_counts"].values()) == 243
    assert len(result["by_municipality"]) == 27
    assert len(result["by_indicator"]) == 9


def test_unknown_municipality_fails(tmp_path):
    source = ROOT / "data/verification_matrix.csv"
    text = source.read_text(encoding="utf-8")
    rows = list(csv.DictReader(text.splitlines()))
    rows[0]["municipality"] = "Unknown Commune"
    modified = tmp_path / "matrix.csv"
    with modified.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError):
        module.generate(modified, ROOT / "data/municipalities.csv",
                        ROOT / "config/indicators.json")
