import csv
import json
import sys

import pytest

from epah_diagnosis.cli import (
    build_matrix,
    main,
    read_municipalities,
    read_municipality_codes,
    validate_matrix,
    write_matrix,
)


def test_canonical_registry_has_27_unique_six_digit_codes():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    registry = root / "data" / "municipalities.csv"
    mapping = read_municipality_codes(registry)
    assert len(mapping) == 27
    assert len(set(mapping.values())) == 27
    assert all(code.startswith("001") for code in mapping.values())
    assert read_municipalities(registry) == list(mapping)


@pytest.mark.parametrize("content", [
    "municipality,istat_code\nA,001001\nB,001001\n",
    "municipality,istat_code\nA,1001\n",
    "municipality,istat_code\nA,\n",
    "municipality,istat_code\nA,001001\nA,001002\n",
])
def test_registry_rejects_duplicate_and_invalid_codes(tmp_path, content):
    path = tmp_path / "municipalities.csv"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        read_municipality_codes(path)


def test_legacy_names_only_registry_remains_compatible(tmp_path):
    path = tmp_path / "municipalities.csv"
    path.write_text("municipality\nA\nB\n", encoding="utf-8")
    assert read_municipalities(path) == ["A", "B"]


def test_catalog_initialized_matrix_is_27_by_9(tmp_path):
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    names = read_municipalities(root / "data" / "municipalities.csv")
    catalog = root / "config" / "indicators.json"
    rows = build_matrix(names, catalog)
    assert len(rows) == 243
    assert all(row["status"] == "Da verificare" for row in rows)
    file = tmp_path / "new_matrix.csv"
    write_matrix(rows, file)
    assert validate_matrix(file, catalog) == (27, 243, [])


def test_cli_init_matrix_rejects_existing_output_without_modifying(tmp_path, monkeypatch):
    path = tmp_path / "existing.csv"
    path.write_text("keep-me-intact", encoding="utf-8")
    names = tmp_path / "municipalities.csv"
    names.write_text("municipality\nA\nB\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [
        "epah", "init-matrix", "--municipalities", str(names), "--output", str(path)
    ])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
    assert path.read_text(encoding="utf-8") == "keep-me-intact"


def test_cli_default_initialization_uses_full_catalog(tmp_path, monkeypatch):
    names = tmp_path / "municipalities.csv"
    names.write_text("municipality\nA\nB\n", encoding="utf-8")
    output = tmp_path / "new.csv"
    monkeypatch.setattr(sys, "argv", [
        "epah", "init-matrix", "--municipalities", str(names), "--output", str(output)
    ])
    main()
    with output.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 18
    assert len({r["indicator_id"] for r in rows}) == 9
