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


def test_legacy_population_and_income_rows_preserved_verbatim():
    previous = load(BASELINE)
    current = load(CURRENT)
    assert len(previous) == 81
    assert len(current) == 243
    assert [(r["municipality"], r["indicator_id"]) for r in current[:81]] == [
        (r["municipality"], r["indicator_id"]) for r in previous
    ]
    unchanged = [
        (old, new) for old, new in zip(previous, current[:81])
        if old["indicator_id"] != "old_building_stock"
    ]
    assert len(unchanged) == 54
    assert all(old == new for old, new in unchanged)
    promoted_buildings = [
        (old, new) for old, new in zip(previous, current[:81])
        if old["indicator_id"] == "old_building_stock"
    ]
    assert len(promoted_buildings) == 27
    assert all(old["status"] == "Da verificare" and not old["value"]
               and new["status"] == "Dato validato" and new["value"]
               for old, new in promoted_buildings)


def test_additive_rows_preserve_validated_priority_audit_and_other_blockers():
    current = load(CURRENT)
    additions = current[81:]
    assert len(additions) == 162
    promoted = {"heating_degree_days", "mean_altitude", "snai_classification"}
    selected = [row for row in additions if row["indicator_id"] in promoted]
    remaining = [row for row in additions if row["indicator_id"] not in promoted]
    assert len(selected) == 81
    assert len(remaining) == 81
    assert all(row["status"] == "Dato validato" and row["value"] for row in selected)
    assert all(row["status"] == "Da verificare" and row["value"] == "" for row in remaining)
    assert len({(row["municipality"], row["indicator_id"]) for row in current}) == 243
    assert sum(row["status"] == "Dato validato" for row in current) == 162


def test_catalog_validates_promoted_matrix_and_legacy_snapshot():
    assert validate_matrix(CURRENT, CATALOG) == (27, 243, [])
    assert validate_matrix(BASELINE) == (27, 81, [])
