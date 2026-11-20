"""Synthetic regressions for source review, not scientific validation."""
import json
from pathlib import Path

from netCDF4 import Dataset
import numpy as np
import pytest

from epah_diagnosis import utci_export_review_v0_5 as review
from epah_diagnosis.provenance import sha256_file


@pytest.fixture
def source(tmp_path):
    folder = review.create_example(tmp_path / "fixture")
    path = folder / "synthetic.nc"
    with Dataset(path, "r+") as ds:
        ds.variables["example_days"][:] = [[[0, 365], [120, 10]]]
    return path


def inspect(path, **kwargs):
    return review.inspect_export(path, reference_year=kwargs.pop("reference_year", 2025),
                                 field=kwargs.pop("field", "example_days"), **kwargs)


def test_annual_coordinate_is_not_daily_series_or_approval(source):
    before = source.read_bytes()
    result = inspect(source)
    assert result["issues"] == []
    assert result["time"]["decoded_bounds"] == ["2025-01-01 00:00:00", "2026-01-01 00:00:00"]
    assert result["selected_values"]["cells"] == 4
    assert result["selected_values"]["zero"] == 1
    for key in ("scientific_approval", "publication_allowed", "threshold_semantics_verified",
                "municipal_coverage_verified", "daily_completeness_verified", "aggregation_performed"):
        assert result[key] is False
    assert source.read_bytes() == before
    assert result["source_sha256"] == sha256_file(source)
    assert str(source) not in json.dumps(result)


def test_inventory_does_not_select_field_from_name(source):
    result = inspect(source, field=None)
    assert result["selected_field"] is None
    assert "explicit_field_selection_required" in result["issues"]
    assert "selected_values" not in result
    assert "example_days" in result["variables"]


def test_actual_export_missing_units_and_last_hour_bounds_remain_unresolved(source):
    with Dataset(source, "r+") as ds:
        var = ds.variables["example_days"]
        var.delncattr("units")
        time = ds.variables["time"]
        time.units = "hours since 2025-1-1 00:00:00"
        time[:] = [4379.5]
        ds.variables["time_bnds"][:] = [[0, 8759]]
        ds.frequency = "day"  # This global attribute does not prove daily completeness.
    result = inspect(source)
    assert result["issues"] == ["day_units_not_explicit", "time_bounds_require_interpretation"]
    assert result["time"]["decoded_bounds"][1] == "2025-12-31 23:00:00"
    assert result["daily_completeness_verified"] is False
    assert "units" not in result["variables"]["example_days"]["attributes"]


def test_mask_nan_zero_fraction_and_range_are_distinct(source):
    with Dataset(source, "r+") as ds:
        ds.variables["example_days"][:] = [[[0, -9999], [np.nan, 365.5]]]
    result = inspect(source)
    values = result["selected_values"]
    assert (values["zero"], values["masked"], values["unmasked_nonfinite"],
            values["outside_day_range"], values["fractional"]) == (1, 1, 1, 1, 1)
    json.dumps(result, allow_nan=False)


def test_all_missing_has_no_numeric_extrema_and_nan_attribute_is_json_safe(source):
    with Dataset(source, "r+") as ds:
        var = ds.createVariable("empty", "f4", ("time", "lat", "lon"), fill_value=np.nan)
        var.units = "days"
        var[:] = np.full((1, 2, 2), np.nan)
    result = inspect(source, field="empty")
    assert result["selected_values"]["finite"] == 0
    assert result["selected_values"]["minimum"] is None
    assert result["selected_values"]["maximum"] is None
    assert "selected_values_no_finite_data" in result["issues"]
    assert result["variables"]["empty"]["attributes"]["_FillValue"] == {"nonfinite": "nan"}
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("units", ["K", "1", "hours", ""])
def test_no_unit_inference_or_temperature_conversion(source, units):
    with Dataset(source, "r+") as ds:
        ds.variables["example_days"].units = units
    result = inspect(source)
    assert "day_units_not_explicit" in result["issues"]
    assert result["selected_values"]["maximum"] == 365


def test_cf_packing_is_declared_and_not_double_scaled(source):
    with Dataset(source, "r+") as ds:
        var = ds.createVariable("packed", "i2", ("time", "lat", "lon"), fill_value=-9999)
        var.units, var.scale_factor, var.add_offset = "days", 0.5, 0.
        var[:] = [[[0, 1.5], [10, 365]]]
    result = inspect(source, field="packed")
    assert result["selected_values"]["maximum"] == 365
    assert result["selected_values"]["fractional"] == 1
    assert result["variables"]["packed"]["attributes"]["scale_factor"] == 0.5


