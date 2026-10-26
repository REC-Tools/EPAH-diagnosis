import csv

import pytest

from epah_diagnosis.matrix_update import upsert_indicator_rows


FIELDS = ["municipality", "indicator_id", "status", "value", "notes"]


def write(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def read(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_upsert_preserves_other_indicators_and_updates_preinitialised(tmp_path):
    path = tmp_path / "matrix.csv"
    write(path, [
        dict(municipality="Alpette", indicator_id="income", status="Dato validato", value="33", notes="keep"),
        dict(municipality="Alpette", indicator_id="snai", status="Da verificare", value="", notes=""),
    ])
    upsert_indicator_rows(path, "snai", [
        dict(municipality="Alpette", indicator_id="snai", status="Dato validato", value="E", notes="fresh")
    ])
    rows = read(path)
    assert len(rows) == 2
    assert rows[0]["value"] == "33" and rows[0]["notes"] == "keep"
    assert rows[1]["value"] == "E" and rows[1]["status"] == "Dato validato"


def test_new_row_appended_once(tmp_path):
    path = tmp_path / "matrix.csv"
    write(path, [dict(municipality="Alpette", indicator_id="income", status="Dato validato", value="33", notes="")])
    update = dict(municipality="Alpette", indicator_id="snai", status="Dato validato", value="E", notes="")
    upsert_indicator_rows(path, "snai", [update])
    upsert_indicator_rows(path, "snai", [update])
    assert len(read(path)) == 2


def test_duplicate_update_rejected_without_touching_source(tmp_path):
    path = tmp_path / "matrix.csv"
    write(path, [dict(municipality="Alpette", indicator_id="income", status="Dato validato", value="33", notes="")])
    original = path.read_bytes()
    update = dict(municipality="Alpette", indicator_id="snai", status="Dato validato", value="E", notes="")
    with pytest.raises(ValueError, match="Duplicate update"):
        upsert_indicator_rows(path, "snai", [update, update])
    assert path.read_bytes() == original


def test_invalid_source_duplicate_rejected(tmp_path):
    path = tmp_path / "matrix.csv"
    row = dict(municipality="Alpette", indicator_id="snai", status="Da verificare", value="", notes="")
    write(path, [row, row])
    original = path.read_bytes()
    with pytest.raises(ValueError, match="Duplicate keys"):
        upsert_indicator_rows(path, "snai", [{**row, "status": "Dato validato"}])
    assert path.read_bytes() == original
