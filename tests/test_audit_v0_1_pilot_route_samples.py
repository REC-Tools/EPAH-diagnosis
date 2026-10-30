"""Synthetic, never observational: v0.1 original-road sample audit."""
import csv
import hashlib
import importlib.util
import io
import json
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/audit_v0_1_pilot_route_samples.py"
SPEC = importlib.util.spec_from_file_location("audit_v0_1_pilot_samples", SOURCE)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def make_fixtures(tmp_path, *, bad=False):
    archive = tmp_path / "Piemonte.zip"
    origin_list = [f"{i:06d}" for i in range(1, 25)] + list(MOD.ORIGINS)
    assert len(set(origin_list)) == 27
    with zipfile.ZipFile(archive, "w") as zipped:
        data = io.StringIO()
        writer = csv.writer(data, delimiter=";", lineterminator="\n")
        writer.writerow(["OR_PROCOM", "DEST_PROCOM", "TEP_TOT", "KM_TOT"])
        for origin in MOD.ORIGINS:
            writer.writerow([origin, "001086", 42, 35])
        zipped.writestr("road.csv", data.getvalue())
    road_sha = MOD.sha256(archive)
    drafts = {}
    for kind, (data_name, qa_name, _) in MOD.INPUTS.items():
        folder = tmp_path / kind
        folder.mkdir()
        drafts[kind] = folder
        out = io.StringIO()
        w = csv.DictWriter(out, fieldnames=["municipality", "municipality_code",
                                           "nearest_service_code", "nearest_dea_code",
                                           "travel_time_minutes", "distance_km"],
                           lineterminator="\n")
        w.writeheader()
        for origin in origin_list:
            w.writerow({"municipality": origin, "municipality_code": origin,
                        "nearest_service_code": "001086", "nearest_dea_code": "001086",
                        "travel_time_minutes": "43.00" if bad and origin == MOD.ORIGINS[0] and kind == "dea_accessibility" else "42.00",
                        "distance_km": "35.00"})
        payload = out.getvalue().encode()
        (folder / data_name).write_bytes(payload)
        (folder / qa_name).write_text(json.dumps({
            "indicator_id": kind, "origin_count": 27,
            "qa_status": "technical_checks_only", "validated_for_release": False,
            "road_zip_sha256": road_sha,
            "data_csv_sha256": hashlib.sha256(payload).hexdigest(),
        }), encoding="utf-8")
    return archive, drafts


def test_nine_original_pairs_match(tmp_path):
    archive, drafts = make_fixtures(tmp_path)
    report = MOD.audit(archive, drafts)
    assert report["routes_checked"] == report["matches"] == 9
    assert report["technical_pass"] is True
    assert report["validated_for_release"] is False
    assert all(row["zip_member"] == "road.csv" for row in report["comparisons"])
    assert len({row["origin"] for row in report["comparisons"]}) == 3


def test_incorrect_declared_minutes_not_approved(tmp_path):
    archive, drafts = make_fixtures(tmp_path, bad=True)
    report = MOD.audit(archive, drafts)
    assert report["matches"] == 8
    assert report["technical_pass"] is False
    assert report["human_review_required"] is True


def test_source_sha_change_rejected(tmp_path):
    archive, drafts = make_fixtures(tmp_path)
    with zipfile.ZipFile(archive, "a") as archive_writer:
        archive_writer.writestr("other.txt", "unexpected bytes")
    with pytest.raises(ValueError, match="checksum"):
        MOD.audit(archive, drafts)


def test_duplicate_source_pair_rejected(tmp_path):
    archive, drafts = make_fixtures(tmp_path)
    with zipfile.ZipFile(archive, "w") as writer:
        writer.writestr("road.csv",
                        "OR_PROCOM;DEST_PROCOM;TEP_TOT;KM_TOT\n"
                        "001073;001086;42;35\n001073;001086;42;35\n")
    with pytest.raises(ValueError, match="Duplicate original"):
        MOD.source_route_evidence(archive, {("001073", "001086")})


def test_missing_original_route_gives_blocked_result(tmp_path):
    archive, drafts = make_fixtures(tmp_path)
    with zipfile.ZipFile(archive, "w") as writer:
        writer.writestr("road.csv",
                        "OR_PROCOM;DEST_PROCOM;TEP_TOT;KM_TOT\n"
                        "001073;001086;42;35\n")
    actual = MOD.source_route_evidence(archive, {("001073", "001086"), ("001224", "001086")})
    assert ("001224", "001086") not in actual
