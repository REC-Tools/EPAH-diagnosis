"""PR-07 regression tests; all computed service and road values are SYNTHETIC."""
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

from epah_diagnosis.cli import read_municipality_codes
from epah_diagnosis import education_rail_access_qa as qa

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data/municipalities.csv"
CITIES = {"Ivrea": "001925", "Chivasso": "001926", "Rivarolo Canavese": "001927"}


def boundaries_zip(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    base = path.parent / "Com01012026_g"
    with shapefile.Writer(str(base), shapeType=shapefile.POLYGON) as writer:
        writer.field("COMUNE", "C", size=100)
        writer.field("PRO_COM_T", "C", size=6)
        for i, (name, code) in enumerate(
            {**read_municipality_codes(REGISTRY), **CITIES}.items()
        ):
            x, y = 400000 + 200 * i, 5030000
            writer.poly([[[x, y], [x + 100, y], [x + 100, y + 100],
                          [x, y + 100], [x, y]]])
            writer.record(name, code)
    with zipfile.ZipFile(path, "w") as archive:
        for suffix in (".shp", ".shx", ".dbf"):
            f = base.with_suffix(suffix)
            archive.write(f, arcname="municipalities/Com01012026_g" + suffix)


def road_zip(path, destinations, *, skip=None, duplicate=None, corrupt=None):
    text = io.StringIO()
    w = csv.writer(text, delimiter=";")
    w.writerow(["OR_PROCOM", "DEST_PROCOM", "TEP_TOT", "KM_TOT"])
    for i, origin in enumerate(read_municipality_codes(REGISTRY).values()):
        for j, dest in enumerate(destinations):
            pair = (origin, dest)
            if pair == skip:
                continue
            minutes = "NaN" if pair == corrupt else str(15 + i % 10 + j * 8)
            record = [origin, dest, minutes, "19"]
            w.writerow(record)
            if pair == duplicate:
                w.writerow(record)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("R01_TO.csv", text.getvalue())


def school_csvs(registry, pathways):
    with registry.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(["Regione", "CodiceScuola", "DescrizioneComune"])
        for city, key in (("Ivrea", "A"), ("Chivasso", "B")):
            writer.writerow(["PIEMONTE", key + "1", city])
            writer.writerow(["PIEMONTE", key + "2", city])
        writer.writerow(["LOMBARDIA", "LX", "Milano"])
    with pathways.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(["CodiceScuola", "TipoPercorso", "Percorso"])
        for key in ("A", "B"):
            writer.writerow([key + "1", "Liceo", "Scientifico"])
            writer.writerow([key + "2", "Tecnico", "Tecnologico"])
        writer.writerow(["LX", "Liceo", "Classico"])


def rail_csv(path, *, duplicate=False, bad_url=False):
    with path.open("w", encoding="utf-8", newline="") as handle:
        w = csv.DictWriter(handle, fieldnames=[
            "station_name", "municipality", "province", "status",
            "source", "source_url", "notes",
        ])
        w.writeheader()
        w.writerows([
            {"station_name": "Ivrea", "municipality": "Ivrea", "province": "TO",
             "status": "active passenger rail", "source": "RFI",
             "source_url": "bad" if bad_url else "https://example.org/ivrea",
             "notes": "Synthetic station"},
            {"station_name": "Rivarolo", "municipality": "Rivarolo Canavese",
             "province": "TO", "status": "active passenger rail", "source": "RFI",
             "source_url": "https://example.org/rivarolo", "notes": "Synthetic"},
            {"station_name": "Pont", "municipality": "Pont Canavese",
             "province": "TO", "status": "bus substitution", "source": "SFM",
             "source_url": "https://example.org/pont", "notes": "Synthetic bus-only"},
            *([{"station_name": "Ivrea", "municipality": "Ivrea", "province": "TO",
                "status": "active passenger rail", "source": "RFI",
                "source_url": "https://example.org/ivrea", "notes": "Duplicate"}]
              if duplicate else []),
        ])


@pytest.fixture
def sources(tmp_path):
    boundary = tmp_path / "boundary.zip"
    road = tmp_path / "road.zip"
    schools = tmp_path / "schools.csv"
    pathways = tmp_path / "pathways.csv"
    rail = tmp_path / "rail.csv"
    boundaries_zip(boundary)
    school_csvs(schools, pathways)
    rail_csv(rail)
    road_zip(road, [CITIES["Ivrea"], CITIES["Chivasso"], CITIES["Rivarolo Canavese"]])
    return {
        "road_zip": road, "boundaries_zip": boundary, "registry": REGISTRY,
        "school_registry": schools, "school_pathways": pathways,
        "rail_gateways": rail,
    }


def params(sources, kind):
    common = {
        "road_zip": sources["road_zip"],
        "boundaries_zip": sources["boundaries_zip"],
        "registry": sources["registry"],
    }
    if kind == "upper_secondary_accessibility":
        common.update({
            "school_registry": sources["school_registry"],
            "school_pathways": sources["school_pathways"],
            "min_school_registry": 5, "min_school_pathways": 5,
            "min_school_poles": 2,
        })
        # Add one non-pole row to satisfy the explicitly tested synthetic fixture.
        with sources["school_pathways"].open("a", encoding="utf-8") as f:
            f.write("XX;Liceo;Classico\n")
    else:
        common.update({"rail_gateways": sources["rail_gateways"], "min_rail_gateways": 2})
    return common


@pytest.mark.parametrize("kind,expected_destinations", [
    ("upper_secondary_accessibility", 2),
    ("rail_accessibility", 2),
])
def test_27_reproducible_minimum_routes(sources, kind, expected_destinations):
    inputs = params(sources, kind)
    data, summary, destinations, report = qa.prepare(kind, **inputs)
    assert len(data) == report["origin_count"] == 27
    assert report["destination_municipality_count"] == expected_destinations
    assert report["expected_route_pairs"] == 27 * expected_destinations
    assert report["complete_route_pairs"] == 27 * expected_destinations
    assert not report["validated_for_release"]
    assert report["road_zip_sha256"] == hashlib.sha256(
        sources["road_zip"].read_bytes()).hexdigest()
    assert summary[0]["municipality_count"] == "27"
    assert all(float(row["travel_time_minutes"]) >= 0 for row in data)
    assert all(len(row["municipality_code"]) == 6 for row in data)
    assert "Pont Canavese" not in {row["municipality"] for row in destinations}


@pytest.mark.parametrize("kind", sorted(qa.INDICATORS))
def test_incomplete_road_grid_fails_closed(sources, kind):
    inputs = params(sources, kind)
    origin = next(iter(read_municipality_codes(REGISTRY).values()))
    road_zip(sources["road_zip"], list(CITIES.values()),
             skip=(origin, CITIES["Ivrea"]))
    with pytest.raises(ValueError, match="Incomplete DEA route grid"):
        qa.prepare(kind, **inputs)


@pytest.mark.parametrize("kind", sorted(qa.INDICATORS))
def test_duplicate_road_pairs_fail_closed(sources, kind):
    inputs = params(sources, kind)
    origin = next(iter(read_municipality_codes(REGISTRY).values()))
    road_zip(sources["road_zip"], list(CITIES.values()),
             duplicate=(origin, CITIES["Ivrea"]))
    with pytest.raises(ValueError, match="Duplicate route"):
        qa.prepare(kind, **inputs)


@pytest.mark.parametrize("kind", sorted(qa.INDICATORS))
def test_nan_road_minutes_rejected(sources, kind):
    inputs = params(sources, kind)
    origin = next(iter(read_municipality_codes(REGISTRY).values()))
    road_zip(sources["road_zip"], list(CITIES.values()),
             corrupt=(origin, CITIES["Ivrea"]))
    with pytest.raises(ValueError, match="Nonfinite/implausible"):
        qa.prepare(kind, **inputs)


def test_rail_bus_only_and_invalid_source_refused(sources):
    params(sources, "rail_accessibility")
    rail_csv(sources["rail_gateways"], bad_url=True)
    with pytest.raises(ValueError, match="HTTPS"):
        qa.prepare("rail_accessibility", **params(sources, "rail_accessibility"))
    rail_csv(sources["rail_gateways"], duplicate=True)
    with pytest.raises(ValueError, match="Duplicate active"):
        qa.prepare("rail_accessibility", **params(sources, "rail_accessibility"))


def test_school_offer_requires_both_pathway_families(sources):
    p = sources["school_pathways"]
    data = p.read_text(encoding="utf-8").replace("B2;Tecnico;Tecnologico", "B2;Liceo;Scientifico")
    p.write_text(data, encoding="utf-8")
    inputs = params(sources, "upper_secondary_accessibility")
    with pytest.raises(ValueError, match="Too few complete school poles"):
        qa.prepare("upper_secondary_accessibility", **inputs)


@pytest.mark.parametrize("kind", sorted(qa.INDICATORS))
def test_incomplete_service_catalog_rejected_by_default(sources, kind):
    inputs = params(sources, kind)
    for key in ("min_school_registry", "min_school_pathways", "min_school_poles", "min_rail_gateways"):
        inputs.pop(key, None)
    with pytest.raises(ValueError, match="Incomplete MIM|Incomplete rail gateway|Too few"):
        qa.prepare(kind, **inputs)


@pytest.mark.parametrize("kind", sorted(qa.INDICATORS))
def test_draft_checksum_and_no_overwrite(sources, kind, tmp_path):
    inputs = params(sources, kind)
    out = tmp_path / "draft"
    report = qa.write_draft(kind, out_dir=out, **inputs)
    file = out / qa.INDICATORS[kind]["data_name"]
    assert report["data_csv_sha256"] == hashlib.sha256(file.read_bytes()).hexdigest()
    assert report["qa_status"] == "technical_checks_only"
    with pytest.raises(FileExistsError):
        qa.write_draft(kind, out_dir=out, **inputs)


@pytest.mark.parametrize("kind", sorted(qa.INDICATORS))
def test_review_metadata_not_implicitly_trusted(sources, kind, tmp_path):
    inputs = params(sources, kind)
    out = tmp_path / "draft"
    qa.write_draft(kind, out_dir=out, **inputs)
    review = tmp_path / "review.json"
    review.write_text('{"decision": "approved"}', encoding="utf-8")
    matrix = ROOT / "data/verification_matrix.csv"
    before = matrix.read_bytes()
    with pytest.raises(ValueError, match="Review or draft checksum"):
        qa.promote(
            kind, draft_dir=out, approval_file=review,
            matrix=matrix, published_dir=tmp_path / "published",
            **inputs,
        )
    assert matrix.read_bytes() == before


@pytest.mark.parametrize("script", [
    "scripts/finalize_upper_secondary_accessibility.py",
    "scripts/finalize_rail_accessibility.py",
])
def test_finalizer_requires_human_evidence(script):
    matrix = ROOT / "data/verification_matrix.csv"
    before = matrix.read_bytes()
    run = subprocess.run(
        [sys.executable, script], cwd=ROOT, capture_output=True, text=True
    )
    assert run.returncode != 0
    assert "--approval" in run.stderr
    assert matrix.read_bytes() == before


def test_matrix_243_rows_unchanged_and_last_two_indicators_unverified():
    with (ROOT / "data/verification_matrix.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 243
    for indicator in qa.INDICATORS:
        selected = [r for r in rows if r["indicator_id"] == indicator]
        assert len(selected) == 27
        assert all(r["status"] == "Da verificare" and not r["value"] for r in selected)
