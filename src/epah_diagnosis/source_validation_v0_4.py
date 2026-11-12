"""Independent technical replay of H03/H04 daily climate and H05 normalized APE.

Offline, stdlib-only. Does NOT import the H03/H04/H05 production builders.
Original NetCDF / APE exports are checked by SHA-256 but their decoding and
source-to-municipality / residential mapping is not independently re-performed.
Never grants scientific approval, changes canonical data, or authorizes release.
"""
from __future__ import annotations

import csv
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, ROUND_HALF_EVEN
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import unicodedata

STATUS = "technical_draft_do_not_publish"
CLIMATE_FILES = ("daily", "h03_dir", "h04_dir", "tmin", "tmax", "mask", "boundaries", "extraction_qa")
H05_FILES = ("normalized", "original", "h05_dir")
DAILY_FIELDS = ("municipality_code", "municipality", "date", "grid_cell_id",
                "grid_latitude", "grid_longitude", "tmin_c", "tmax_c")
H05_FIELDS = ("municipality_code", "municipality", "reference_date", "data_scope", "group", "count")
APE_CLASSES = ("A4", "A3", "A2", "A1", "B", "C", "D", "E", "F", "G")
SHA_KEYS = {
    "daily": "normalized_daily_csv_sha256",
    "tmin": "original_tmin_netcdf_sha256",
    "tmax": "original_tmax_netcdf_sha256",
}
HEX = re.compile(r"[0-9a-f]{64}\Z")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _require_sha(actual: str, expected: object, label: str) -> None:
    if not isinstance(expected, str) or not HEX.fullmatch(expected) or actual != expected:
        raise ValueError(f"{label}: missing or mismatching SHA-256")


def _read_csv(path: Path, fields: tuple[str, ...]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        headings = reader.fieldnames or []
        if len(headings) != len(set(headings)) or not set(fields) <= set(headings):
            raise ValueError(f"{path.name}: missing/duplicate CSV headers")
        rows = list(reader)
    if not rows or any(None in row or any(row.get(k) is None for k in fields) for row in rows):
        raise ValueError(f"{path.name}: empty or malformed CSV")
    return rows


def _json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name}: expected JSON object")
    return value


def _normal(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in normalized if c.isalnum() and not unicodedata.combining(c))


def _registry(path: Path) -> dict[str, str]:
    rows = _read_csv(path, ("municipality", "istat_code"))
    result = {}
    names = set()
    for row in rows:
        code, name = row["istat_code"], row["municipality"]
        if (not re.fullmatch(r"[0-9]{6}", code) or not name.strip()
                or code in result or _normal(name) in names):
            raise ValueError("Invalid or duplicate ISTAT registry code/name")
        result[code] = name
        names.add(_normal(name))
    if len(result) != 27:
        raise ValueError("Exactly 27 municipalities required")
    return result


def _number(value: str, label: str, *, integer: bool = False) -> Decimal:
    if (not isinstance(value, str) or value != value.strip()
            or not re.fullmatch(r"[0-9]+" if integer else r"-?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)", value)):
        raise ValueError(f"{label}: invalid decimal or missing value")
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{label}: malformed decimal") from exc
    if not result.is_finite() or integer and result < 0:
        raise ValueError(f"{label}: invalid numerical range")
    return result


def _receipt(directory: Path, filename: str, registry_path: Path, *, indicator: str) -> tuple[list[dict], dict]:
    manifest = _json(directory / "manifest.json")
    qa_file = directory / "qa.json"
    qa = _json(qa_file)
    if (manifest.get("status") != STATUS or qa.get("status") != STATUS
            or manifest.get("scientific_approval") is not False
            or manifest.get("canonical_data_modified") is not False):
        raise ValueError(f"{indicator}: preview is not a technical-only, unapproved source")
    _require_sha(digest(registry_path), manifest.get("municipality_registry_sha256"),
                f"{indicator} municipality registry")
    for name in (filename, "qa.json"):
        _require_sha(digest(directory / name), manifest.get("outputs_sha256", {}).get(name),
                    f"{indicator}/{name}")
    if indicator == "H03":
        if (qa.get("indicator_inventory_id") != "H03"
                or manifest.get("raw_netcdf_temporal_and_spatial_consistency_verified") is not False):
            raise ValueError("H03: expected technically unreviewed extraction")
    elif indicator == "H04":
        if (qa.get("epah_inventory_id") != "H04"
                or manifest.get("indicator_id") != "H04"
                or manifest.get("source_to_municipality_mapping_verified") is not False):
            raise ValueError("H04: expected unreviewed grid-cell mapping")
    elif indicator == "H05":
        if (manifest.get("indicator_id") != "h05_ape_fg"
                or manifest.get("source_mapping_verified") is not False
                or qa.get("qa", {}).get("source_mapping_verified") is not False
                or qa.get("qa", {}).get("residential_filter_verified") is not False):
            raise ValueError("H05: residential source mapping has not been certified")
    return _read_csv(directory / filename, ("municipality_code", "municipality", "status")), manifest


