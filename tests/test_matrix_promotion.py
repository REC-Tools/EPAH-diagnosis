import csv
from pathlib import Path

from epah_diagnosis.cli import validate_matrix

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "data/reference/verification_matrix_baseline_81.csv"
CURRENT = ROOT / "data/verification_matrix.csv"
CATALOG = ROOT / "config/indicators.json"


def load(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_original_rows_preserved_verbatim():
    previous = load(BASELINE)
    current = load(CURRENT)
    assert len(previous) == 81
    assert len(current) == 243
    assert current[:81] == previous


def test_additive_rows_preserve_status_and_climate_progress():
    current = load(CURRENT)
    additions = current[81:]
    assert len(additions) == 162
    climate = [row for row in additions if row["indicator_id"] == "heating_degree_days"]
    other = [row for row in additions if row["indicator_id"] != "heating_degree_days"]
    assert len(climate) == 27
    assert len(other) == 135
    assert all(row["status"] == "Dato acquisito" and row["value"] for row in climate)
    assert all(row["status"] == "Da verificare" and row["value"] == "" for row in other)
    assert len({(row["municipality"], row["indicator_id"]) for row in current}) == 243


def test_catalog_validates_promoted_matrix_and_legacy_snapshot():
    assert validate_matrix(CURRENT, CATALOG) == (27, 243, [])
    assert validate_matrix(BASELINE) == (27, 81, [])