@pytest.mark.parametrize("cal", ["360_day", "noleap"])
def test_non_gregorian_not_silently_approved(source, cal):
    with Dataset(source, "r+") as ds:
        ds.variables["time"].calendar = cal
    assert "calendar_not_supported_for_gregorian_day_range" in inspect(source)["issues"]


def test_missing_calendar_year_mismatch_and_leap_limit(source):
    with Dataset(source, "r+") as ds:
        ds.variables["time"].delncattr("calendar")
        ds.variables["example_days"][:] = [[[366, 0], [0, 0]]]
    result = inspect(source, reference_year=2024)
    assert "calendar_not_explicit" in result["issues"]
    assert "time_reference_year_mismatch" in result["issues"]
    assert result["selected_values"]["outside_day_range"] == 0


@pytest.mark.parametrize("change,issue", [
    ("duplicate", "latitude_coordinate_not_monotonic"),
    ("missing_units", "latitude_units_not_explicit"),
    ("masked", "latitude_coordinate_not_supported"),
    ("bounds_missing", "time_bounds_missing"),
    ("bounds_scalar", "time_bounds_not_supported"),
    ("bad_time_units", "time_metadata_not_decodable"),
    ("missing_time_units", "time_metadata_not_decodable"),
])
def test_coordinate_failures_are_explicit(source, change, issue):
    with Dataset(source, "r+") as ds:
        if change == "duplicate":
            ds.variables["lat"][:] = [45.5, 45.5]
        elif change == "missing_units":
            ds.variables["lat"].delncattr("units")
        elif change == "masked":
            ds.variables["lat"][:] = [np.nan, 45.5]
        elif change == "bounds_missing":
            ds.variables["time"].bounds = "absent"
        elif change == "bounds_scalar":
            ds.createVariable("scalar", "f8")[:] = 0
            ds.variables["time"].bounds = "scalar"
        elif change == "missing_time_units":
            ds.variables["time"].delncattr("units")
        else:
            ds.variables["time"].units = "days"
    assert issue in inspect(source)["issues"]


def test_missing_field_and_extra_dimension_are_not_count_fields(source):
    assert "selected_field_missing" in inspect(source, field="missing")["issues"]
    assert "selected_field_dimensions_not_supported" in inspect(source, field="lat")["issues"]


def test_example_is_replayable_and_never_overwritten(tmp_path):
    output = tmp_path / "fresh-parent" / "example"
    review.create_example(output)
    saved = json.loads((output / "review.json").read_text())
    assert saved == inspect(output / "synthetic.nc")
    assert saved["issues"] == ["selected_values_masked"]
    assert "NOT ERA5-HEAT" in (output / "README.txt").read_text()
    before = (output / "review.json").read_bytes()
    with pytest.raises(FileExistsError):
        review.create_example(output)
    assert (output / "review.json").read_bytes() == before


def test_cli_exit_states_and_exclusive_destination(source, tmp_path, capsys):
    output = tmp_path / "fresh-parent" / "review.json"
    args = ["inspect", "--file", str(source), "--reference-year", "2025", "--json-out", str(output)]
    assert review.main(args) == 2  # Inventory requires explicit field review.
    first = output.read_bytes()
    assert review.main(args) == 1
    assert output.read_bytes() == first
    args[-1] = str(tmp_path / "selected.json")
    assert review.main(args + ["--field", "example_days"]) == 0
    bad = tmp_path / "bad.nc"
    bad.write_bytes(b"not a netcdf")
    assert review.main(["inspect", "--file", str(bad), "--reference-year", "2025",
                        "--json-out", str(tmp_path / "bad.json")]) == 1
    assert not (tmp_path / "bad.json").exists()
    source_before = source.read_bytes()
    args[-1] = str(source)
    assert review.main(args) == 1
    assert source.read_bytes() == source_before
    assert str(tmp_path) not in capsys.readouterr().out


def test_source_change_during_read_rejects_report(source, monkeypatch):
    real = review.sha256_file
    count = 0

    def changing(path):
        nonlocal count
        count += 1
        return real(path) if count == 1 else "changed"

    monkeypatch.setattr(review, "sha256_file", changing)
    with pytest.raises(ValueError, match="Source changed"):
        inspect(source)