def _preview_map(rows: list[dict], registry: dict[str, str], kind: str) -> dict[str, dict]:
    result = {}
    for row in rows:
        code = row["municipality_code"]
        if (code not in registry or code in result or _normal(row["municipality"]) != _normal(registry[code])
                or row["status"] != STATUS):
            raise ValueError(f"{kind}: duplicate, unknown or improperly labelled municipality")
        result[code] = row
    if set(result) != set(registry):
        raise ValueError(f"{kind}: not exactly 27 municipality observations")
    return result


def validate_climate(paths: dict[str, Path], registry_path: Path) -> dict:
    """Independent daily annual totals; no production aggregation imports."""
    registry = _registry(registry_path)
    rows03, man03 = _receipt(paths["h03_dir"], "hdd_eurostat_annual_preview.csv", registry_path, indicator="H03")
    rows04, man04 = _receipt(paths["h04_dir"], "cdd_eurostat_annual_preview.csv", registry_path, indicator="H04")
    preview03 = _preview_map(rows03, registry, "H03")
    preview04 = _preview_map(rows04, registry, "H04")
    for key, manifest_key in SHA_KEYS.items():
        actual = digest(paths[key])
        _require_sha(actual, man03.get(manifest_key), f"H03 {key}")
        _require_sha(actual, man04.get(manifest_key), f"H04 {key}")

    extraction = _json(paths["extraction_qa"])
    raw_receipts = extraction.get("input_hashes_sha256", {})
    if (extraction.get("status") != STATUS or extraction.get("candidate_id") != "H03"
            or extraction.get("source_netcdf_temporal_grid_and_temperature_checks_passed") is not True
            or extraction.get("technical_geospatial_cell_selection_completed") is not True
            or extraction.get("masked_cells_only") is not True
            or extraction.get("scientific_approval") is not False):
        raise ValueError("H03 extractor QA missing technical NetCDF / masked-cell checks")
    for path_key, receipt_key in (
        ("daily", "normalized_daily_csv"), ("tmin", "tmin_netcdf"),
        ("tmax", "tmax_netcdf"), ("mask", "mask_netcdf"),
        ("boundaries", "boundaries_geojson"),
    ):
        _require_sha(digest(paths[path_key]), raw_receipts.get(receipt_key),
                    f"Extractor {path_key}")
    _require_sha(digest(registry_path), raw_receipts.get("municipality_registry"), "Extractor registry")
    _require_sha(digest(paths["h03_dir"] / "hdd_eurostat_annual_preview.csv"),
                extraction.get("annual_hdd_preview_sha256"), "Extractor H03 output")
    if extraction.get("reference_year") != 2025:
        raise ValueError("Extractor year must be 2025")

    dates = {(date(2025, 1, 1) + timedelta(days=i)).isoformat() for i in range(365)}
    daily = _read_csv(paths["daily"], DAILY_FIELDS)
    if len(daily) != 27 * 365 or extraction.get("daily_observations") != len(daily):
        raise ValueError("Expected exactly 27 x 365 daily climate records")
    seen, cell_by_code, shared = set(), {}, {}
    totals = {code: {"H03": Decimal(0), "H04": Decimal(0)} for code in registry}
    for row in daily:
        code, day = row["municipality_code"], row["date"]
        if (code not in registry or _normal(row["municipality"]) != _normal(registry[code])
                or day not in dates or (code, day) in seen):
            raise ValueError("Invalid, duplicated or out-of-calendar daily observation")
        seen.add((code, day))
        cell = row["grid_cell_id"]
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", cell):
            raise ValueError("Invalid NWIOI cell identifier")
        lat = _number(row["grid_latitude"], "latitude")
        lon = _number(row["grid_longitude"], "longitude")
        if not Decimal(43) <= lat <= Decimal("47.5") or not Decimal(6) <= lon <= Decimal(11):
            raise ValueError("NWIOI grid cell outside Piemonte study envelope")
        location = (cell, lat, lon)
        if code in cell_by_code and cell_by_code[code] != location:
            raise ValueError("A municipality changed grid cells during the year")
        cell_by_code[code] = location
        tmin, tmax = _number(row["tmin_c"], "tmin"), _number(row["tmax_c"], "tmax")
        if not Decimal(-65) <= tmin <= tmax <= Decimal(65):
            raise ValueError("Invalid or inverted Tmin/Tmax")
        observation = (lat, lon, tmin, tmax)
        if (cell, day) in shared and shared[cell, day] != observation:
            raise ValueError("Shared grid-cell temperatures contradict each other")
        shared[cell, day] = observation
        mean = (tmin + tmax) / Decimal(2)
        totals[code]["H03"] += Decimal(18) - mean if mean <= Decimal(15) else Decimal(0)
        totals[code]["H04"] += mean - Decimal(21) if mean >= Decimal(24) else Decimal(0)
    if len(seen) != 27 * len(dates):
        raise ValueError("Missing municipal dates in full climate year")
    for code in registry:
        cell, lat, lon = cell_by_code[code]
        for indicator, obs, key, rounding in (
            ("H03", preview03[code], "hdd_eurostat_estimated_c_days", ROUND_HALF_UP),
            ("H04", preview04[code], "cdd_eurostat_estimated_c_days", ROUND_HALF_EVEN),
        ):
            if (obs.get("reference_year") != "2025" or obs.get("temperature_days") != "365"
                    or obs.get("grid_cell_id") != cell
                    or _number(obs.get("grid_latitude"), f"{indicator} grid latitude") != lat
                    or _number(obs.get("grid_longitude"), f"{indicator} grid longitude") != lon):
                raise ValueError(f"{indicator}/{code}: calendar, grid or 365-day mismatch")
            recomputed = totals[code][indicator].quantize(Decimal("0.01"), rounding=rounding)
            observed = _number(obs.get(key), f"{indicator} annual preview")
            if observed != recomputed:
                raise ValueError(f"{indicator}/{code}: independent annual reproduction mismatch")
    return {
        "status": "technical_replay_passed_review_pending",
        "h03_h04_recomputed_27_by_365": True,
        "municipalities": 27, "daily_rows": len(daily), "year": 2025,
        "unique_grid_cells": len(set(cell_by_code.values())),
        "source_sha256_verified": True,
        "extraction_qa_verified": True,
        "independent_netcdf_decoding": False,
        "grid_cell_representativeness_approved": False,
        "scientific_approval": False, "publication_allowed": False,
        "limitations": [
            "NetCDF SHA digests and extraction QA verified, but this audit does not reopen NetCDF tensors.",
            "One grid cell per municipality, not an areal or population-weighted climate value.",
            "Altitude representativeness and original remote-source identity require review.",
        ],
    }


