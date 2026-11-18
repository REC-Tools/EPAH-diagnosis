"""Validate proposal metadata, never calculate indicators or approve methodology."""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re

TEXT_FIELDS = ("id", "name", "change_type", "role", "unit", "statistical_unit", "universe",
               "numerator", "denominator", "reference_period", "geography", "source_ref",
               "source_locator", "dataset_code", "definition", "review_status", "local_use", "data_state")
LIST_FIELDS = ("local_requirements", "limitations", "related_inventory", "unresolved_decisions")


def check_catalog(document: dict) -> dict:
    if (not isinstance(document, dict) or document.get("schema_version") != "0.5-methodology-proposals-1"
            or document.get("id_namespace") != "project_local_not_official_epah"
            or document.get("scientific_approval") is not False
            or document.get("publication_allowed") is not False):
        raise ValueError("Expected an explicitly unapproved v0.5 proposal catalogue")
    sources = document.get("sources")
    if not isinstance(sources, dict) or not sources:
        raise ValueError("Source registry is required")
    for source in sources.values():
        if (not isinstance(source, dict) or not source.get("url", "").startswith("https://")
                or not isinstance(source.get("title"), str) or not source["title"].strip()):
            raise ValueError("Every source requires a title and HTTPS URL")
        date.fromisoformat(source["checked_on"])
    indicators = document.get("indicators")
    if not isinstance(indicators, list) or not indicators:
        raise ValueError("Indicator proposals are required")
    identifiers = set()
    for item in indicators:
        if not isinstance(item, dict) or set(item) != set(TEXT_FIELDS + LIST_FIELDS):
            raise ValueError("Indicator contract fields are missing or unknown")
        if any(not isinstance(item[key], str) or not item[key].strip() for key in TEXT_FIELDS):
            raise ValueError("Units, period, universe, numerator, denominator and provenance must be explicit")
        if not re.fullmatch(r"V05-\d{2}", item["id"]) or item["id"] in identifiers:
            raise ValueError("Proposal IDs must be unique project-local V05 identifiers")
        identifiers.add(item["id"])
        if (item["review_status"] != "not_approved" or item["data_state"] != "source_identified_not_acquired"
                or item["local_use"] != "benchmark_only_until_local_protocol"
                or item["geography"] not in {"country", "grid_country_aggregate"}):
            raise ValueError("National proposals cannot be promoted to approved municipal observations")
        if item["source_ref"] not in sources:
            raise ValueError("Unknown source reference")
        if (item["unit"] not in {"percent", "days_per_year", "z_score"}
                or item["role"] not in {"health_context", "climate_exposure", "housing_context",
                    "socioeconomic_context", "mobility_context", "self_reported_affordability",
                    "expenditure_distribution"}):
            raise ValueError("Unknown unit or role; keep context, exposure and outcomes distinct")
        if item["change_type"] not in {"new_epah_2026", "updated_epah_2026", "existing_epah_priority"}:
            raise ValueError("Unknown change type")
        for key in LIST_FIELDS:
            if not isinstance(item[key], list) or any(not isinstance(v, str) or not v.strip() for v in item[key]):
                raise ValueError(f"{key} must contain explicit text items")
        if not item["local_requirements"] or not item["limitations"]:
            raise ValueError("Local evidence requirements and limitations are mandatory")
    return {"status": "proposal_metadata_checked_not_scientific_approval", "proposals": len(indicators),
            "scientific_approval": False, "publication_allowed": False,
            "municipal_series_added": 0, "ids": sorted(identifiers)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check",))
    parser.add_argument("--catalog", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        raw = args.catalog.read_bytes()
        result = check_catalog(json.loads(raw.decode("utf-8")))
        result["catalog_sha256"] = hashlib.sha256(raw).hexdigest()
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f"BLOCKED: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
