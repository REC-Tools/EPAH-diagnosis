"""Offline inspection of annual UTCI exports, without scientific approval.

The field is always chosen explicitly. This boundary inventories source bytes;
it never infers units, repairs metadata, or performs municipal aggregation.
"""
from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import math
from pathlib import Path
import tempfile

import numpy as np
from netCDF4 import Dataset, num2date

from .directory_publication import publish_directory
from .provenance import sha256_file

ATTRIBUTES = ("standard_name", "long_name", "units", "calendar", "axis",
              "bounds", "coordinates", "cell_methods", "_FillValue",
              "missing_value", "scale_factor", "add_offset", "valid_range",
              "valid_min", "valid_max", "_Unsigned")


def _json_value(value):
    if isinstance(value, np.ndarray):
        return _json_value(value.tolist())
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, np.generic):
        return _json_value(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return {"nonfinite": str(value)}
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _attributes(variable) -> dict:
    return {key: _json_value(variable.getncattr(key))
            for key in ATTRIBUTES if key in variable.ncattrs()}


def _numbers(variable) -> tuple[np.ndarray, np.ndarray]:
    values = np.ma.asarray(variable[:], dtype=float)
    return np.asarray(values.data), np.ma.getmaskarray(values)


def _coordinate(ds, name: str, kind: str, issues: list[str]) -> dict:
    variable = ds.variables[name]
    values, mask = _numbers(variable)
    record = {"variable": name, "attributes": _attributes(variable),
              "dimensions": list(variable.dimensions)}
    expected = "degrees_north" if kind == "latitude" else "degrees_east"
    if getattr(variable, "units", None) != expected:
        issues.append(f"{kind}_units_not_explicit")
    if values.ndim != 1 or values.size < 2 or mask.any() or not np.isfinite(values).all():
        issues.append(f"{kind}_coordinate_not_supported")
        return record
    delta = np.diff(values)
    monotonic = bool((delta > 0).all() or (delta < 0).all())
    record.update(values=values.tolist(), minimum=float(values.min()),
                  maximum=float(values.max()), strictly_monotonic=monotonic,
                  steps=delta.tolist())
    if not monotonic:
        issues.append(f"{kind}_coordinate_not_monotonic")
    limit = 90 if kind == "latitude" else 360
    if (np.abs(values) > limit).any():
        issues.append(f"{kind}_coordinate_out_of_range")
    return record


def _time(ds, name: str, year: int, issues: list[str]) -> dict:
    variable = ds.variables[name]
    record = {"variable": name, "attributes": _attributes(variable),
              "annual_daily_completeness_verified": False}
    values, mask = _numbers(variable)
    if values.shape != (1,) or mask.any() or not np.isfinite(values).all():
        issues.append("annual_time_coordinate_not_single_finite_value")
        return record
    units = getattr(variable, "units", None)
    cal = getattr(variable, "calendar", "standard")
    record["calendar_used_for_decoding"] = cal
    if "calendar" not in variable.ncattrs():
        issues.append("calendar_not_explicit")
    if not isinstance(units, str) or not units.strip() or not isinstance(cal, str):
        issues.append("time_metadata_not_decodable")
        return record
    if cal not in {"standard", "gregorian", "proleptic_gregorian"}:
        issues.append("calendar_not_supported_for_gregorian_day_range")
    try:
        decoded = num2date(values, units=units, calendar=cal)
        record["decoded_values"] = [str(value) for value in decoded]
        if decoded[0].year != year:
            issues.append("time_reference_year_mismatch")
        bounds_name = getattr(variable, "bounds", None)
        if not bounds_name or bounds_name not in ds.variables:
            issues.append("time_bounds_missing")
        else:
            bounds = ds.variables[bounds_name]
            raw, missing = _numbers(bounds)
            record["bounds_variable"] = bounds_name
            record["bounds_values"] = _json_value(raw)
            if raw.shape != (1, 2) or bounds.dimensions[0] != name or missing.any() or not np.isfinite(raw).all():
                issues.append("time_bounds_not_supported")
            else:
                ends = num2date(raw[0], units=units, calendar=cal)
                record["decoded_bounds"] = [str(value) for value in ends]
                # Record rather than reinterpret inclusive last-hour bounds as
                # a half-open full year. Even exact bounds do not prove 365 inputs.
                record["bounds_are_jan1_to_next_jan1"] = (
                    str(ends[0]) == f"{year:04d}-01-01 00:00:00"
                    and str(ends[1]) == f"{year + 1:04d}-01-01 00:00:00")
                if not record["bounds_are_jan1_to_next_jan1"]:
                    issues.append("time_bounds_require_interpretation")
    except (ValueError, TypeError, OverflowError):
        issues.append("time_metadata_not_decodable")
    return record


def inspect_export(path: Path, *, reference_year: int, field: str | None = None) -> dict:
    """Read one NetCDF, with CF mask/scale; report issues without repairing it."""
    if not 1 <= reference_year <= 9998:
        raise ValueError("reference_year must be between 1 and 9998")
    before = sha256_file(path)
    issues: list[str] = []
    report = {
        "schema": "epah.utci-export-review.v1", "status": "technical_draft_do_not_publish",
        "reference_year": reference_year, "source_sha256": before,
        "scientific_approval": False, "publication_allowed": False,
        "threshold_semantics_verified": False, "municipal_coverage_verified": False,
        "daily_completeness_verified": False, "aggregation_performed": False,
        "issues": issues,
    }
    with Dataset(path, "r") as ds:
        report["dimensions"] = {name: len(dim) for name, dim in ds.dimensions.items()}
        report["global_attributes"] = {
            key: _json_value(ds.getncattr(key))
            for key in ("Conventions", "institution", "frequency") if key in ds.ncattrs()}
        if "history" in ds.ncattrs():
            report["history_sha256"] = hashlib.sha256(str(ds.history).encode("utf-8")).hexdigest()
        report["variables"] = {
            name: {"dimensions": list(var.dimensions), "shape": list(var.shape),
                   "dtype": str(var.dtype), "attributes": _attributes(var)}
            for name, var in ds.variables.items()}
        if ds.groups:
            issues.append("nested_groups_not_supported")
        report["selected_field"] = field
        if field is None:
            issues.append("explicit_field_selection_required")
        elif field not in ds.variables:
            issues.append("selected_field_missing")
        else:
            selected = ds.variables[field]
            if not np.issubdtype(selected.dtype, np.number) or np.issubdtype(selected.dtype, np.complexfloating):
                issues.append("selected_field_not_real_numeric")
            else:
                data, mask = _numbers(selected)
                finite = (~mask) & np.isfinite(data)
                valid = data[finite]
                days = 366 if calendar.isleap(reference_year) else 365
                report["selected_values"] = {
                    "decoding": "netCDF4 automatic CF mask and scale; no unit conversion",
                    "cells": int(data.size), "masked": int(mask.sum()),
                    "unmasked_nonfinite": int(((~mask) & ~np.isfinite(data)).sum()),
                    "finite": int(valid.size), "zero": int((valid == 0).sum()),
                    "minimum": float(valid.min()) if valid.size else None,
                    "maximum": float(valid.max()) if valid.size else None,
                    "gregorian_year_day_limit": days,
                    "outside_day_range": int(((valid < 0) | (valid > days)).sum()),
                    "fractional": int((valid != np.floor(valid)).sum()),
                }
                stats = report["selected_values"]
                if getattr(selected, "units", None) not in {"day", "days", "d"}:
                    issues.append("day_units_not_explicit")
                for key in ("masked", "unmasked_nonfinite", "outside_day_range", "fractional"):
                    if stats[key]:
                        issues.append(f"selected_values_{key}")
                if not valid.size:
                    issues.append("selected_values_no_finite_data")
            names = {}
            for kind, axis in (("time", "T"), ("latitude", "Y"), ("longitude", "X")):
                candidates = [name for name, var in ds.variables.items()
                              if var.dimensions == (name,) and name in selected.dimensions
                              and (getattr(var, "standard_name", None) == kind
                                   or getattr(var, "axis", None) == axis)]
                if len(candidates) != 1:
                    issues.append(f"{kind}_coordinate_missing_or_ambiguous")
                    continue
                name = candidates[0]
                names[kind] = name
                report[kind] = (_time(ds, name, reference_year, issues) if kind == "time"
                                else _coordinate(ds, name, kind, issues))
            if len(names) != 3 or len(selected.dimensions) != 3 or set(selected.dimensions) != set(names.values()):
                issues.append("selected_field_dimensions_not_supported")
    if sha256_file(path) != before:
        raise ValueError("Source changed during inspection; discard the report")
    report["source_unchanged"] = True
    report["inspection_state"] = "issues_found" if issues else "structural_checks_passed_review_still_required"
    return report


def _write_report(report: dict, destination: Path) -> None:
    payload = json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(payload)


def create_example(destination: Path) -> Path:
    """Publish a clearly synthetic annual fixture and its real inspection."""
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Preserve previous output; choose a new destination")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".utci-example-", dir=destination.parent) as tmp:
        stage = Path(tmp) / "example"
        stage.mkdir()
        source = stage / "synthetic.nc"
        with Dataset(source, "w") as ds:
            ds.title = "SOFTWARE TEST FIXTURE, NOT ERA5-HEAT"
            ds.Conventions = "CF-1.6"
            for name, size in (("time", 1), ("bnds", 2), ("lat", 2), ("lon", 2)):
                ds.createDimension(name, size)
            time = ds.createVariable("time", "f8", ("time",))
            time.standard_name, time.units = "time", "days since 2025-01-01"
            time.calendar, time.bounds = "proleptic_gregorian", "time_bnds"
            time[:] = [182]
            ds.createVariable("time_bnds", "f8", ("time", "bnds"))[:] = [[0, 365]]
            for name, standard, units, values in (
                ("lat", "latitude", "degrees_north", [45.5, 45.25]),
                ("lon", "longitude", "degrees_east", [7.25, 7.5])):
                coord = ds.createVariable(name, "f8", (name,))
                coord.standard_name, coord.units = standard, units
                coord[:] = values
            var = ds.createVariable("example_days", "f4", ("time", "lat", "lon"), fill_value=-9999.)
            var.units = "days"
            var[:] = [[[0, 365], [120, -9999]]]
        _write_report(inspect_export(source, reference_year=2025, field="example_days"), stage / "review.json")
        (stage / "README.txt").write_text(
            "SOFTWARE TEST FIXTURE, NOT ERA5-HEAT.\n"
            "One masked cell is intentional: review.json must flag it, not replace it with zero.\n"
            "No threshold, municipal coverage, scientific approval or publication is verified.\n", encoding="utf-8")
        return publish_directory(stage, destination)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="Inventory an original without changing it")
    inspect.add_argument("--file", type=Path, required=True)
    inspect.add_argument("--reference-year", type=int, required=True)
    inspect.add_argument("--field")
    inspect.add_argument("--json-out", type=Path, required=True)
    example = commands.add_parser("example", help="Create a synthetic fixture and review")
    example.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "example":
            create_example(args.out_dir)
            print("Synthetic example created; intentional missingness remains flagged.")
            return 0
        report = inspect_export(args.file, reference_year=args.reference_year, field=args.field)
        _write_report(report, args.json_out)
        print(f"{report['inspection_state']}; {len(report['issues'])} issue(s); no scientific approval.")
        return 2 if report["issues"] else 0
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        # Do not expose private source paths or credentials in command errors.
        print(f"Inspection failed ({type(exc).__name__}); source and previous outputs preserved.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