def validate_h05(paths: dict[str, Path], registry_path: Path) -> dict:
    """Independent normalized EPC class aggregation; original export mapping pending."""
    registry = _registry(registry_path)
    rows, manifest = _receipt(paths["h05_dir"], "h05_ape_fg_preview.csv", registry_path, indicator="H05")
    preview = _preview_map(rows, registry, "H05")
    _require_sha(digest(paths["original"]), manifest.get("original_export_sha256"), "H05 original")
    _require_sha(digest(paths["normalized"]), manifest.get("normalized_csv_sha256"), "H05 normalized")
    source = _read_csv(paths["normalized"], H05_FIELDS)
    if len(source) != 27 * (len(APE_CLASSES) + 1):
        raise ValueError("H05 normalized class inventory must contain exactly 27 x 11 rows")
    category, reference_dates = {}, set()
    for row in source:
        code, name = row["municipality_code"], row["municipality"]
        if code not in registry or _normal(name) != _normal(registry[code]):
            raise ValueError("H05 normalized municipality mismatch")
        when = row["reference_date"]
        try:
            parsed = date.fromisoformat(when)
        except ValueError as exc:
            raise ValueError("H05 invalid reference date") from exc
        if when != parsed.isoformat() or row["data_scope"] != "valid_residential_ape":
            raise ValueError("H05 wrong date format or residential scope")
        reference_dates.add(when)
        group = row["group"]
        if group not in (*APE_CLASSES, "total") or group in category.setdefault(code, {}):
            raise ValueError("H05 duplicated or unknown energy class")
        category[code][group] = int(_number(row["count"], "H05 class count", integer=True))
    if len(reference_dates) != 1 or set(category) != set(registry):
        raise ValueError("H05 mixed dates or incomplete municipalities")
    for code, parts in category.items():
        if set(parts) != set((*APE_CLASSES, "total")):
            raise ValueError("H05 incomplete certificate energy classes")
        denom = parts["total"]
        numerator = parts["F"] + parts["G"]
        if denom <= 0 or denom != sum(parts[c] for c in APE_CLASSES):
            raise ValueError("H05 certificate total unreconciled")
        item = preview[code]
        if (item.get("reference_date") != next(iter(reference_dates))
                or item.get("indicator_id") != "h05_ape_fg"
                or item.get("numerator") != str(numerator)
                or item.get("denominator") != str(denom)):
            raise ValueError(f"H05/{code}: independent certificate counts disagree")
        pct = Decimal(100) * Decimal(numerator) / Decimal(denom)
        if abs(_number(item.get("value_pct"), f"H05 {code} percentage") - pct) > Decimal("0.005"):
            raise ValueError(f"H05/{code}: certificate percentage inconsistent")
    return {
        "status": "technical_replay_passed_review_pending",
        "municipalities": 27, "class_records": len(source),
        "reference_date": next(iter(reference_dates)),
        "source_sha256_verified": True, "normalized_ape_classes_recomputed": True,
        "independent_original_residential_filter": False,
        "representative_of_housing_stock": False,
        "scientific_approval": False, "publication_allowed": False,
        "limitations": [
            "Original export hash verified; no independent original-to-normalized filter or deduplication audit.",
            "Only valid residential EPC certificates, not all dwellings.",
            "Unknown selection bias and time coverage require human methodological review.",
        ],
    }


