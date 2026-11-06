"""H03 annual NWIOI HDD: deterministic, synthetic-only, no network and no data promotion."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/prepare_hdd_eurostat_2025_v0_3.py"
SPEC = importlib.util.spec_from_file_location("h03_candidate", SCRIPT)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)
CODES = {f"001{i:03}": f"Comune {i}" for i in range(1, 28)}
FIELDS = list(mod.REQUIRED)


def rows_for(year: int = 2025) -> list[dict[str, str]]:
    days = mod.dates_in_year(year)
    return [
        {
            "municipality_code": code,
            "municipality": name,
            "date": day,
            "grid_cell_id": f"CELL{i:03}",
            "grid_latitude": "45.500",
            "grid_longitude": "7.750",
            "tmin_c": "11.0", "tmax_c": "13.0",
        }
        for i, (code, name) in enumerate(CODES.items())
        for day in days
    ]


def csvfile(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def registry_file(path: Path, codes: dict[str, str] = CODES) -> None:
    with path.open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=["municipality", "istat_code"], lineterminator="\n")
        writer.writeheader()
        for code, name in codes.items():
            writer.writerow({"municipality": name, "istat_code": code})


@pytest.fixture
def environment(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    daily = tmp_path / "temperatures.csv"
    registry = tmp_path / "municipalities.csv"
    tn = tmp_path / "tmin.nc"
    tx = tmp_path / "tmax.nc"
    registry_file(registry)
    csvfile(daily, rows_for())
    tn.write_bytes(b"synthetic-not-actually-netcdf-temperature-min")
    tx.write_bytes(b"synthetic-not-actually-netcdf-temperature-max")
    return daily, registry, tn, tx


def test_eurostat_hdd_formula_not_naive_18_degree_base() -> None:
    D = Decimal
    assert mod.hdd_day_from_minmax(D("12"), D("12")) == D("6")
    assert mod.hdd_day_from_minmax(D("15"), D("15")) == D("3")
    assert mod.hdd_day_from_minmax(D("15"), D("16")) == D("0")
    assert mod.hdd_day_from_minmax(D("-5"), D("5")) == D("18")


@pytest.mark.parametrize("left,right", [(-70, 0), (-1, 75), (16, 15)])
def test_physical_temperature_checks(left: int, right: int) -> None:
    with pytest.raises(ValueError, match="Unphysical"):
        mod.hdd_day_from_minmax(Decimal(left), Decimal(right))


@pytest.mark.parametrize("bad", ["", "nan", "NaN", "inf", "1,2", "12.300,5", "-", "--1", "1e2", "--", "#N/A"])
def test_non_numeric_temperatures_rejected(bad: str) -> None:
    with pytest.raises(ValueError, match="invalid decimal"):
        mod.parse_decimal(bad, "synthetic")


def test_calendar_year_and_leap_day() -> None:
    assert len(mod.dates_in_year(2025)) == 365
    assert len(mod.dates_in_year(2024)) == 366
    assert "2024-02-29" in mod.dates_in_year(2024)
    assert "2025-02-29" not in mod.dates_in_year(2025)


def test_annual_hdd_correct_for_all_27(environment: tuple[Path, ...]) -> None:
    daily, registry, *_ = environment
    output, qa = mod.aggregate(daily, mod.read_registry(registry))
    assert len(output) == 27
    assert qa["normalized_daily_rows"] == 27 * 365
    assert qa["unweighted_municipal_mean_c_days"] == "2190.00"
    assert qa["unique_grid_cells"] == 27
    assert all(row["hdd_eurostat_estimated_c_days"] == "2190.00" for row in output)
    assert all(row["temperature_days"] == "365" for row in output)
    assert {row["status"] for row in output} == {mod.STATUS}


def test_leap_year_2024_full_366_rows(tmp_path: Path) -> None:
    registry = tmp_path / "registry.csv"
    daily = tmp_path / "daily.csv"
    registry_file(registry)
    csvfile(daily, rows_for(2024))
    values, qa = mod.aggregate(daily, mod.read_registry(registry), 2024)
    assert qa["normalized_daily_rows"] == 27 * 366
    assert values[0]["hdd_eurostat_estimated_c_days"] == "2196.00"


def test_writes_immutable_qa_and_manifest_hashes(environment: tuple[Path, ...], tmp_path: Path) -> None:
    daily, registry, tn, tx = environment
    folder = tmp_path / "qa"
    args = ["--normalized-daily-csv", str(daily), "--original-tmin-netcdf", str(tn),
            "--original-tmax-netcdf", str(tx), "--registry", str(registry), "--out-dir", str(folder)]
    assert mod.main(args) == 0
    assert len(list(csv.DictReader((folder / "hdd_eurostat_annual_preview.csv").open(encoding="utf-8")))) == 27
    qa = json.loads((folder / "qa.json").read_text(encoding="utf-8"))
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    assert qa["indicator_inventory_id"] == "H03"
    assert qa["source_inventory_id"] == "F08"
    assert qa["qa"]["source_to_municipality_mapping_verified"] is False
    assert qa["qa"]["source_netcdf_extraction_verified"] is False
    assert manifest["scientific_approval"] is False
    assert manifest["canonical_data_modified"] is False
    assert manifest["original_tmin_netcdf_sha256"] == hashlib.sha256(tn.read_bytes()).hexdigest()
    assert manifest["original_tmax_netcdf_sha256"] == hashlib.sha256(tx.read_bytes()).hexdigest()
    assert manifest["outputs_sha256"]["qa.json"] == hashlib.sha256((folder / "qa.json").read_bytes()).hexdigest()
    with pytest.raises(SystemExit):
        mod.main(args)
    assert (folder / "manifest.json").is_file()


def test_hash_mismatch_blocks_without_output(environment: tuple[Path, ...], tmp_path: Path) -> None:
    daily, registry, tn, tx = environment
    output = tmp_path / "out"
    args = ["--normalized-daily-csv", str(daily), "--original-tmin-netcdf", str(tn),
            "--original-tmax-netcdf", str(tx), "--registry", str(registry),
            "--out-dir", str(output), "--expected-tmin-sha256", "0" * 64]
    with pytest.raises(SystemExit):
        mod.main(args)
    assert not output.exists()


def fail_with_change(environment: tuple[Path, ...], mutate, expected: str) -> None:
    daily, registry, *_ = environment
    rows = rows_for()
    mutate(rows)
    csvfile(daily, rows)
    with pytest.raises(ValueError, match=expected):
        mod.aggregate(daily, mod.read_registry(registry))


def test_missing_middle_day_fails(environment: tuple[Path, ...]) -> None:
    fail_with_change(environment, lambda rows: rows.pop(25), "missing 1 calendar dates")


def test_missing_entire_municipality_fails(environment: tuple[Path, ...]) -> None:
    fail_with_change(environment, lambda rows: rows.__setitem__(slice(0, 365), []), "missing 365 calendar dates")


def test_duplicate_day_fails(environment: tuple[Path, ...]) -> None:
    fail_with_change(environment, lambda rows: rows.append(rows[0].copy()), "duplicate municipality/date")


def test_wrong_year_fails(environment: tuple[Path, ...]) -> None:
    fail_with_change(environment, lambda rows: rows[0].update(date="2024-01-01"), "date outside")


def test_invalid_february_29_fails(environment: tuple[Path, ...]) -> None:
    fail_with_change(environment, lambda rows: rows[0].update(date="2025-02-29"), "invalid ISO date")


def test_unexpected_istat_code_fails(environment: tuple[Path, ...]) -> None:
    fail_with_change(environment, lambda rows: rows[0].update(municipality_code="001999"), "unexpected municipality code")


def test_mismatched_istat_name_fails(environment: tuple[Path, ...]) -> None:
    fail_with_change(environment, lambda rows: rows[0].update(municipality="Other Town"), "code/name mismatch")


def test_multiple_cells_for_one_municipality_fails(environment: tuple[Path, ...]) -> None:
    fail_with_change(environment, lambda rows: rows[0].update(grid_cell_id="CELL_OTHER"), "multiple grid cells")


def test_grid_cell_outside_area_fails(environment: tuple[Path, ...]) -> None:
    fail_with_change(environment, lambda rows: rows[0].update(grid_latitude="30"), "outside Piemonte")


def test_tmin_greater_than_tmax_fails(environment: tuple[Path, ...]) -> None:
    fail_with_change(environment, lambda rows: rows[0].update(tmin_c="20"), "Unphysical")


def test_same_cell_conflicting_temperature_fails(environment: tuple[Path, ...]) -> None:
    def mutation(rows):
        for row in rows[365:]:
            row["grid_cell_id"] = "CELL000"
            if row["date"] == "2025-01-01":
                row["tmin_c"] = "10.0"
    fail_with_change(environment, mutation, "contradictory values")


def test_zero_hdd_if_all_days_warm(environment: tuple[Path, ...]) -> None:
    daily, registry, *_ = environment
    rows = rows_for()
    for row in rows:
        row["tmin_c"] = "16.0"
        row["tmax_c"] = "18.0"
    csvfile(daily, rows)
    values, qa = mod.aggregate(daily, mod.read_registry(registry))
    assert values[0]["hdd_eurostat_estimated_c_days"] == "0.00"
    assert qa["hdd_min_c_days"] == "0.00"


def test_shared_grid_cell_allowed_when_daily_series_identical(environment: tuple[Path, ...]) -> None:
    daily, registry, *_ = environment
    rows = rows_for()
    for row in rows[365:730]:
        row["grid_cell_id"] = "CELL000"
    csvfile(daily, rows)
    _, qa = mod.aggregate(daily, mod.read_registry(registry))
    assert qa["unique_grid_cells"] == 26


def test_rounded_calendar_sum_is_only_end_rounding(environment: tuple[Path, ...]) -> None:
    daily, registry, *_ = environment
    rows = rows_for()
    for row in rows:
        row["tmin_c"] = "13.335"
        row["tmax_c"] = "13.335"
    csvfile(daily, rows)
    values, _ = mod.aggregate(daily, mod.read_registry(registry))
    # 365*(18-13.335)=1702.725 -> 1702.73, not 365*4.67.
    assert values[0]["hdd_eurostat_estimated_c_days"] == "1702.73"


def test_malformed_csv_headers_fail(tmp_path: Path) -> None:
    file = tmp_path / "bad.csv"
    file.write_text("municipality_code,date,tmin_c,tmax_c\n001001,2025-01-01,1,2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unique headers"):
        mod.aggregate(file, CODES)


def test_registry_size_and_names_rejected(tmp_path: Path) -> None:
    file = tmp_path / "registry.csv"
    registry_file(file, {"001001": "One"})
    with pytest.raises(ValueError, match="Expected exactly 27"):
        mod.read_registry(file)


def test_two_original_files_must_be_different(environment: tuple[Path, ...], tmp_path: Path) -> None:
    daily, registry, tn, _ = environment
    with pytest.raises(SystemExit):
        mod.main(["--normalized-daily-csv", str(daily), "--original-tmin-netcdf", str(tn),
                  "--original-tmax-netcdf", str(tn), "--registry", str(registry),
                  "--out-dir", str(tmp_path / "output")])
    assert not (tmp_path / "output").exists()
