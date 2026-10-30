"""Synthetic fixture tests; no real-world municipality or methodology approval."""
import csv
import hashlib
import importlib.util
import io
import json
import zipfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_accessibility_candidates.py"
SPEC = importlib.util.spec_from_file_location("audit_accessibility_candidates", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def csv_bytes(records):
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=list(records[0]))
    writer.writeheader()
    writer.writerows(records)
    return out.getvalue().encode()


def make_fixture(root):
    codes = [f"001{i:03d}" for i in range(1, 28)]
    registry = csv_bytes([{"municipality": f"Synthetic {i}", "istat_code": code} for i, code in enumerate(codes)])
    intake = {
        "road": {"status": "technical_preflight_pass", "technical_preflight_passed": True, "sha256": "a" * 64},
        "boundaries": {"status": "technical_preflight_pass", "technical_preflight_passed": True, "sha256": "b" * 64},
    }
    schools = {
        "school_registry": {"status": "technical_preflight_pass", "technical_preflight_passed": True, "sha256": "c" * 64},
        "school_pathways": {"status": "technical_preflight_pass", "technical_preflight_passed": True, "sha256": "d" * 64},
    }

    def save(path, contents):
        file = root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(contents)

    save("access_inputs_manual_v01/audit.json", json.dumps({"original_source_results": intake}).encode())
    save("access_inputs_mim_202425/audit.json", json.dumps({"original_source_results": schools}).encode())
    for indicator, (folder, datafile, qafile, _, dest_col) in MODULE.INDICATORS.items():
        rows = [{"municipality_code": code, dest_col: "001100", "travel_time_minutes": "20", "distance_km": "12"} for code in codes]
        data = csv_bytes(rows)
        summary = csv_bytes([{"total": 27}])
        save(f"{folder}/{datafile}", data)
        save(f"{folder}/{indicator}_summary.csv", summary)
        qa = {"indicator_id": indicator, "origin_count": 27, "qa_status": "technical_checks_only", "validated_for_release": False,
              "data_csv_sha256": hashlib.sha256(data).hexdigest(), "summary_csv_sha256": hashlib.sha256(summary).hexdigest(),
              "road_zip_sha256": "a" * 64, "boundaries_zip_sha256": "b" * 64,
              "expected_route_pairs": 27, "source_authenticity_reviewed": False}
        if indicator == "dea_accessibility":
            qa.update(eligible_dea_municipality_count=1, route_pair_count=27)
        else:
            qa.update(destination_municipality_count=1, complete_route_pairs=27)
            dest_name = MODULE.DESTINATIONS[indicator][0]
            destination = csv_bytes([{"municipality_code": "001100"}])
            save(f"{folder}/{dest_name}", destination)
            qa["destination_csv_sha256"] = hashlib.sha256(destination).hexdigest()
        if indicator == "upper_secondary_accessibility":
            qa["school_registry_sha256"] = "c" * 64
            qa["school_pathways_sha256"] = "d" * 64
        save(f"{folder}/{qafile}", json.dumps(qa).encode())
    return registry


def test_valid_synthetic_fixture(tmp_path):
    registry = make_fixture(tmp_path)
    report = MODULE.evaluate(MODULE.QualityFiles(directory=tmp_path), registry)
    assert report["technical_integrity_pass"] is True
    assert report["school_rail_identical_triples"] == 27
    assert report["release_authorized"] is False
    assert report["human_review_required"] is True


def test_mutated_data_fails_sha(tmp_path):
    registry = make_fixture(tmp_path)
    path = tmp_path / "rail_accessibility_v01/rail_accessibility_minutes.csv"
    path.write_bytes(path.read_bytes().replace(b"20,12", b"21,12", 1))
    report = MODULE.evaluate(MODULE.QualityFiles(directory=tmp_path), registry)
    assert report["technical_integrity_pass"] is False
    assert any("SHA-256 inconsistent" in x for x in report["technical_blockers"])


def test_missing_origin_fails_coverage_even_if_hash_updated(tmp_path):
    registry = make_fixture(tmp_path)
    folder = tmp_path / "upper_secondary_accessibility_v01"
    path = folder / "upper_secondary_accessibility_minutes.csv"
    rows = list(csv.DictReader(io.StringIO(path.read_text())))[:-1]
    new = csv_bytes(rows)
    path.write_bytes(new)
    qa = folder / "upper_secondary_accessibility_qa.json"
    obj = json.loads(qa.read_text())
    obj["data_csv_sha256"] = hashlib.sha256(new).hexdigest()
    qa.write_text(json.dumps(obj))
    report = MODULE.evaluate(MODULE.QualityFiles(directory=tmp_path), registry)
    assert any("origins do not match" in x for x in report["technical_blockers"])


def test_zip_and_directory_agree(tmp_path):
    registry = make_fixture(tmp_path)
    archive = tmp_path.parent / "synthetic_quality.zip"
    with zipfile.ZipFile(archive, "w") as out:
        for file in tmp_path.rglob("*"):
            if file.is_file():
                out.write(file, "quality/" + str(file.relative_to(tmp_path)))
    direct = MODULE.evaluate(MODULE.QualityFiles(directory=tmp_path), registry)
    zipped = MODULE.evaluate(MODULE.QualityFiles(archive=archive), registry)
    assert direct == zipped
