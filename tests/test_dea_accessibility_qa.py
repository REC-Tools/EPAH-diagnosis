"""PR-06: DEA I/II route-grid audit, hospital eligibility and promotion barriers.

All sources in this module are SYNTHETIC. No claim about actual Piemonte
hospital classifications or observed accessibility is made by these tests.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
import shapefile

from epah_diagnosis import dea_accessibility_qa as qa
from epah_diagnosis.cli import read_municipality_codes

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data/municipalities.csv"
HOSPITAL_CODES = {"Ivrea": "001125", "Chivasso": "001081"}


def build_boundaries(path: Path, *, mismatch=False):
    """Tiny UTM32 shape archive with authoritative-looking, synthetic attributes."""
    root = path.parent / "Com01012026_g"
    root.mkdir(exist_ok=True)
    stem = root / "Com01012026_g"
    with shapefile.Writer(str(stem), shapeType=shapefile.POLYGON) as writer:
        writer.field("COMUNE", "C", size=90)
        writer.field("PRO_COM_T", "C", size=6)
        names = {**read_municipality_codes(REGISTRY), **HOSPITAL_CODES}
        for index, (name, code) in enumerate(names.items()):
            if mismatch and name == "Alpette":
                code = "001999"
            x = 400000 + 200 * index
            y = 5030000
            writer.poly([[[x, y], [x, y + 100], [x + 100, y + 100], [x + 100, y], [x, y]]])
            writer.record(name, code)
    with zipfile.ZipFile(path, "w") as z:
        for suffix in (".shp", ".shx", ".dbf"):
            source = stem.with_suffix(suffix)
            z.write(source, arcname="Generalizzati/Com01012026_g" + suffix)


def build_hospitals(path: Path, *, extra=None):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "hospital_name", "municipality", "dea_level", "reference_year", "source",
        ])
        writer.writeheader()
        writer.writerows([
            {"hospital_name": "Hospital A", "municipality": "Ivrea",
             "dea_level": "I", "reference_year": "2023", "source": "synthetic fixture"},
            {"hospital_name": "Hospital B", "municipality": "Chivasso",
             "dea_level": "II", "reference_year": "2025", "source": "synthetic fixture"},
            *(extra or []),
        ])


def build_road(path: Path, *, omit=None, duplicate=None, corrupted=None):
    lines = io.StringIO()
    writer = csv.writer(lines, delimiter=";")
    writer.writerow(["OR_PROCOM", "DEST_PROCOM", "TEP_TOT", "KM_TOT"])
    codes = list(read_municipality_codes(REGISTRY).values())
    for i, origin in enumerate(codes):
        for j, dest in enumerate(HOSPITAL_CODES.values()):
            if (origin, dest) == omit:
                continue
            time = 10 + (i % 10) + (20 if j == 0 else 0)
            km = time * 1.1
            if (origin, dest) == corrupted:
                time = "NaN"
            record = [origin, dest, time, km]
            writer.writerow(record)
            if (origin, dest) == duplicate:
                writer.writerow(record)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("R01_TO.csv", lines.getvalue())


@pytest.fixture
def sources(tmp_path):
    road = tmp_path / "Piemonte.zip"
    boundaries = tmp_path / "Limiti01012026_g.zip"
    hospitals = tmp_path / "piemonte_dea_hospitals.csv"
    build_road(road)
    build_boundaries(boundaries)
    build_hospitals(hospitals)
    return road, boundaries, hospitals


def test_complete_synthetic_27_by_two_dea_routes(sources):
    road, boundaries, hospitals = sources
    rows, summary, report = qa.prepare(
        road, boundaries, hospitals, REGISTRY, min_facilities=2
    )
    assert len(rows) == 27
    assert report["route_pair_count"] == report["expected_route_pairs"] == 54
    assert report["origin_count"] == 27
    assert report["hospital_facility_count"] == 2
    assert report["validated_for_release"] is False
    assert report["national_2025_dea_network_reviewed"] is False
    assert report["road_zip_sha256"] == hashlib.sha256(road.read_bytes()).hexdigest()
    assert all(r["nearest_dea_municipality"] == "Chivasso" for r in rows)
    assert all(float(r["travel_time_minutes"]) >= 0 for r in rows)
    assert summary[0]["municipality_count"] == "27"
    assert "Piemonte DEA" in summary[0]["method"]
    assert rows[0]["road_graph_year"] == "2020"
    assert rows[0]["road_matrix_geography"] == "2021"


def test_network_must_reject_non_dea_emergency_service(sources):
    _, _, hospitals = sources
    build_hospitals(hospitals, extra=[{
        "hospital_name": "Cuorgne PS", "municipality": "Cuorgne",
        "dea_level": "PS", "reference_year": "2025", "source": "synthetic",
    }])
    with pytest.raises(ValueError, match="Non-DEA"):
        qa.read_dea_hospitals(hospitals, min_facilities=2)


def test_hospital_duplicate_rejected(sources):
    _, _, hospitals = sources
    extra = [{
        "hospital_name": "Hospital A", "municipality": "Ivrea",
        "dea_level": "I", "reference_year": "2023", "source": "duplicate",
    }]
    build_hospitals(hospitals, extra=extra)
    with pytest.raises(ValueError, match="Duplicate DEA"):
        qa.read_dea_hospitals(hospitals, min_facilities=2)


def test_original_curated_network_has_only_dea_levels_and_mixed_years():
    path = ROOT / "data/reference/piemonte_dea_hospitals.csv"
    hospitals, years = qa.read_dea_hospitals(path)
    assert len(hospitals) >= 20
    assert years == {"2023", "2025"}
    assert "cuorgne" not in {qa.normalize_text(h["municipality"]) for h in hospitals}


def test_2026_boundary_code_crosswalk_rejected_when_mismatch(sources, tmp_path):
    road, _, hospitals = sources
    bad = tmp_path / "different_boundaries.zip"
    build_boundaries(bad, mismatch=True)
    with pytest.raises(ValueError, match="Registry 2026 code"):
        qa.prepare(road, bad, hospitals, REGISTRY, min_facilities=2)


def test_partial_route_grid_fails_closed(sources):
    road, boundaries, hospitals = sources
    first = next(iter(read_municipality_codes(REGISTRY).values()))
    build_road(road, omit=(first, HOSPITAL_CODES["Ivrea"]))
    with pytest.raises(ValueError, match="Incomplete DEA route grid"):
        qa.prepare(road, boundaries, hospitals, REGISTRY, min_facilities=2)


def test_duplicate_route_pair_fails_closed(sources):
    road, boundaries, hospitals = sources
    first = next(iter(read_municipality_codes(REGISTRY).values()))
    build_road(road, duplicate=(first, HOSPITAL_CODES["Ivrea"]))
    with pytest.raises(ValueError, match="Duplicate route"):
        qa.prepare(road, boundaries, hospitals, REGISTRY, min_facilities=2)


def test_nan_time_fails_closed(sources):
    road, boundaries, hospitals = sources
    first = next(iter(read_municipality_codes(REGISTRY).values()))
    build_road(road, corrupted=(first, HOSPITAL_CODES["Ivrea"]))
    with pytest.raises(ValueError, match="Nonfinite/implausible"):
        qa.prepare(road, boundaries, hospitals, REGISTRY, min_facilities=2)


def test_hospital_list_incomplete_by_default(sources):
    road, boundaries, hospitals = sources
    with pytest.raises(ValueError, match="too short"):
        qa.prepare(road, boundaries, hospitals, REGISTRY)


def test_draft_is_hashed_and_cannot_overwrite(sources, tmp_path):
    road, boundaries, hospitals = sources
    out = tmp_path / "draft"
    result = qa.write_draft(road, boundaries, hospitals, REGISTRY, out, min_facilities=2)
    data = (out / "dea_accessibility_minutes.csv").read_bytes()
    assert result["data_csv_sha256"] == hashlib.sha256(data).hexdigest()
    before = data
    with pytest.raises(FileExistsError):
        qa.write_draft(road, boundaries, hospitals, REGISTRY, out, min_facilities=2)
    assert (out / "dea_accessibility_minutes.csv").read_bytes() == before


def test_promotion_refuses_fake_or_incomplete_review(sources, tmp_path):
    road, boundaries, hospitals = sources
    out = tmp_path / "draft"
    qa.write_draft(road, boundaries, hospitals, REGISTRY, out, min_facilities=2)
    evidence = tmp_path / "approval.json"
    evidence.write_text('{"decision":"approved"}', encoding="utf-8")
    output = tmp_path / "published"
    matrix = ROOT / "data/verification_matrix.csv"
    original = matrix.read_bytes()
    with pytest.raises(ValueError, match="metadata"):
        qa.promote(road, boundaries, hospitals, REGISTRY, out, evidence, matrix,
                   output, min_facilities=2)
    assert matrix.read_bytes() == original
    assert not output.exists()


def test_promotion_refuses_false_required_human_checks(sources, tmp_path):
    road, boundaries, hospitals = sources
    out = tmp_path / "draft"
    report = qa.write_draft(road, boundaries, hospitals, REGISTRY, out, min_facilities=2)
    review = {
        "indicator_id": "dea_accessibility", "reference_year": "2021",
        "road_graph_year": "2020",
        **{k: report[k] for k in (
            "road_zip_sha256", "boundaries_zip_sha256", "hospitals_csv_sha256",
            "registry_csv_sha256", "data_csv_sha256", "summary_csv_sha256",
        )},
        "decision": "approved", "reviewed_by": "Synthetic reviewer - TEST ONLY",
        "reviewed_on": "2026-10-29",
        "review_evidence_url": "https://example.org/synthetic-evidence",
        "review_notes": "Synthetic test fixture; not an actual scientific approval",
        "methodology_scope_decision": "piemonte_dea_proxy_approved_with_limits",
    }
    evidence = tmp_path / "review.json"
    evidence.write_text(json.dumps(review), encoding="utf-8")
    with pytest.raises(ValueError, match="human verification"):
        qa.promote(road, boundaries, hospitals, REGISTRY, out, evidence,
                   ROOT / "data/verification_matrix.csv", tmp_path / "published", min_facilities=2)


def test_finalizer_requires_approval_and_never_changes_existing_matrix():
    matrix = ROOT / "data/verification_matrix.csv"
    original = matrix.read_bytes()
    result = subprocess.run(
        [sys.executable, "scripts/finalize_dea_accessibility.py"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0
    assert "--approval" in result.stderr
    assert matrix.read_bytes() == original


def test_existing_matrix_contains_27_unverified_dea_rows():
    with (ROOT / "data/verification_matrix.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    selected = [r for r in rows if r["indicator_id"] == "dea_accessibility"]
    assert len(rows) == 243 and len(selected) == 27
    assert all(row["status"] == "Da verificare" and not row["value"] for row in selected)
