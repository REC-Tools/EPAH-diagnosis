"""QA-first road accessibility to a curated list of Piemonte DEA I/II hospitals.

Technical validity is not source authenticity or proof of the 2025 DEA network.
Routes are municipality-centroid-to-municipality-centroid ISTAT 2021 proxies,
not household-to-hospital or ambulance travel times.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
import statistics
import zipfile
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from epah_diagnosis.cli import read_municipality_codes
from epah_diagnosis.geography import parse_boundaries_zip
from epah_diagnosis.matrix_update import upsert_indicator_rows
from epah_diagnosis.service_access import (
    PIEMONTE_DISTANCE_MATRIX_URL, _as_float, _detect_delimiter,
    _matrix_columns, normalize_text,
)

INDICATOR_ID = "dea_accessibility"
SOURCE_ISTAT = "https://www.istat.it/notizia/matrici-di-contiguita-distanza-e-pendolarismo/"
SOURCE_HEALTH = "https://www.salute.gov.it/new/it/banche-dati/elenco-strutture-della-rete-dellemergenza-ospedaliera/"
ROAD_YEAR = "2021"
ROAD_GRAPH_YEAR = "2020"
HEALTH_BASELINE = "2025"
DATA_COLUMNS = [
    "municipality", "municipality_code", "nearest_dea_municipality",
    "nearest_dea_code", "dea_hospital_names", "dea_levels",
    "travel_time_minutes", "distance_km", "road_matrix_geography",
    "road_graph_year", "hospital_reference_years", "source_url_istat",
    "source_url_health", "limitations",
]
SUMMARY_COLUMNS = [
    "territory", "municipality_count", "mean_minutes", "median_minutes",
    "min_minutes", "max_minutes", "municipalities_over_30_min",
    "municipalities_over_40_min", "eligible_dea_municipalities",
    "hospital_reference_years", "method",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as data:
        for chunk in iter(lambda: data.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def csv_bytes(fields: list[str], rows: list[dict]) -> bytes:
    f = io.StringIO(newline="")
    writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return f.getvalue().encode("utf-8")


def _valid_code(value: object) -> str:
    txt = str(value or "").strip()
    if not txt.isdigit() or not 1 <= len(txt) <= 6:
        return ""
    return txt.zfill(6)


def read_dea_hospitals(path: Path, *, min_facilities: int = 20) -> tuple[list[dict], set[str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"hospital_name", "municipality", "dea_level", "reference_year", "source"}
        if not reader.fieldnames or not required <= set(reader.fieldnames):
            raise ValueError("Hospital reference missing required columns")
        rows = list(reader)
    if len(rows) < min_facilities:
        raise ValueError(f"DEA facility list too short: {len(rows)} < {min_facilities}")
    normalized = set()
    years = set()
    for row in rows:
        if not all((row[field] or "").strip() for field in required):
            raise ValueError("DEA facility has missing name, municipality, level, year or source")
        if row["dea_level"].strip() not in {"I", "II"}:
            raise ValueError(f"Non-DEA destination is in eligibility list: {row['hospital_name']}")
        if not re.fullmatch(r"20\d{2}", row["reference_year"].strip()):
            raise ValueError("Invalid DEA snapshot reference year")
        year = int(row["reference_year"])
        if year > 2025 or year < 2014:
            raise ValueError("DEA snapshot reference year outside documented 2014-2025 range")
        key = (normalize_text(row["hospital_name"]), normalize_text(row["municipality"]))
        if key in normalized:
            raise ValueError(f"Duplicate DEA facility {row['hospital_name']}")
        normalized.add(key)
        years.add(row["reference_year"].strip())
    return rows, years


def resolve_codes(boundaries_zip: Path, targets: dict[str, str], hospitals: list[dict]) -> dict[str, str]:
    """Resolve hospital municipalities from ISTAT boundaries and compare target IDs.

    Hospital names are only for display; the route join uses six-digit codes.
    The 2026-to-2021 code crosswalk still requires human historical review.
    """
    names = set(targets) | {h["municipality"].strip() for h in hospitals}
    boundaries = parse_boundaries_zip(boundaries_zip.read_bytes(), names)
    found = {}
    for feature in boundaries["features"]:
        props = feature["properties"]
        name = props["municipality"]
        code = props["municipality_code"]
        key = normalize_text(name)
        if key in found and found[key] != code:
            raise ValueError(f"Conflicting official municipality codes for {name}")
        found[key] = code
    if len(found) != len({normalize_text(n) for n in names}):
        raise ValueError("Official municipality boundaries have incomplete target/DEA coverage")
    for name, code in targets.items():
        if found.get(normalize_text(name)) != code:
            raise ValueError(f"Registry 2026 code and official boundaries disagree for {name}")
    return found


def read_routes(road_zip: Path, origins: dict[str, str], destinations: dict[str, str],
                *, require_complete: bool = True) -> tuple[dict[str, tuple], int]:
    """Single streaming pass; every relevant origin x DEA destination must be present.

    No negative/NaN times, duplicate pairs, missing routes or incomplete subsets
    can silently produce an optimistic minimum travel time.
    """
    if not origins or not destinations:
        raise ValueError("Origin and destination code maps cannot be empty")
    seen: set[tuple[str, str]] = set()
    best: dict[str, tuple] = {}
    valid_schema = False
    schema_errors = []
    with zipfile.ZipFile(road_zip) as archive:
        csv_names = sorted(n for n in archive.namelist() if n.lower().endswith(".csv"))
        if not csv_names:
            raise ValueError("ISTAT road ZIP has no CSV members")
        for member in csv_names:
            with archive.open(member) as raw:
                f = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace", newline="")
                sample = f.read(8192)
                delim = _detect_delimiter(sample)
                f.seek(0)
                reader = csv.DictReader(f, delimiter=delim)
                if not reader.fieldnames:
                    continue
                try:
                    cols = _matrix_columns(reader.fieldnames)
                except ValueError as exc:
                    schema_errors.append(f"{member}: {exc}")
                    continue
                valid_schema = True
                for row in reader:
                    origin = _valid_code(row.get(cols["origin_code"]))
                    if origin not in origins:
                        continue
                    dest = _valid_code(row.get(cols["destination_code"]))
                    if dest not in destinations:
                        continue
                    pair = (origin, dest)
                    if pair in seen:
                        raise ValueError(f"Duplicate route {origin}->{dest}")
                    seen.add(pair)
                    try:
                        minutes = _as_float(row.get(cols["time"]))
                        km = _as_float(row.get(cols["distance"])) if "distance" in cols else None
                    except (TypeError, ValueError) as exc:
                        raise ValueError(f"Invalid ISTAT TEP_TOT/KM_TOT for {origin}->{dest}") from exc
                    if not math.isfinite(minutes) or not 0 <= minutes <= 1440:
                        raise ValueError(f"Nonfinite/implausible road minutes for {origin}->{dest}")
                    if km is not None and (not math.isfinite(km) or not 0 <= km <= 3000):
                        raise ValueError(f"Nonfinite/implausible distance for {origin}->{dest}")
                    candidate = (minutes, dest, km)
                    previous = best.get(origin)
                    if previous is None or (minutes, dest) < (previous[0], previous[1]):
                        best[origin] = candidate
    if not valid_schema:
        raise ValueError("No usable ISTAT road schema: " + "; ".join(schema_errors[:4]))
    if require_complete:
        expected = len(origins) * len(destinations)
        if len(seen) != expected:
            missing = sorted((o, d) for o in origins for d in destinations if (o, d) not in seen)
            raise ValueError(f"Incomplete DEA route grid: {len(seen)}/{expected}; sample {missing[:5]}")
    if set(best) != set(origins):
        raise ValueError("Missing nearest DEA for origin codes: " + str(sorted(set(origins) - set(best))))
    return best, len(seen)


def prepare(road_zip: Path, boundaries_zip: Path, hospitals_csv: Path,
            registry_csv: Path, *, min_facilities: int = 20) -> tuple[list[dict], list[dict], dict]:
    """Compute technical draft (27 cities), never promote matrix or invent approvals."""
    targets = read_municipality_codes(registry_csv)
    if len(targets) != 27:
        raise ValueError("DEA diagnosis must cover exactly 27 municipalities")
    hospitals, reference_years = read_dea_hospitals(hospitals_csv, min_facilities=min_facilities)
    codes = resolve_codes(boundaries_zip, targets, hospitals)
    sites = {}
    for h in hospitals:
        city = h["municipality"].strip()
        code = codes[normalize_text(city)]
        sites.setdefault(code, []).append(h)
    destination_names = {code: sorted({h["municipality"].strip() for h in hs})[0]
                         for code, hs in sites.items()}
    origins = {code: name for name, code in targets.items()}
    best, pair_count = read_routes(road_zip, origins, destination_names)

    lines = []
    limitations = (
        "Road time between ISTAT municipal reference points, not the hospital door; "
        "road network 2020, municipality geography 2021. Destination list is "
        "Piemonte-only destination list, reference years " + " / ".join(sorted(reference_years))
        + "; cross-region DEA facilities and current network changes are not yet "
        "independently reviewed."
    )
    for name, code in targets.items():
        minutes, dest, km = best[code]
        hospital_names = sorted({h["hospital_name"].strip() for h in sites[dest]})
        levels = sorted({h["dea_level"].strip() for h in sites[dest]})
        lines.append({
            "municipality": name,
            "municipality_code": code,
            "nearest_dea_municipality": destination_names[dest],
            "nearest_dea_code": dest,
            "dea_hospital_names": " | ".join(hospital_names),
            "dea_levels": " / ".join(levels),
            "travel_time_minutes": f"{minutes:.2f}",
            "distance_km": "" if km is None else f"{km:.2f}",
            "road_matrix_geography": ROAD_YEAR,
            "road_graph_year": ROAD_GRAPH_YEAR,
            "hospital_reference_years": " / ".join(sorted(reference_years)),
            "source_url_istat": SOURCE_ISTAT,
            "source_url_health": SOURCE_HEALTH,
            "limitations": limitations,
        })
    values = [float(x["travel_time_minutes"]) for x in lines]
    summary = [{
        "territory": "Green Community Sinergie in Canavese",
        "municipality_count": "27",
        "mean_minutes": f"{statistics.mean(values):.2f}",
        "median_minutes": f"{statistics.median(values):.2f}",
        "min_minutes": f"{min(values):.2f}",
        "max_minutes": f"{max(values):.2f}",
        "municipalities_over_30_min": str(sum(v > 30 for v in values)),
        "municipalities_over_40_min": str(sum(v > 40 for v in values)),
        "eligible_dea_municipalities": str(len(sites)),
        "hospital_reference_years": " / ".join(sorted(reference_years)),
        "method": "Minimum finite TEP_TOT among listed Piemonte DEA I/II host municipalities",
    }]
    qa = {
        "schema_version": "1.0",
        "indicator_id": INDICATOR_ID,
        "reference_year": ROAD_YEAR,
        "road_graph_year": ROAD_GRAPH_YEAR,
        "road_matrix_url": PIEMONTE_DISTANCE_MATRIX_URL,
        "hospital_source_url": SOURCE_HEALTH,
        "hospital_snapshot_reference_years": sorted(reference_years),
        "hospital_scope": "Piemonte only; candidate DEA I/II hospital network not independently certified",
        "route_pair_count": pair_count,
        "expected_route_pairs": len(origins) * len(sites),
        "origin_count": len(origins),
        "hospital_facility_count": len(hospitals),
        "eligible_dea_municipality_count": len(sites),
        "road_zip_sha256": sha256(road_zip),
        "boundaries_zip_sha256": sha256(boundaries_zip),
        "hospitals_csv_sha256": sha256(hospitals_csv),
        "registry_csv_sha256": sha256(registry_csv),
        "checks": [
            "27 unique ISTAT origin municipality codes",
            "curated DEA I/II only (not Pronto Soccorso)",
            "official boundaries join; 2021-2026 vintage crosswalk pending approval",
            "complete directed origin x candidate DEA matrix, without duplicate or invalid routes",
            "minimum finite non-negative modelled road time for each origin",
            "non-population-weighted descriptive statistics",
        ],
        "source_authenticity_reviewed": False,
        "national_2025_dea_network_reviewed": False,
        "cross_region_eligibility_reviewed": False,
        "historical_code_crosswalk_reviewed": False,
        "license_reviewed": False,
        "independent_route_sample_reviewed": False,
        "qa_status": "technical_checks_only",
        "validated_for_release": False,
    }
    return lines, summary, qa


def write_draft(road_zip: Path, boundaries_zip: Path, hospitals_csv: Path,
                registry_csv: Path, output_dir: Path, *, min_facilities: int = 20) -> dict:
    targets = [
        output_dir / "dea_accessibility_minutes.csv",
        output_dir / "dea_accessibility_summary.csv",
        output_dir / "dea_accessibility_qa.json",
    ]
    source_paths = {p.resolve() for p in (road_zip, boundaries_zip, hospitals_csv, registry_csv)}
    if any(p.resolve() in source_paths for p in targets):
        raise ValueError("Output cannot overwrite a source file")
    if any(p.exists() for p in targets):
        raise FileExistsError("DEA draft output exists; use a fresh directory")
    lines, summary, qa = prepare(road_zip, boundaries_zip, hospitals_csv, registry_csv,
                                 min_facilities=min_facilities)
    a = csv_bytes(DATA_COLUMNS, lines)
    b = csv_bytes(SUMMARY_COLUMNS, summary)
    qa["data_csv_sha256"] = hashlib.sha256(a).hexdigest()
    qa["summary_csv_sha256"] = hashlib.sha256(b).hexdigest()
    c = (json.dumps(qa, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    try:
        for path, payload in zip(targets, (a, b, c)):
            with path.open("xb") as f:
                f.write(payload)
            written.append(path)
    except Exception:
        for path in written:
            path.unlink(missing_ok=True)
        raise
    return qa


def _valid_date(x: object) -> bool:
    if not isinstance(x, str):
        return False
    try:
        d = date.fromisoformat(x)
        return d.isoformat() == x and d <= date.today()
    except ValueError:
        return False


def _valid_url(x: object) -> bool:
    if not isinstance(x, str):
        return False
    try:
        p = urlsplit(x)
        return p.scheme == "https" and bool(p.netloc)
    except ValueError:
        return False


def promote(road_zip: Path, boundaries_zip: Path, hospitals_csv: Path,
            registry_csv: Path, draft_dir: Path, approval_path: Path,
            matrix_file: Path, indicators_dir: Path, *, min_facilities: int = 20) -> int:
    """Promote the limited Piemonte destination proxy after genuine human review.

    Only the 27 Green Community origin municipalities are the study area.
    Exhaustive nationwide nearest-DEA coverage is not a v0.1 claim.
    JSON fields cannot authenticate a person.
    """
    qa = json.loads((draft_dir / "dea_accessibility_qa.json").read_text(encoding="utf-8"))
    review = json.loads(approval_path.read_text(encoding="utf-8"))
    draft_data = draft_dir / "dea_accessibility_minutes.csv"
    draft_summary = draft_dir / "dea_accessibility_summary.csv"
    hashes = {
        "road_zip_sha256": sha256(road_zip),
        "boundaries_zip_sha256": sha256(boundaries_zip),
        "hospitals_csv_sha256": sha256(hospitals_csv),
        "registry_csv_sha256": sha256(registry_csv),
        "data_csv_sha256": sha256(draft_data),
        "summary_csv_sha256": sha256(draft_summary),
    }
    expected = {
        "indicator_id": INDICATOR_ID, "reference_year": ROAD_YEAR,
        "road_graph_year": ROAD_GRAPH_YEAR, **hashes,
    }
    for key, value in expected.items():
        if qa.get(key) != value or review.get(key) != value:
            raise ValueError(f"QA/review metadata or input bytes mismatch: {key}")
    if review.get("decision") != "approved":
        raise ValueError("Explicit approval is required")
    if not (isinstance(review.get("reviewed_by"), str) and review["reviewed_by"].strip()):
        raise ValueError("Named human reviewer required")
    if not _valid_date(review.get("reviewed_on")) or not _valid_url(review.get("review_evidence_url")):
        raise ValueError("Valid review date and durable HTTPS evidence required")
    if not isinstance(review.get("review_notes"), str) or not review["review_notes"].strip():
        raise ValueError("Detailed scientific review notes required")
    # Pilot v0.1: selected Piemonte DEA I/II reference; full nationwide
    # and out-of-region alternatives are deferred to v0.2, NOT certified.
    for field in (
        "source_authenticity_reviewed", "historical_code_crosswalk_reviewed",
        "license_reviewed", "independent_route_sample_reviewed",
    ):
        if review.get(field) is not True:
            raise ValueError(f"Independent human verification not attested: {field}")
    if review.get("methodology_scope_decision") != "piemonte_dea_proxy_approved_with_limits":
        raise ValueError("Human review must explicitly approve limited Piemonte DEA proxy")

    lines, summary, recalculated = prepare(
        road_zip, boundaries_zip, hospitals_csv, registry_csv, min_facilities=min_facilities,
    )
    if (sha256(draft_data) != hashlib.sha256(csv_bytes(DATA_COLUMNS, lines)).hexdigest() or
        sha256(draft_summary) != hashlib.sha256(csv_bytes(SUMMARY_COLUMNS, summary)).hexdigest() or
        recalculated["expected_route_pairs"] != qa.get("expected_route_pairs")):
        raise ValueError("Prepared DEA output differs from recomputed original source")
    with matrix_file.open(encoding="utf-8", newline="") as f:
        current = list(csv.DictReader(f))
    previous = [r for r in current if r["indicator_id"] == INDICATOR_ID]
    if len(previous) != 27 or len({r["municipality"] for r in previous}) != 27:
        raise ValueError("Verification matrix must have 27 distinct DEA rows")
    by_name = {r["municipality"]: r for r in lines}
    if set(by_name) != {r["municipality"] for r in previous}:
        raise ValueError("DEA municipality names do not match existing matrix")
    updates = []
    for old in previous:
        rec = by_name[old["municipality"]]
        row = dict(old)
        row.update({
            "status": "Dato validato",
            "year": ROAD_YEAR,
            "territorial_level": "Comune",
            "unit": "minuti",
            "source_url": SOURCE_ISTAT,
            "value": rec["travel_time_minutes"],
            "quality": "ISTAT TEP_TOT 2021; human-reviewed curated Piemonte DEA destination proxy",
            "limitations": rec["limitations"],
            "notes": (
                f"Piemonte DEA: {rec['nearest_dea_municipality']} "
                f"(ISTAT {rec['nearest_dea_code']}); review: {review['review_evidence_url']}"
            ),
        })
        updates.append(row)
    destinations = [
        indicators_dir / "dea_accessibility_minutes.csv",
        indicators_dir / "dea_accessibility_summary.csv",
    ]
    if any(p.exists() for p in destinations):
        raise FileExistsError("Published DEA indicator output already exists")
    indicators_dir.mkdir(parents=True, exist_ok=True)
    written = []
    try:
        for src, dst in zip((draft_data, draft_summary), destinations):
            with dst.open("xb") as f:
                f.write(src.read_bytes())
            written.append(dst)
        upsert_indicator_rows(matrix_file, INDICATOR_ID, updates)
    except Exception:
        for p in written:
            p.unlink(missing_ok=True)
        raise
    return len(updates)
