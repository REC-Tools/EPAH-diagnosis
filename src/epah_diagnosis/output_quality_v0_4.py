"""Independent semantic audit of a v0.4 technical review pack.

Checks data/HTML/PDF consistency and tamper evidence; never certifies original
sources, scientific validity or authorization to publish territorial results.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path, PurePosixPath
import re

from pypdf import PdfReader

STATUS = "technical_draft_do_not_publish"
REQUIRED = {
    "observations.csv", "review.html", "review.pdf", "metadata.json",
    "observations_manifest.json", "README_REVIEW.txt",
}
SCRIPT = re.compile(
    r'<script\s+type="application/json"\s+id="payload">([\s\S]*?)</script>',
    flags=re.IGNORECASE,
)


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _checked_path(root: Path, name: str) -> Path:
    if (not isinstance(name, str) or not name or "\\" in name
            or PurePosixPath(name).is_absolute()
            or any(part in {"..", "."} for part in PurePosixPath(name).parts)):
        raise ValueError("Unsafe output manifest path")
    target = root / name
    if (not target.resolve().is_relative_to(root.resolve()) or not target.is_file()
            or any(p.is_symlink() for p in (target, *target.parents))):
        raise ValueError(f"Missing or unsafe output: {name}")
    return target


def _json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid JSON object: {path.name}")
    return data


def _manifest(root: Path, filename: str) -> dict:
    receipt = _json(root / filename)
    if (receipt.get("status") != STATUS or receipt.get("publication_allowed") is not False
            or receipt.get("scientific_approval", False) is not False):
        raise ValueError(f"Invalid nonpublication state: {filename}")
    hashes = receipt.get("outputs_sha256")
    if not isinstance(hashes, dict) or not hashes:
        raise ValueError(f"Missing output digests: {filename}")
    for name, expected in hashes.items():
        if not isinstance(expected, str) or not re.fullmatch(r"[a-f0-9]{64}", expected):
            raise ValueError(f"Invalid output digest: {name}")
        if _sha(_checked_path(root, name)) != expected:
            raise ValueError(f"Output checksum mismatch: {name}")
    return receipt


def audit(pack: Path, *, atlas: Path | None = None) -> dict:
    if not pack.is_dir():
        raise ValueError("Review pack directory does not exist")
    manifest = _manifest(pack, "manifest.json")
    if not REQUIRED <= set(manifest["outputs_sha256"]):
        raise ValueError("Missing required review pack files from manifest")
    nested = _json(pack / "observations_manifest.json")
    if nested.get("status") != STATUS or nested.get("publication_allowed") is not False:
        raise ValueError("Observation export incorrectly presented as approved")
    for name, expected in nested.get("outputs_sha256", {}).items():
        if name in {"metadata.json", "observations.csv"}:
            if _sha(pack / name) != expected:
                raise ValueError(f"Observation export checksum mismatch: {name}")
    if atlas is not None:
        bound = manifest.get("reference_atlas_sha256")
        if not isinstance(bound, dict):
            raise ValueError("Atlas provenance missing")
        for name in ("atlas_data.json", "atlas_manifest.json"):
            if _sha(_checked_path(atlas, name)) != bound.get(name):
                raise ValueError(f"Atlas input mismatch: {name}")
    metadata = _json(pack / "metadata.json")
    metrics = metadata.get("indicators")
    if (metadata.get("status") != STATUS or metadata.get("publication_allowed") is not False
            or metadata.get("scientific_approval") is not False or not isinstance(metrics, list)
            or not metrics):
        raise ValueError("Invalid observation metadata or approval")
    ids = [item.get("indicator_id") for item in metrics]
    if len(ids) != len(set(ids)) or not all(isinstance(k, str) and k for k in ids):
        raise ValueError("Duplicate or missing indicator identifiers")
    if manifest.get("indicator_slots") != len(ids) or metadata.get("municipalities") != 27:
        raise ValueError("Review pack indicator inventory mismatch")

    with (pack / "observations.csv").open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)) or not {"municipality_code", "municipality",
              "indicator_id", "value", "missing_reason", "publication_allowed",
              "reference_period", "unit", "source", "numerator", "denominator"} <= set(fields):
            raise ValueError("Invalid observations CSV schema")
        rows = list(reader)
    if len(rows) != len(ids) * 27 or metadata.get("observations") != len(rows):
        raise ValueError("Review pack must have exactly 27 rows per metric")
    by_metric = Counter(row["indicator_id"] for row in rows)
    if any(by_metric.get(k) != 27 for k in ids) or set(by_metric) != set(ids):
        raise ValueError("Indicator coverage mismatch")
    if len({(r["indicator_id"], r["municipality_code"]) for r in rows}) != len(rows):
        raise ValueError("Duplicate municipality/indicator pair")
    scope = {r["municipality_code"]: r["municipality"] for r in rows}
    if (len(scope) != 27
            or any(not re.fullmatch(r"[0-9]{6}", key) or not value for key, value in scope.items())
            or any(scope[r["municipality_code"]] != r["municipality"] for r in rows)):
        raise ValueError("Invalid or inconsistent municipality registry")
    for item in metrics:
        key = item["indicator_id"]
        subset = [r for r in rows if r["indicator_id"] == key]
        complete = all(r["missing_reason"] == "" and r["value"] != "" for r in subset)
        missing = all(r["missing_reason"] == "not_acquired" and r["value"] == ""
                      for r in subset)
        if not (complete or missing):
            raise ValueError(f"Partially available metric without explicit missingness: {key}")
        if item.get("available") is not complete or item.get("municipalities") != (27 if complete else 0):
            raise ValueError(f"Metric availability mismatch: {key}")
        periods = sorted({r["reference_period"] for r in subset if r["reference_period"]})
        if periods != item.get("reference_periods"):
            raise ValueError(f"Reference periods mismatch: {key}")
    for row in rows:
        if row["publication_allowed"] != "false":
            raise ValueError("Observation claims publication approval")
        if bool(row["numerator"]) != bool(row["denominator"]):
            raise ValueError("Partial numerator or denominator")
        if row["missing_reason"] != "" and (row["numerator"] or row["denominator"]):
            raise ValueError("Missing observation has counts")

    html = (pack / "review.html").read_text(encoding="utf-8")
    match = SCRIPT.search(html)
    if not match:
        raise ValueError("Missing machine-readable HTML payload")
    embedded = json.loads(match.group(1))
    if (embedded.get("status") != STATUS or embedded.get("publication_allowed") is not False
            or not isinstance(embedded.get("rows"), list)
            or not isinstance(embedded.get("indicators"), list)):
        raise ValueError("HTML snapshot lacks technical-only state")
    if [item.get("indicator_id") for item in embedded["indicators"]] != ids:
        raise ValueError("HTML indicator inventory mismatch")
    # The HTML embeds each original observation plus a human-facing display field.
    html_rows = embedded["rows"]
    if len(html_rows) != len(rows):
        raise ValueError("HTML row count mismatch")
    for i, (csv_row, shown) in enumerate(zip(rows, html_rows)):
        if {k: v for k, v in shown.items() if k != "display"} != csv_row:
            raise ValueError(f"HTML / CSV observation mismatch at row {i + 1}")
        cells = shown.get("display")
        if (not isinstance(cells, list) or len(cells) != 5
                or cells[:3] != [csv_row["municipality"], csv_row["municipality_code"],
                                csv_row["reference_period"] or "—"]):
            raise ValueError(f"Malformed HTML display at row {i + 1}")
        expected_value = (
            "non acquisito" if csv_row["missing_reason"] == "not_acquired"
            else csv_row["value"] + (" " + csv_row["unit"] if csv_row["value"] else "")
        )
        counts = (csv_row["numerator"] + " / " + csv_row["denominator"]
                  if csv_row["numerator"] else "—")
        if cells[3] != expected_value or cells[4] != counts:
            raise ValueError(f"HTML displayed values mismatch at row {i + 1}")

    try:
        pdf = PdfReader(str(pack / "review.pdf"))
        if len(pdf.pages) < len(ids) + 1:
            raise ValueError("PDF is missing indicator sections")
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception as exc:
        raise ValueError("Unreadable review PDF") from exc
    if "NON PUBBLICARE" not in text:
        raise ValueError("PDF missing nonpublication disclaimer")
    if any(key not in text for key in ids):
        raise ValueError("PDF missing one or more indicator identifiers")
    return {
        "schema_version": "v0.4-output-quality",
        "status": "technical_output_consistency_passed",
        "scientific_approval": False, "publication_allowed": False,
        "municipalities": 27, "indicator_slots": len(ids),
        "observations": len(rows), "html_csv_semantic_match": True,
        "pdf_indicator_sections": len(ids), "hashes_verified": True,
        "visual_review_completed": False,
    }