def assess(registry_path: Path, *, climate: dict[str, Path] | None = None,
           h05: dict[str, Path] | None = None) -> dict:
    """Return separate evidence states; missing evidence never becomes a pass."""
    registry = _registry(registry_path)
    result = {
        "schema_version": "0.4-technical-source-replay",
        "status": STATUS, "publication_allowed": False, "scientific_approval": False,
        "registry_sha256": digest(registry_path), "registered_municipalities": len(registry),
        "climate_h03_h04": {"status": "blocked_missing_originals"},
        "residential_h05": {"status": "blocked_missing_originals"},
        "completely_validated_for_territorial_publication": False,
    }
    if climate is not None and all(k in climate and climate[k].is_file() for k in CLIMATE_FILES):
        result["climate_h03_h04"] = validate_climate(climate, registry_path)
    if h05 is not None and all(k in h05 and h05[k].is_file() for k in H05_FILES):
        result["residential_h05"] = validate_h05(h05, registry_path)
    return result


def publish_report(out_dir: Path, report: dict) -> Path:
    """Preserve prior QA evidence; staged, immutable local technical report."""
    if out_dir.exists():
        raise FileExistsError("Choose a NEW QA output directory")
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".epah-v04-audit-", dir=out_dir.parent) as parent:
        stage = Path(parent) / "audit"
        stage.mkdir()
        (stage / "validation.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
            encoding="utf-8")
        (stage / "manifest.json").write_text(
            json.dumps({
                "status": STATUS, "publication_allowed": False,
                "outputs_sha256": {"validation.json": digest(stage / "validation.json")},
            }, indent=2) + "\n", encoding="utf-8")
        if out_dir.exists():
            raise FileExistsError("QA report appeared concurrently")
        os.replace(stage, out_dir)
    return out_dir
