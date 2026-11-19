"""Source dates for review, without recency weights or scientific promotion."""
from datetime import date
import re

FIELDS = {"id", "title", "url", "guide_page", "category", "kind", "verification_status",
          "publication_year", "reference_year_start", "reference_year_end", "dataset_acquired_on",
          "metadata_checked_on", "temporal_evidence"}


def _year(value):
    return type(value) is int and 1000 <= value <= 9999


def check_source_register(document):
    if (set(document) != {"schema_version", "target_analysis_year", "scientific_approval",
                          "publication_allowed", "guide", "sources"}
            or document["schema_version"] != "0.5-source-register-1"
            or document["scientific_approval"] is not False
            or document["publication_allowed"] is not False
            or not _year(document["target_analysis_year"])):
        raise ValueError("Expected an unapproved source register with an explicit target year")
    guide = document["guide"]
    if (set(guide) != {"url", "sha256", "edition_date", "acquired_on", "resource_count"}
            or not guide["url"].startswith("https://")
            or not re.fullmatch(r"[0-9a-f]{64}", guide["sha256"])
            or type(guide["resource_count"]) is not int or guide["resource_count"] < 1):
        raise ValueError("Guide provenance is required")
    date.fromisoformat(guide["edition_date"])
    date.fromisoformat(guide["acquired_on"])
    sources = document["sources"]
    if not isinstance(sources, list) or len(sources) != guide["resource_count"]:
        raise ValueError("Every guide resource must be accounted for")
    identifiers, periods = set(), []
    for source in sources:
        if not isinstance(source, dict) or set(source) != FIELDS:
            raise ValueError("Source fields missing or unknown; weights are not supported")
        if any(not isinstance(source[key], str) or not source[key].strip()
               for key in ["id", "title", "url", "category", "kind", "temporal_evidence"]):
            raise ValueError("Source identity and temporal evidence must be explicit")
        if source["id"] in identifiers or not source["url"].startswith("https://"):
            raise ValueError("Source IDs must be unique and URLs HTTPS")
        identifiers.add(source["id"])
        if type(source["guide_page"]) is not int or source["guide_page"] < 1:
            raise ValueError("A one-based guide page is required")
        for key in ["publication_year", "reference_year_start", "reference_year_end"]:
            if source[key] is not None and not _year(source[key]):
                raise ValueError("Years must be integers or null, not publication-date guesses")
        start, end = source["reference_year_start"], source["reference_year_end"]
        if (start is None) != (end is None) or (start is not None and start > end):
            raise ValueError("Reference interval must be complete and ordered, or both null")
        for key in ["dataset_acquired_on", "metadata_checked_on"]:
            if source[key] is not None:
                date.fromisoformat(source[key])
        if source["verification_status"] not in {"indexed_only", "metadata_checked", "access_failed"}:
            raise ValueError("Unknown verification status; no approval may be inferred")
        if source["verification_status"] != "indexed_only" and source["metadata_checked_on"] is None:
            raise ValueError("Checked or failed access must name its verification date")
        periods.append({"id": source["id"], "reference_year_end": end,
                        "target_minus_reference_end_years": None if end is None else document["target_analysis_year"] - end})
    return {"status": "source_period_metadata_checked_not_scientific_approval",
            "target_analysis_year": document["target_analysis_year"], "sources": len(sources),
            "distinct_urls": len({source["url"] for source in sources}),
            "weights_applied": False, "scientific_approval": False, "publication_allowed": False,
            "municipal_series_added": 0, "periods": periods}
