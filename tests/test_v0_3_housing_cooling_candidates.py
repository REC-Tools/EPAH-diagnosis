"""Synthetic-only regression tests for EPAH v0.3 housing and cooling candidates."""
from __future__ import annotations

import csv
import importlib.util
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(filename: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


housing = load("prepare_v0_3_housing_candidates.py", "housing_candidates")
cooling = load("prepare_cdd_eurostat_2025_v0_3.py", "cooling_candidate")


def test_cdd_eurostat_threshold_is_not_simple_positive_degree_difference():
    D = Decimal
    assert cooling.cdd_day_from_minmax(D("23.9"), D("23.9")) == D("0")
    assert cooling.cdd_day_from_minmax(D("24"), D("24")) == D("3")
    assert cooling.cdd_day_from_minmax(D("22"), D("28")) == D("4")
    assert cooling.cdd_day_from_minmax(D("10"), D("20")) == D("0")
    with pytest.raises(ValueError):
        cooling.cdd_day_from_minmax(D("20"), D("10"))


@pytest.fixture
def codes():
    return {f"001{i:03}": f"Municipality {i}" for i in range(1, 28)}


def make_table(path, registry, indicator):
    spec = housing.SOURCES[indicator]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=housing.FIELDS)
        writer.writeheader()
        for code, name in registry.items():
            for cat in spec["groups"]:
                if indicator == "h05_ape_fg":
                    value = 100 if cat == "total" else (10 if cat != "G" else 10)
                else:
                    value = {"occupied_by_residents": 60, "not_occupied_by_residents": 40, "total": 100}[cat]
                writer.writerow(dict(municipality_code=code, municipality=name,
                                    reference_date="2023-12-31" if indicator != "h05_ape_fg" else "2026-08-31",
                                    data_scope=spec["scope"], group=cat, count=value))


def test_housing_complete_27_and_weighted_share(tmp_path, codes):
    for indicator, share in (("h05_ape_fg", "20.00"), ("dwellings_not_occupied_by_residents", "40.00")):
        source = tmp_path / f"{indicator}.csv"
        make_table(source, codes, indicator)
        values, qa = housing.aggregate(source, codes, indicator)
        assert len(values) == 27
        assert qa["weighted_share_pct"] == share
        assert all(row["status"] == housing.STATUS for row in values)


def test_housing_rejects_wrong_scope_and_missing_categories(tmp_path, codes):
    source = tmp_path / "housing.csv"
    make_table(source, codes, "h05_ape_fg")
    content = source.read_text()
    source.write_text(content.replace("valid_residential_ape", "all_use_ape", 1))
    with pytest.raises(ValueError, match="wrong scope"):
        housing.aggregate(source, codes, "h05_ape_fg")
    make_table(source, codes, "h05_ape_fg")
    lines = source.read_text().splitlines()
    source.write_text("\n".join(lines[:-1]) + "\n")
    with pytest.raises(ValueError, match="incomplete categories"):
        housing.aggregate(source, codes, "h05_ape_fg")


def test_housing_rejects_false_denominator_and_zero(tmp_path, codes):
    source = tmp_path / "housing.csv"
    make_table(source, codes, "dwellings_not_occupied_by_residents")
    lines = source.read_text().splitlines()
    lines[3] = lines[3].replace(",100", ",99")
    source.write_text("\n".join(lines) + "\n")
    with pytest.raises(ValueError, match="unreconciled denominator"):
        housing.aggregate(source, codes, "dwellings_not_occupied_by_residents")


def test_housing_rejects_outdated_year(tmp_path, codes):
    source = tmp_path / "housing.csv"
    make_table(source, codes, "dwellings_not_occupied_by_residents")
    source.write_text(source.read_text().replace("2023-12-31", "2011-12-31"))
    with pytest.raises(ValueError, match="2023-12-31"):
        housing.aggregate(source, codes, "dwellings_not_occupied_by_residents")
