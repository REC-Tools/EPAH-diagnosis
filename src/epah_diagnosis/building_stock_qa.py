"""Fail-closed preparation of ISTAT CPA 2011 building-vintage proxy."""
from __future__ import annotations

import hashlib
from pathlib import Path

from epah_diagnosis.cli import read_municipality_codes
from epah_diagnosis.istat_building_stock import (
    CPA_2011_URL, filter_by_codes, is_piemonte, parse_cpa_zip,
    weighted_share_pre_1981,
)

SOURCE_PAGE = "https://www.istat.it/notizia/basi-territoriali-e-variabili-censuarie/"
FIELDS = (
    "buildings_pre_1919", "buildings_1919_1945", "buildings_1946_1960",
    "buildings_1961_1970", "buildings_1971_1980", "buildings_1981_1990",
    "buildings_1991_2000", "buildings_2001_2005", "buildings_after_2005",
)


def prepare(source_bytes: bytes, registry: Path, *, min_italy=7000, min_piemonte=900):
    """Return draft rows, weighted benchmarks and QA metadata, with no I/O writes.

    Thresholds can be relaxed in synthetic unit tests, never from production CLI.
    """
    if source_bytes[:2] != b"PK":
        raise ValueError("Expected ISTAT CPA 2011 ZIP archive")
    codes = read_municipality_codes(registry)
    if len(codes) != 27 or len(set(codes.values())) != 27:
        raise ValueError("Expected 27 unique municipality ISTAT codes")
    national = parse_cpa_zip(source_bytes)
    regional = [r for r in national if is_piemonte(r.municipality_code)]
    if len(national) < min_italy or len(regional) < min_piemonte:
        raise ValueError(
            "Source archive has incomplete national/Piemonte coverage: "
            f"{len(national)} Italy and {len(regional)} Piemonte"
        )
    selected = filter_by_codes(national, set(codes.values()))
    if len(selected) != 27:
        raise ValueError(f"Expected 27 building-stock results; got {len(selected)}")
    by_code = {r.municipality_code: r for r in selected}
    rows = []
    for name, code in codes.items():
        rec = by_code[code]
        total, early = rec.residential_buildings_total, rec.buildings_pre_1981
        ages = [getattr(rec, key) for key in FIELDS]
        if not isinstance(total, int) or total <= 0 or early < 0:
            raise ValueError(f"Invalid denominator or numerator: {name}")
        if any(not isinstance(x, int) or x < 0 for x in ages):
            raise ValueError(f"Invalid age counts: {name}")
        if sum(ages[:5]) != early or sum(ages) > total:
            raise ValueError(f"Epoch counts inconsistent with E3/E8-E16: {name}")
        rows.append({
            "municipality_code": code, "municipality": name, "year": "2011",
            "residential_buildings_total": str(total),
            "buildings_pre_1981": str(early),
            **{key: str(getattr(rec, key)) for key in FIELDS},
            "share_pre_1981_pct": f"{rec.share_pre_1981:.2f}",
            "source_url": CPA_2011_URL,
            "quality": "2011 census-section counts aggregated by ISTAT code; independent QA pending",
            "limitations": "Historic proxy; subsequent renovation and actual energy rating unknown.",
        })
    groups = (
        ("Green Community Sinergie in Canavese", selected),
        ("Piemonte", regional),
        ("Italia", national),
    )
    benchmarks = [{
        "territory": name, "year": "2011",
        "municipality_count": str(len(items)),
        "residential_buildings_total": str(sum(x.residential_buildings_total for x in items)),
        "buildings_pre_1981": str(sum(x.buildings_pre_1981 for x in items)),
        "share_pre_1981_pct": f"{weighted_share_pre_1981(items):.2f}",
        "method": "sum(E8:E12)/sum(E3)*100 (building-count weighted)",
        "source_url": CPA_2011_URL,
    } for name, items in groups]
    quality = {
        "indicator_id": "old_building_stock", "reference_year": "2011",
        "source_page": SOURCE_PAGE, "source_url": CPA_2011_URL,
        "archive_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "registry_sha256": hashlib.sha256(registry.read_bytes()).hexdigest(),
        "coverage": len(rows), "national_count": len(national),
        "piemonte_count": len(regional),
        "checks": [
            "27 unique 6-digit municipality codes",
            "positive E3 and consistent E8-E16",
            "whole-archive coverage",
            "benchmarks based on integer counts",
        ],
        "qa_status": "technical_checks_only",
        "source_authenticity_reviewed": False,
        "historical_geography_reviewed": False,
        "license_reviewed": False,
        "independent_sample_reviewed": False,
        "validated_for_release": False,
    }
    return rows, benchmarks, quality


BUILDING_COLUMNS = [
    "municipality_code", "municipality", "year",
    "residential_buildings_total", "buildings_pre_1981", *FIELDS,
    "share_pre_1981_pct", "source_url", "quality", "limitations",
]
BENCHMARK_COLUMNS = [
    "territory", "year", "municipality_count", "residential_buildings_total",
    "buildings_pre_1981", "share_pre_1981_pct", "method", "source_url",
]
