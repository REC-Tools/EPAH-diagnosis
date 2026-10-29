"""Independent comparison of local heating degree days with a reviewed legal-table transcription.

The archived official PDF is an historical edition. Agreement alone does not
prove current legal validity or authorize changing a matrix row to validated.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from epah_diagnosis.climate import load_reference
from epah_diagnosis.provenance import sha256_file


CURRENT_ANNEX_URL = (
    "https://def.finanze.it/DocTribFrontend/getAttoNormativoDetail.do"
    "?ACTION=getArticolo&articolo=Allegato+A&codiceOrdinamento=60A+++++0000000"
    "&id=%7B0E4DC3BD-3B00-45E2-9CA6-B4DECB631C36%7D"
)
HISTORIC_ANNEX_PDF = (
    "https://def.finanze.it/DocTribFrontend/getContent.do"
    "?id=%7BDEA36BB0-0D39-469B-B33C-22B29A7DBF3D%7D"
)
CURRENT_VERSION = "2016-08-09"


def compare_reference(snapshot_path: Path, historical_path: Path) -> dict:
    snapshot = load_reference(snapshot_path)
    historical = load_reference(historical_path)
    current = {r.municipality.casefold(): r for r in snapshot}
    old = {r.municipality.casefold(): r for r in historical}
    if set(current) != set(old):
        raise ValueError(
            "Source and legal transcription municipality coverage differ: "
            f"missing in legal: {sorted(set(current) - set(old))}, "
            f"unexpected: {sorted(set(old) - set(current))}"
        )

    value_mismatches = []
    zone_mismatches = []
    altitude_mismatches = []
    for key in sorted(current):
        observed, reference = current[key], old[key]
        if observed.province != reference.province:
            raise ValueError(f"Province mismatch for {observed.municipality}")
        if observed.heating_degree_days != reference.heating_degree_days:
            value_mismatches.append({
                "municipality": observed.municipality,
                "snapshot": observed.heating_degree_days,
                "legal_table": reference.heating_degree_days,
            })
        if observed.climate_zone != reference.climate_zone:
            zone_mismatches.append({
                "municipality": observed.municipality,
                "snapshot": observed.climate_zone,
                "legal_table": reference.climate_zone,
            })
        if observed.municipal_seat_altitude_m != reference.municipal_seat_altitude_m:
            altitude_mismatches.append({
                "municipality": observed.municipality,
                "snapshot_m": observed.municipal_seat_altitude_m,
                "legal_table_m": reference.municipal_seat_altitude_m,
            })

    return {
        "comparison": "historic_official_annex_vs_local_snapshot",
        "reference_edition": "historical_2008",
        "historic_official_url": HISTORIC_ANNEX_PDF,
        "current_official_url": CURRENT_ANNEX_URL,
        "current_legal_edition": CURRENT_VERSION,
        "current_edition_independently_checked": False,
        "municipalities": len(current),
        "snapshot_sha256": sha256_file(snapshot_path),
        "historical_transcription_sha256": sha256_file(historical_path),
        "value_mismatches": value_mismatches,
        "zone_mismatches": zone_mismatches,
        "altitude_mismatches": altitude_mismatches,
        "gg_zone_comparison_passed": not (value_mismatches or zone_mismatches),
        "validated_for_release": False,
        "limitations": [
            "Manual transcription of historical official annex, not a source-file checksum.",
            "Current consolidated Annex A (2016) not independently reviewed.",
            "Regulatory municipal-seat altitude is ancillary to heating degree days.",
        ],
    }


def _url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        part = urlsplit(value)
        return part.scheme == "https" and bool(part.netloc)
    except ValueError:
        return False


def _date(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def approve_with_evidence(report: dict, evidence_path: Path) -> dict:
    """Validate evidence structure and input hashes, not the human review's truth.

    A reviewer must actually compare the current official annex and record a
    durable URL to the review. Do not fabricate these fields.
    """
    if not report["gg_zone_comparison_passed"]:
        raise ValueError("Cannot approve mismatching climate values or zones")
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    fields = {
        "indicator_id": "heating_degree_days",
        "decision": "approved",
        "official_version_reviewed": CURRENT_VERSION,
        "official_url": CURRENT_ANNEX_URL,
        "snapshot_sha256": report["snapshot_sha256"],
        "historical_transcription_sha256": report["historical_transcription_sha256"],
    }
    for field, expected in fields.items():
        if evidence.get(field) != expected:
            raise ValueError(f"Approval evidence missing or inconsistent: {field}")
    if not isinstance(evidence.get("reviewed_by"), str) or not evidence["reviewed_by"].strip():
        raise ValueError("Approval must contain a named reviewer")
    if not _date(evidence.get("reviewed_on")):
        raise ValueError("Approval review date must be ISO YYYY-MM-DD")
    if date.fromisoformat(evidence["reviewed_on"]) > date.today():
        raise ValueError("Review date cannot be in the future")
    if not _url(evidence.get("review_evidence_url")):
        raise ValueError("Human evidence must have a durable HTTPS URL")
    if evidence.get("license_review_decision") != "approved_for_use":
        raise ValueError("Evidence must include a positive legal/source usage review")

    disputed = {item["municipality"] for item in report["altitude_mismatches"]}
    acknowledged = evidence.get("altitude_discrepancies_acknowledged")
    if not isinstance(acknowledged, list) or set(acknowledged) != disputed:
        raise ValueError("Altitude discrepancies must be explicitly acknowledged")
    if not isinstance(evidence.get("review_notes"), str) or not evidence["review_notes"].strip():
        raise ValueError("Review notes are required")
    return {
        **report,
        "current_edition_independently_checked": True,
        "validated_for_release": True,
        "reviewed_by": evidence["reviewed_by"],
        "reviewed_on": evidence["reviewed_on"],
        "review_evidence_url": evidence["review_evidence_url"],
    }
