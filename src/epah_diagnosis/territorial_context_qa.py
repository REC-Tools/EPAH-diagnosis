"""Fail-closed preparation and reviewed promotion of altitude and SNAI proxies.

Both sources are official workbooks. File format checks, coverage and hashes do
not authenticate origin, licenses, historical geography or human review.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from collections import Counter
from datetime import date
from pathlib import Path
from statistics import mean, median
from urllib.parse import urlsplit

from epah_diagnosis.altitude import ALTITUDE_XLSX_URL, normalize_text, parse_altitude_workbook
from epah_diagnosis.cli import read_municipality_codes
from epah_diagnosis.matrix_update import upsert_indicator_rows
from epah_diagnosis.snai import CLASS_LABELS, SNAI_2020_URL, parse_snai_workbook

CONFIG = {
    "mean_altitude": {
        "reference_year": "2021",
        "source_id": "istat_altitude_2021",
        "source_url": ALTITUDE_XLSX_URL,
        "unit": "m s.l.m.",
        "output": "mean_altitude_2021.csv",
        "summary": "mean_altitude_summary_2021.csv",
    },
    "snai_classification": {
        "reference_year": "2020",
        "source_id": "snai_areas_2020",
        "source_url": SNAI_2020_URL,
        "unit": "classe A-F",
        "output": "snai_classification_2020.csv",
        "summary": "snai_classification_summary_2020.csv",
    },
}
DATA_COLUMNS = {
    "mean_altitude": [
        "municipality", "municipality_code", "year", "mean_altitude_m",
        "min_altitude_m", "max_altitude_m", "source_url", "limitations",
    ],
    "snai_classification": [
        "municipality", "municipality_code", "year", "snai_class",
        "snai_label", "source_url", "limitations",
    ],
}
SUMMARY_COLUMNS = {
    "mean_altitude": [
        "territory", "municipality_count", "mean_of_municipal_mean_altitude_m",
        "median_municipal_mean_altitude_m", "min_municipal_mean_altitude_m",
        "max_municipal_mean_altitude_m", "method",
    ],
    "snai_classification": [
        "territory", "municipality_count", "class_A", "class_B", "class_C",
        "class_D", "class_E", "class_F", "inner_area_municipalities_D_E_F", "method",
    ],
}


def csv_bytes(fields: list[str], rows: list[dict]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def _hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def prepare(indicator_id: str, source_bytes: bytes, registry: Path,
            *, minimum_national_records: int = 7000) -> tuple[list[dict], list[dict], dict]:
    """Return 27 draft observations, summary, and QA report with no writes.

    Mandatory six-digit municipal codes prevent ambiguous national name joins.
    A threshold checks that a full national workbook, not a partial extract,
    was supplied. Synthetic tests may override the threshold.
    """
    if indicator_id not in CONFIG:
        raise ValueError("Unknown territorial indicator")
    if source_bytes[:2] != b"PK":
        raise ValueError("Official workbook must be XLSX/ZIP bytes")
    target = read_municipality_codes(registry)
    if len(target) != 27:
        raise ValueError("Exactly 27 target municipalities required")
    items = (parse_altitude_workbook(source_bytes)
             if indicator_id == "mean_altitude"
             else parse_snai_workbook(source_bytes))
    if len(items) < minimum_national_records:
        raise ValueError(
            f"Incomplete national workbook: only {len(items)} records "
            f"(minimum {minimum_national_records})"
        )
    by_code = {}
    for item in items:
        code = item.municipality_code
        if code is None:
            continue
        if code in by_code:
            raise ValueError(f"Duplicate ISTAT municipality code in workbook: {code}")
        by_code[code] = item

    missing = sorted(set(target.values()) - set(by_code))
    if missing:
        raise ValueError("Target ISTAT codes absent from workbook: " + ", ".join(missing))
    rows = []
    for name, code in target.items():
        item = by_code[code]
        if normalize_text(item.municipality) != normalize_text(name):
            raise ValueError(
                f"Name/code mismatch for {code}: registry={name}, source={item.municipality}"
            )
        meta = CONFIG[indicator_id]
        if indicator_id == "mean_altitude":
            value = float(item.mean_altitude_m)
            min_val, max_val = item.min_altitude_m, item.max_altitude_m
            if not math.isfinite(value) or not -500 <= value <= 9000:
                raise ValueError(f"Invalid altitude for {name}: {value}")
            for boundary in (min_val, max_val):
                if boundary is not None and (
                    not math.isfinite(float(boundary)) or not -500 <= boundary <= 9000
                ):
                    raise ValueError(f"Invalid altitude bounds for {name}")
            if min_val is not None and value < min_val:
                raise ValueError(f"Mean below minimum altitude for {name}")
            if max_val is not None and value > max_val:
                raise ValueError(f"Mean above maximum altitude for {name}")
            if min_val is not None and max_val is not None and min_val > max_val:
                raise ValueError(f"Invalid min/max altitude for {name}")
            row = {
                "municipality": name, "municipality_code": code, "year": "2021",
                "mean_altitude_m": f"{value:.2f}",
                "min_altitude_m": "" if min_val is None else f"{min_val:.2f}",
                "max_altitude_m": "" if max_val is None else f"{max_val:.2f}",
                "source_url": meta["source_url"],
                "limitations": (
                    "Territorial mean altitude from 2021 geography; not municipal-seat "
                    "height, access time or an energy-poverty measurement."
                ),
            }
        else:
            if item.snai_class not in CLASS_LABELS:
                raise ValueError(f"Invalid SNAI A-F category for {name}")
            if item.snai_label != CLASS_LABELS[item.snai_class]:
                raise ValueError(f"Invalid SNAI label for {name}")
            row = {
                "municipality": name, "municipality_code": code, "year": "2020",
                "snai_class": item.snai_class,
                "snai_label": CLASS_LABELS[item.snai_class],
                "source_url": meta["source_url"],
                "limitations": (
                    "Official SNAI policy classification 2020; not a current "
                    "road-time measurement or a linear numeric score."
                ),
            }
        rows.append(row)
    if indicator_id == "mean_altitude":
        vals = [float(row["mean_altitude_m"]) for row in rows]
        summary = [{
            "territory": "Green Community Sinergie in Canavese",
            "municipality_count": str(len(rows)),
            "mean_of_municipal_mean_altitude_m": f"{mean(vals):.2f}",
            "median_municipal_mean_altitude_m": f"{median(vals):.2f}",
            "min_municipal_mean_altitude_m": f"{min(vals):.2f}",
            "max_municipal_mean_altitude_m": f"{max(vals):.2f}",
            "method": "Unweighted descriptive summary of 27 municipal mean altitudes",
        }]
    else:
        counts = Counter(row["snai_class"] for row in rows)
        summary = [{
            "territory": "Green Community Sinergie in Canavese",
            "municipality_count": str(len(rows)),
            **{f"class_{c}": str(counts.get(c, 0)) for c in "ABCDEF"},
            "inner_area_municipalities_D_E_F": str(sum(counts.get(c, 0) for c in "DEF")),
            "method": "Counts of official categorical SNAI 2020 A-F; no composite score",
        }]
    qa = {
        "schema_version": "1.0",
        "indicator_id": indicator_id,
        "reference_year": CONFIG[indicator_id]["reference_year"],
        "source_id": CONFIG[indicator_id]["source_id"],
        "source_url": CONFIG[indicator_id]["source_url"],
        "source_file_sha256": _hash(source_bytes),
        "registry_sha256": _hash(registry.read_bytes()),
        "source_record_count": len(items),
        "target_municipalities": len(rows),
        "checks": [
            "27 municipalities matched by six-digit ISTAT codes and normalized names",
            "national workbook coverage and code uniqueness",
            "indicator-specific numeric range or categorical class checks",
            "source and registry byte-level SHA-256 provenance",
        ],
        "qa_status": "technical_checks_only",
        "verified_source_authenticity": False,
        "verified_historical_geography": False,
        "verified_license": False,
        "verified_independent_sample": False,
        "validated_for_release": False,
    }
    return rows, summary, qa


def write_draft(indicator_id: str, source_xlsx: Path, registry: Path,
                output_dir: Path, *, minimum_national_records: int = 7000) -> dict:
    if indicator_id not in CONFIG:
        raise ValueError("Unknown territorial indicator")
    meta = CONFIG[indicator_id]
    data_path = output_dir / meta["output"]
    summary_path = output_dir / meta["summary"]
    qa_path = output_dir / f"{indicator_id}_qa.json"
    targets = [data_path, summary_path, qa_path]
    if any(path.exists() for path in targets):
        raise FileExistsError("Draft exists; use a new output directory")
    if any(path.resolve() in {source_xlsx.resolve(), registry.resolve()} for path in targets):
        raise ValueError("Cannot overwrite input files")
    rows, summary, qa = prepare(
        indicator_id, source_xlsx.read_bytes(), registry,
        minimum_national_records=minimum_national_records,
    )
    data = csv_bytes(DATA_COLUMNS[indicator_id], rows)
    stats = csv_bytes(SUMMARY_COLUMNS[indicator_id], summary)
    qa["data_csv_sha256"] = _hash(data)
    qa["summary_csv_sha256"] = _hash(stats)
    qa_blob = (json.dumps(qa, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    output_dir.mkdir(parents=True, exist_ok=True)
    created = []
    try:
        for path, payload in zip(targets, (data, stats, qa_blob)):
            with path.open("xb") as handle:
                handle.write(payload)
            created.append(path)
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    return qa


def _date(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        checked = date.fromisoformat(value)
        return checked.isoformat() == value and checked <= date.today()
    except ValueError:
        return False


def _https(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        p = urlsplit(value)
        return p.scheme == "https" and bool(p.netloc)
    except ValueError:
        return False


def promote(indicator_id: str, source_xlsx: Path, registry: Path, draft_dir: Path,
            approval_path: Path, matrix: Path, indicators_dir: Path) -> int:
    """Publish only when current source bytes and human review evidence match.

    JSON signatures are structural guards, not cryptographic human signatures.
    Review authenticity must be established outside the script.
    """
    if indicator_id not in CONFIG:
        raise ValueError("Unknown territorial indicator")
    meta = CONFIG[indicator_id]
    data_path = draft_dir / meta["output"]
    summary_path = draft_dir / meta["summary"]
    qa = json.loads((draft_dir / f"{indicator_id}_qa.json").read_text(encoding="utf-8"))
    approval = json.loads(approval_path.read_text(encoding="utf-8"))
    expected = {
        "indicator_id": indicator_id,
        "reference_year": meta["reference_year"],
        "decision": "approved",
        "source_file_sha256": _hash(source_xlsx.read_bytes()),
        "registry_sha256": _hash(registry.read_bytes()),
        "data_csv_sha256": _hash(data_path.read_bytes()),
        "summary_csv_sha256": _hash(summary_path.read_bytes()),
    }
    if any(qa.get(k) != v or approval.get(k) != v for k, v in expected.items()
           if k not in {"decision"}):
        raise ValueError("Review or QA metadata does not match current source and draft hashes")
    if approval.get("decision") != "approved":
        raise ValueError("Missing explicit approval")
    if not isinstance(approval.get("reviewed_by"), str) or not approval["reviewed_by"].strip():
        raise ValueError("Named human reviewer required")
    if not _date(approval.get("reviewed_on")) or not _https(approval.get("review_evidence_url")):
        raise ValueError("Valid review date and durable HTTPS evidence required")
    if not isinstance(approval.get("review_notes"), str) or not approval["review_notes"].strip():
        raise ValueError("Review notes required")
    for field in (
        "source_authenticity_reviewed", "historical_geography_reviewed",
        "license_reviewed", "independent_sample_reviewed",
    ):
        if approval.get(field) is not True:
            raise ValueError(f"Human QA evidence missing: {field}")
    # Recompute the full 27-municipality results from the unchanged source.
    rows, summary, fresh = prepare(indicator_id, source_xlsx.read_bytes(), registry)
    if fresh["source_file_sha256"] != qa["source_file_sha256"]:
        raise ValueError("Original source changed")
    if _hash(csv_bytes(DATA_COLUMNS[indicator_id], rows)) != qa["data_csv_sha256"]:
        raise ValueError("Prepared observation CSV has changed")
    if _hash(csv_bytes(SUMMARY_COLUMNS[indicator_id], summary)) != qa["summary_csv_sha256"]:
        raise ValueError("Prepared summary CSV has changed")
    with matrix.open(encoding="utf-8", newline="") as handle:
        matrix_rows = list(csv.DictReader(handle))
    affected = [row for row in matrix_rows if row["indicator_id"] == indicator_id]
    if len(affected) != 27 or len({row["municipality"] for row in affected}) != 27:
        raise ValueError("Matrix must include 27 unique rows for the target indicator")
    by_name = {row["municipality"]: row for row in rows}
    if set(by_name) != {row["municipality"] for row in affected}:
        raise ValueError("Draft municipalities do not match matrix")
    updates = []
    for row in affected:
        observation = by_name[row["municipality"]]
        value = (observation["mean_altitude_m"] if indicator_id == "mean_altitude"
                 else observation["snai_class"])
        update = dict(row)
        update.update({
            "status": "Dato validato",
            "year": meta["reference_year"],
            "territorial_level": "Comune",
            "unit": meta["unit"],
            "source_url": meta["source_url"],
            "value": value,
            "quality": "Official data; independently reviewed source/coverage/method",
            "limitations": observation["limitations"],
            "notes": (
                f"ISTAT {observation['municipality_code']}; review evidence: "
                + approval["review_evidence_url"]
            ),
        })
        updates.append(update)
    destinations = [indicators_dir / meta["output"], indicators_dir / meta["summary"]]
    if any(path.exists() for path in destinations):
        raise FileExistsError("Published indicator output exists; refusing overwrite")
    indicators_dir.mkdir(parents=True, exist_ok=True)
    created = []
    try:
        for origin, destination in zip((data_path, summary_path), destinations):
            with destination.open("xb") as handle:
                handle.write(origin.read_bytes())
            created.append(destination)
        upsert_indicator_rows(matrix, indicator_id, updates)
    except Exception:
        for destination in created:
            destination.unlink(missing_ok=True)
        raise
    return len(updates)
