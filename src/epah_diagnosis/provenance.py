"""Read-only provenance records for real local artifact bytes.

A generated manifest is always a QA-unassessed draft, not a source-validation
certificate. Metadata is copied from the registry and never invented.
"""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(
    artifact: Path,
    indicator_id: str,
    catalog_path: Path,
    registry_path: Path,
    *,
    reference_year: str,
    source_files: dict[str, Path] | None = None,
    git_commit: str | None = None,
    entrypoint: str | None = None,
) -> dict:
    if not artifact.is_file():
        raise FileNotFoundError(f"Missing artifact: {artifact}")
    if not reference_year.strip():
        raise ValueError("reference_year is required")

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    indicators = {item["id"]: item for item in catalog["indicators"]}
    sources = {item["id"]: item for item in registry["sources"]}
    if indicator_id not in indicators:
        raise ValueError(f"Unknown indicator: {indicator_id}")
    required_ids = indicators[indicator_id]["source_ids"]
    if not required_ids:
        raise ValueError("Indicator has no registered source IDs")
    files = source_files or {}
    if set(files) - set(required_ids):
        raise ValueError("Source file identifiers must match the indicator catalog")
    records = []
    for identifier in required_ids:
        if identifier not in sources:
            raise ValueError(f"Unregistered source: {identifier}")
        item = sources[identifier]
        path = files.get(identifier)
        if path is not None and not path.is_file():
            raise FileNotFoundError(f"Missing source file: {path}")
        records.append({
            "source_id": identifier,
            "landing_url": item.get("landing_url"),
            "download_url": item.get("data_url"),
            "source_file_sha256": sha256_file(path) if path is not None else None,
            "reference_year": item.get("reference_year"),
            "publication_date": item.get("published_at"),
            "retrieved_at": None,
            "license": item.get("license"),
            "license_status": item.get("license_status", "not_recorded"),
            "source_verification_status": item.get("source_verification_status", "not_recorded"),
        })

    return {
        "schema_version": "1.0",
        "artifact": {
            "id": f"{indicator_id}-{reference_year}",
            "type": "indicator_table",
            "path": artifact.name,
            "indicator_id": indicator_id,
            "reference_year": reference_year,
            "territorial_level": "municipality",
            "geography_version": None,
            "sha256": sha256_file(artifact),
        },
        "sources": records,
        "processing": {
            "generated_at": datetime.now(UTC).isoformat(),
            "git_commit": git_commit,
            "entrypoint": entrypoint,
            "parameters": {},
        },
        "quality": {
            "expected_municipalities": 27,
            "observed_municipalities": None,
            "duplicate_keys": None,
            "missing_values": None,
            "checks": [],
            "qa_result": "not_assessed",
            "exceptions": [],
        },
        "publication": {
            "status": "draft",
            "approved_by": None,
            "approved_at": None,
            "limitations": "Manifest records file integrity only. No independent scientific or source QA performed.",
        },
    }
