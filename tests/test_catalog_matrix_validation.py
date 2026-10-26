import csv
import json

from epah_diagnosis.cli import MATRIX_FIELDS, validate_matrix, write_matrix, build_matrix


def test_catalog_accepts_expanded_matrix(tmp_path):
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps({"indicators": [{"id": "population_65_plus"},
        {"id": "income_vulnerability"}, {"id": "old_building_stock"},
        {"id": "rail_accessibility"}]}), encoding="utf-8")
    rows = build_matrix(["A", "B"])
    for municipality in ["A", "B"]:
        row = {key: "" for key in MATRIX_FIELDS}
        row.update(municipality=municipality, indicator_id="rail_accessibility",
                   status="Da verificare")
        rows.append(row)
    path = tmp_path / "matrix.csv"
    write_matrix(rows, path)
    assert validate_matrix(path, catalog) == (2, 8, [])
    assert validate_matrix(path)[2]  # Legacy 3-indicator mode remains strict.


def test_missing_combination_is_rejected_even_with_equal_row_count(tmp_path):
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps({"indicators": [{"id": "population_65_plus"},
        {"id": "income_vulnerability"}, {"id": "old_building_stock"}]}))
    rows = build_matrix(["A", "B"])
    rows[-1] = {**rows[-1], "indicator_id": "population_65_plus"}
    file = tmp_path / "matrix.csv"
    write_matrix(rows, file)
    _, _, errors = validate_matrix(file, catalog)
    assert any("duplicate" in e for e in errors)
    assert any("missing" in e for e in errors)
