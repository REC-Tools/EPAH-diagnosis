"""Offline, review-gated education and passenger-rail accessibility.

Technical checks do not certify whether the school offer or a rail service
is operational today. The underlying ISTAT road network is from 2020,
and origins/destinations use the 2021 municipal geography.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import statistics
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from epah_diagnosis.cli import read_municipality_codes
from epah_diagnosis.dea_accessibility_qa import read_routes, sha256
from epah_diagnosis.education_access import (
    SCHOOL_REGISTRY_URL, SECONDARY_PATHWAYS_URL,
    _decode_csv, build_upper_secondary_poles,
)
from epah_diagnosis.geography import parse_boundaries_zip
from epah_diagnosis.matrix_update import upsert_indicator_rows
from epah_diagnosis.rail_access import load_rail_gateways
from epah_diagnosis.service_access import normalize_text

ROAD_SOURCE = "https://www.istat.it/notizia/matrici-di-contiguita-distanza-e-pendolarismo/"
MIM_SOURCE = "https://dati.istruzione.it/opendata/"
RAIL_SOURCE = "https://www.sfmtorino.it/le-linee-sfm/sfm1-pont-rivarolo-chieri/"

INDICATORS = {
    "upper_secondary_accessibility": {
        "data_name": "upper_secondary_accessibility_minutes.csv",
        "summary_name": "upper_secondary_accessibility_summary.csv",
        "destination_name": "upper_secondary_poles_2024_25.csv",
        "reference_year": "2021",
        "service_vintage": "2024/25",
        "source_url": MIM_SOURCE,
    },
    "rail_accessibility": {
        "data_name": "rail_accessibility_minutes.csv",
        "summary_name": "rail_accessibility_summary.csv",
        "destination_name": "active_rail_gateways_review_snapshot.csv",
        "reference_year": "2021",
        "service_vintage": "2026 snapshot, to verify",
        "source_url": RAIL_SOURCE,
    },
}
DATA_COLS = [
    "municipality", "municipality_code", "nearest_service_municipality",
    "nearest_service_code", "service_names", "travel_time_minutes",
    "distance_km", "service_reference", "road_geography_year",
    "road_graph_year", "source_road", "source_service", "limitations",
]
SUMMARY_COLS = [
    "territory", "municipality_count", "mean_minutes", "median_minutes",
    "min_minutes", "max_minutes", "municipalities_over_30_min",
    "municipalities_over_40_min", "destination_municipalities",
    "service_reference", "method",
]
DEST_COLS = [
    "municipality", "municipality_code", "service_name",
    "service_type", "service_reference", "evidence",
]


def _csv_bytes(fields: list[str], rows: list[dict]) -> bytes:
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def _source_names_and_snapshot(
    indicator_id: str,
    *,
    school_registry: Path | None = None,
    school_pathways: Path | None = None,
    rail_gateways: Path | None = None,
    min_school_registry: int = 1000,
    min_school_pathways: int = 1000,
    min_school_poles: int = 10,
    min_rail_gateways: int = 5,
) -> tuple[list[dict], dict[str, str], dict]:
    if indicator_id == "upper_secondary_accessibility":
        if school_registry is None or school_pathways is None:
            raise ValueError("Both original MIM 2024/25 CSVs are required")
        original_registry = school_registry.read_bytes()
        original_pathways = school_pathways.read_bytes()
        if original_registry.lstrip().lower().startswith((b"<html", b"<!doctype html")):
            raise ValueError("School registry download is HTML, not original CSV")
        if original_pathways.lstrip().lower().startswith((b"<html", b"<!doctype html")):
            raise ValueError("School pathways download is HTML, not original CSV")
        schools = _decode_csv(original_registry)
        pathways = _decode_csv(original_pathways)
        if len(schools) < min_school_registry or len(pathways) < min_school_pathways:
            raise ValueError(
                f"Incomplete MIM school/pathway dataset: {len(schools)}/{len(pathways)}"
            )
        poles = build_upper_secondary_poles(schools, pathways, "Piemonte")
        if len(poles) < min_school_poles:
            raise ValueError(f"Too few complete school poles: {len(poles)}")
        if len({normalize_text(p.municipality) for p in poles}) != len(poles):
            raise ValueError("Duplicate school-pole municipality")
        service_rows = [
            {
                "municipality": p.municipality,
                "service_name": "Liceo classico/scientifico + tecnico/professionale",
                "service_type": "complete_upper_secondary_offer",
                "service_reference": "2024/25",
                "evidence": SCHOOL_REGISTRY_URL + " | " + SECONDARY_PATHWAYS_URL,
            }
            for p in poles
        ]
        provenance = {
            "school_registry_sha256": sha256(school_registry),
            "school_pathways_sha256": sha256(school_pathways),
            "school_registry_row_count": len(schools),
            "school_pathways_row_count": len(pathways),
            "service_definition": (
                "Both classical/scientific lyceum and technical/professional "
                "pathway in the same municipality; historical MIM 2024/25 proxy."
            ),
        }
    elif indicator_id == "rail_accessibility":
        if rail_gateways is None:
            raise ValueError("Original versioned rail-gateway CSV is required")
        with rail_gateways.open(encoding="utf-8", newline="") as f:
            raw = list(csv.DictReader(f))
        if len(raw) < min_rail_gateways:
            raise ValueError(f"Incomplete rail gateway snapshot: {len(raw)} records")
        active = load_rail_gateways(rail_gateways)
        if len(active) < min_rail_gateways:
            raise ValueError("Too few verified-as-active passenger rail stations")
        unique_stations = set()
        service_rows = []
        for gateway in active:
            name = normalize_text(gateway.station_name)
            key = (name, normalize_text(gateway.municipality))
            if key in unique_stations:
                raise ValueError("Duplicate active passenger rail station")
            unique_stations.add(key)
            if not gateway.source.strip() or not _https(gateway.source_url):
                raise ValueError("Rail gateway lacks operator and HTTPS evidence URL")
            service_rows.append({
                "municipality": gateway.municipality,
                "service_name": gateway.station_name,
                "service_type": "active_passenger_rail_snapshot",
                "service_reference": "2026 snapshot; current operation unverified",
                "evidence": gateway.source_url,
            })
        provenance = {
            "rail_snapshot_sha256": sha256(rail_gateways),
            "rail_snapshot_raw_rows": len(raw),
            "active_passenger_rail_station_count": len(active),
            "excluded_nonactive_rows": len(raw) - len(active),
            "service_definition": (
                "Active passenger rail in curated Canavese-relevant snapshot; "
                "exclude bus substitution, service frequency not measured."
            ),
        }
    else:
        raise ValueError(f"Unknown accessibility indicator: {indicator_id}")

    names: dict[str, str] = {}
    for item in service_rows:
        normalized = normalize_text(item["municipality"])
        if not normalized:
            raise ValueError("Empty service municipality")
        if normalized in names and names[normalized] != item["municipality"]:
            raise ValueError("Inconsistent names for one destination municipality")
        names[normalized] = item["municipality"]
    return service_rows, names, provenance


def _resolve_codes(
    boundaries_zip: Path,
    targets: dict[str, str],
    destination_names: dict[str, str],
) -> dict[str, str]:
    all_names = set(targets) | set(destination_names.values())
    boundary = parse_boundaries_zip(boundaries_zip.read_bytes(), all_names)
    by_normalized: dict[str, str] = {}
    for feature in boundary["features"]:
        props = feature["properties"]
        normalized = normalize_text(props["municipality"])
        code = props["municipality_code"]
        if normalized in by_normalized:
            raise ValueError("Duplicated boundary municipality")
        by_normalized[normalized] = code
    if len(by_normalized) != len({normalize_text(name) for name in all_names}):
        raise ValueError("ISTAT boundary coverage missing destination or target")
    for name, code in targets.items():
        if by_normalized.get(normalize_text(name)) != code:
            raise ValueError(f"ISTAT registry and official boundaries codes disagree: {name}")
    return by_normalized


def prepare(
    indicator_id: str,
    road_zip: Path,
    boundaries_zip: Path,
    registry: Path,
    *,
    school_registry: Path | None = None,
    school_pathways: Path | None = None,
    rail_gateways: Path | None = None,
    min_school_registry: int = 1000,
    min_school_pathways: int = 1000,
    min_school_poles: int = 10,
    min_rail_gateways: int = 5,
) -> tuple[list[dict], list[dict], list[dict], dict]:
    if indicator_id not in INDICATORS:
        raise ValueError(f"Unknown indicator: {indicator_id}")
    target = read_municipality_codes(registry)
    if len(target) != 27:
        raise ValueError("Exactly 27 target municipalities required")
    services, names, meta = _source_names_and_snapshot(
        indicator_id,
        school_registry=school_registry,
        school_pathways=school_pathways,
        rail_gateways=rail_gateways,
        min_school_registry=min_school_registry,
        min_school_pathways=min_school_pathways,
        min_school_poles=min_school_poles,
        min_rail_gateways=min_rail_gateways,
    )
    codes = _resolve_codes(boundaries_zip, target, names)
    destinations = {codes[key]: name for key, name in names.items()}
    origins = {code: name for name, code in target.items()}
    if not destinations or len(destinations) != len(names):
        raise ValueError("Destination municipality codes are missing or duplicated")

    selected, count = read_routes(road_zip, origins, destinations)
    by_destination: dict[str, list[dict]] = {}
    for service in services:
        code = codes[normalize_text(service["municipality"])]
        by_destination.setdefault(code, []).append(service)
    destination_rows = []
    for code, members in sorted(by_destination.items()):
        for item in sorted(members, key=lambda x: x["service_name"]):
            destination_rows.append({
                "municipality": destinations[code], "municipality_code": code,
                **{key: item[key] for key in (
                    "service_name", "service_type", "service_reference", "evidence"
                )},
            })
    meta_config = INDICATORS[indicator_id]
    limitations = (
        "ISTAT 2021 municipal reference-point road time, graph 2020; not a "
        "door-to-door or public transport travel time. Candidate services "
        "are limited to Piemonte / curated Canavese snapshot, not necessarily "
        "the closest eligible facility across Italy. The service offer/status "
        "has a different vintage and requires independent human verification."
    )
    data = []
    for name, code in target.items():
        minutes, dest, km = selected[code]
        choices = by_destination[dest]
        data.append({
            "municipality": name, "municipality_code": code,
            "nearest_service_municipality": destinations[dest],
            "nearest_service_code": dest,
            "service_names": " | ".join(sorted({x["service_name"] for x in choices})),
            "travel_time_minutes": f"{minutes:.2f}",
            "distance_km": "" if km is None else f"{km:.2f}",
            "service_reference": meta_config["service_vintage"],
            "road_geography_year": "2021",
            "road_graph_year": "2020",
            "source_road": ROAD_SOURCE,
            "source_service": meta_config["source_url"],
            "limitations": limitations,
        })
    vals = [float(x["travel_time_minutes"]) for x in data]
    summary = [{
        "territory": "Green Community Sinergie in Canavese",
        "municipality_count": str(len(data)),
        "mean_minutes": f"{statistics.mean(vals):.2f}",
        "median_minutes": f"{statistics.median(vals):.2f}",
        "min_minutes": f"{min(vals):.2f}",
        "max_minutes": f"{max(vals):.2f}",
        "municipalities_over_30_min": str(sum(v > 30 for v in vals)),
        "municipalities_over_40_min": str(sum(v > 40 for v in vals)),
        "destination_municipalities": str(len(destinations)),
        "service_reference": meta_config["service_vintage"],
        "method": (
            "Minimum complete-grid ISTAT 2021 TEP_TOT to eligible "
            "Piemonte/Canavese-reference destination municipalities"
        ),
    }]
    quality = {
        "schema_version": "1.0",
        "indicator_id": indicator_id,
        "road_geography_year": "2021",
        "road_graph_year": "2020",
        "service_vintage": meta_config["service_vintage"],
        "service_source_url": meta_config["source_url"],
        "road_source_url": ROAD_SOURCE,
        "origin_count": len(data),
        "destination_municipality_count": len(destinations),
        "complete_route_pairs": count,
        "expected_route_pairs": len(origins) * len(destinations),
        "road_zip_sha256": sha256(road_zip),
        "boundaries_zip_sha256": sha256(boundaries_zip),
        "registry_csv_sha256": sha256(registry),
        **meta,
        "technical_checks": [
            "27 unique ISTAT municipality codes with 2026 boundary join",
            "complete origin-by-destination road-time grid, finite non-negative TEP_TOT",
            "eligible school offer or active passenger rail snapshot",
            "minimum route time selected per origin, no composite score",
        ],
        "road_2021_to_registry_2026_crosswalk_reviewed": False,
        "source_authenticity_reviewed": False,
        "service_eligibility_reviewed": False,
        "out_of_region_service_coverage_reviewed": False,
        "license_reviewed": False,
        "independent_route_sample_reviewed": False,
        "qa_status": "technical_checks_only",
        "validated_for_release": False,
    }
    return data, summary, destination_rows, quality


def write_draft(
    indicator_id: str,
    road_zip: Path,
    boundaries_zip: Path,
    registry: Path,
    out_dir: Path,
    **sources,
) -> dict:
    if indicator_id not in INDICATORS:
        raise ValueError(f"Unknown indicator: {indicator_id}")
    cfg = INDICATORS[indicator_id]
    targets = [
        out_dir / cfg["data_name"], out_dir / cfg["summary_name"],
        out_dir / cfg["destination_name"],
        out_dir / f"{indicator_id}_qa.json",
    ]
    inputs = {p.resolve() for p in (road_zip, boundaries_zip, registry)}
    inputs.update(
        p.resolve() for key, p in sources.items()
        if key in {"school_registry", "school_pathways", "rail_gateways"} and p is not None
    )
    if any(p.resolve() in inputs for p in targets):
        raise ValueError("Draft output path overlaps input source")
    if any(p.exists() for p in targets):
        raise FileExistsError("Draft already exists; use a fresh directory")
    data, summary, destinations, report = prepare(
        indicator_id, road_zip, boundaries_zip, registry, **sources
    )
    blobs = [
        _csv_bytes(DATA_COLS, data),
        _csv_bytes(SUMMARY_COLS, summary),
        _csv_bytes(DEST_COLS, destinations),
    ]
    for field, b in zip(
        ("data_csv_sha256", "summary_csv_sha256", "destination_csv_sha256"), blobs
    ):
        report[field] = hashlib.sha256(b).hexdigest()
    blobs.append((json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    try:
        for path, payload in zip(targets, blobs):
            with path.open("xb") as f:
                f.write(payload)
            written.append(path)
    except Exception:
        for path in written:
            path.unlink(missing_ok=True)
        raise
    return report


def _valid_date(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        d = date.fromisoformat(value)
        return d.isoformat() == value and d <= date.today()
    except ValueError:
        return False


def _https(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = urlsplit(value)
        return parsed.scheme == "https" and bool(parsed.netloc)
    except ValueError:
        return False


def promote(
    indicator_id: str, road_zip: Path, boundaries_zip: Path, registry: Path,
    draft_dir: Path, approval_file: Path, matrix: Path, published_dir: Path,
    **sources,
) -> int:
    """Publish after real independent review and rechecking exact source bytes."""
    if indicator_id not in INDICATORS:
        raise ValueError(f"Unknown indicator: {indicator_id}")
    cfg = INDICATORS[indicator_id]
    paths = [
        draft_dir / cfg["data_name"], draft_dir / cfg["summary_name"],
        draft_dir / cfg["destination_name"],
    ]
    qa = json.loads((draft_dir / f"{indicator_id}_qa.json").read_text(encoding="utf-8"))
    review = json.loads(approval_file.read_text(encoding="utf-8"))
    data, summary, dest, calculated = prepare(
        indicator_id, road_zip, boundaries_zip, registry, **sources
    )
    blobs = [
        _csv_bytes(DATA_COLS, data),
        _csv_bytes(SUMMARY_COLS, summary),
        _csv_bytes(DEST_COLS, dest),
    ]
    hashes = {
        "road_zip_sha256": sha256(road_zip),
        "boundaries_zip_sha256": sha256(boundaries_zip),
        "registry_csv_sha256": sha256(registry),
        "data_csv_sha256": hashlib.sha256(blobs[0]).hexdigest(),
        "summary_csv_sha256": hashlib.sha256(blobs[1]).hexdigest(),
        "destination_csv_sha256": hashlib.sha256(blobs[2]).hexdigest(),
    }
    for k in ("school_registry_sha256", "school_pathways_sha256", "rail_snapshot_sha256"):
        if k in calculated:
            hashes[k] = calculated[k]
    expected = {
        "indicator_id": indicator_id,
        "road_geography_year": "2021",
        "road_graph_year": "2020",
        "service_vintage": cfg["service_vintage"],
        **hashes,
    }
    for key, value in expected.items():
        if qa.get(key) != value or review.get(key) != value:
            raise ValueError(f"Review or draft checksum does not match original: {key}")
    if review.get("decision") != "approved":
        raise ValueError("Human QA decision is not approved")
    if not isinstance(review.get("reviewed_by"), str) or not review["reviewed_by"].strip():
        raise ValueError("Named reviewer missing")
    if not _valid_date(review.get("reviewed_on")) or not _https(review.get("review_evidence_url")):
        raise ValueError("Valid review date and HTTPS evidence link required")
    if not isinstance(review.get("review_notes"), str) or not review["review_notes"].strip():
        raise ValueError("Review notes missing")
    for field in (
        "road_2021_to_registry_2026_crosswalk_reviewed",
        "source_authenticity_reviewed", "service_eligibility_reviewed",
        "out_of_region_service_coverage_reviewed", "license_reviewed",
        "independent_route_sample_reviewed",
    ):
        if review.get(field) is not True:
            raise ValueError(f"Missing actual human QA verification: {field}")
    if review.get("methodology_scope_decision") != "piemonte_curated_proxy_approved_with_limits":
        raise ValueError("Review must approve explicit limited service destination scope")
    if any(sha256(p) != h for p, h in zip(paths, hashes_values_for_draft(hashes))):
        raise ValueError("Draft published files differ from hash-matched source results")
    if calculated["expected_route_pairs"] != qa.get("expected_route_pairs"):
        raise ValueError("Route grid changed since draft")

    with matrix.open(encoding="utf-8", newline="") as f:
        current = list(csv.DictReader(f))
    previous = [row for row in current if row["indicator_id"] == indicator_id]
    if len(previous) != 27 or len({row["municipality"] for row in previous}) != 27:
        raise ValueError("Verification matrix must contain 27 unique core indicator rows")
    by_name = {item["municipality"]: item for item in data}
    if set(by_name) != {row["municipality"] for row in previous}:
        raise ValueError("Canonical matrix and latest draft municipal coverage differ")
    updated = []
    for old in previous:
        item = by_name[old["municipality"]]
        row = dict(old)
        row.update({
            "status": "Dato validato",
            "year": "2021",
            "territorial_level": "Comune",
            "unit": "minuti",
            "source_url": cfg["source_url"],
            "value": item["travel_time_minutes"],
            "quality": "ISTAT TEP_TOT 2021 and independently reviewed service destination proxy",
            "limitations": item["limitations"],
            "notes": (
                f"Nearest eligible municipality {item['nearest_service_municipality']} "
                f"(ISTAT {item['nearest_service_code']}); human QA: {review['review_evidence_url']}"
            ),
        })
        updated.append(row)
    target_paths = [published_dir / name for name in (
        cfg["data_name"], cfg["summary_name"], cfg["destination_name"]
    )]
    if any(p.exists() for p in target_paths):
        raise FileExistsError("Published dataset already exists; refusing overwrite")
    published_dir.mkdir(parents=True, exist_ok=True)
    written = []
    try:
        for path, payload in zip(target_paths, blobs):
            with path.open("xb") as out:
                out.write(payload)
            written.append(path)
        upsert_indicator_rows(matrix, indicator_id, updated)
    except Exception:
        for p in written:
            p.unlink(missing_ok=True)
        raise
    return len(updated)


def hashes_values_for_draft(hashes: dict) -> tuple[str, str, str]:
    return (
        hashes["data_csv_sha256"],
        hashes["summary_csv_sha256"],
        hashes["destination_csv_sha256"],
    )
