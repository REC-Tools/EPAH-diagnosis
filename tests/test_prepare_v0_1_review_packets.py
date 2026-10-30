"""Synthetic checks: no approval can be generated from QA without exact originals."""
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/prepare_v0_1_review_packets.py"
SPEC = importlib.util.spec_from_file_location("prepare_v0_1_review_packets", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
ROOT = Path(__file__).resolve().parents[1]


def write(path: Path, content: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return hashlib.sha256(content).hexdigest()


def make_case(tmp_path):
    sources = {}
    for name in ("road_zip", "boundaries_zip", "hospitals", "rail_gateways",
                 "registry", "school_registry", "school_pathways"):
        sources[name] = tmp_path / (name + ".dat")
        write(sources[name], (name + "-synthetic").encode())
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["municipality", "istat_code"])
    for i in range(1, 28):
        writer.writerow([f"Test {i}", f"{i:06d}"])
    write(sources["registry"], out.getvalue().encode())
    drafts = {}
    for identifier, config in MODULE.SPECS.items():
        folder = tmp_path / identifier
        drafts[identifier] = folder
        fields = ["municipality_code", "travel_time_minutes"]
        records = io.StringIO()
        writer = csv.writer(records, lineterminator="\n")
        writer.writerow(fields)
        for i in range(1, 28):
            writer.writerow([f"{i:06d}", "25.00"])
        qa = {
            "indicator_id": identifier,
            "qa_status": "technical_checks_only",
            "validated_for_release": False,
            "origin_count": 27,
            "road_graph_year": "2020",
            "service_vintage": "2024/25" if identifier == "upper_secondary_accessibility" else "2026 snapshot, to verify",
            "expected_route_pairs": 54,
            "route_pair_count": 54,
            "complete_route_pairs": 54,
            "eligible_dea_municipality_count": 2,
            "destination_municipality_count": 2,
        }
        for field, filename in config["outputs"].items():
            qa[field] = write(folder / filename, records.getvalue().encode() if field == "data_csv_sha256" else b"a,b\n1,2\n")
        for field, src in {**MODULE.COMMON_HASHES, **config["sources"]}.items():
            qa[field] = MODULE.sha256(sources[src])
        write(folder / config["qa"], json.dumps(qa).encode())
    return drafts, sources


def test_builds_three_pending_approvals_and_nine_pending_methodologies(tmp_path):
    drafts, sources = make_case(tmp_path)
    files = MODULE.build_packets(drafts, sources, ROOT / "config/indicators.json",
                                 ROOT / "config/release_v0_1.json", tmp_path / "new_review")
    assert len(files) == 8
    for filename in ("dea_approval.pending.json", "rail_approval.pending.json", "school_approval.pending.json"):
        item = json.loads(files[filename])
        assert item["decision"] == "pending"
        assert item["reviewed_by"] == item["review_evidence_url"] == ""
        assert item["methodology_scope_decision"] == "pending"
        assert all(value is False for key, value in item.items() if key.endswith("_reviewed"))
    approved = json.loads(files["methodology_reviews.pending.json"])
    assert len(approved["methodology_approvals"]) == 9
    assert all(item["decision"] == "pending" for item in approved["methodology_approvals"])


def test_rejects_modified_original(tmp_path):
    drafts, sources = make_case(tmp_path)
    write(sources["hospitals"], b"tampered")
    with pytest.raises(ValueError, match="SHA mismatch"):
        MODULE.build_packets(drafts, sources, ROOT / "config/indicators.json",
                             ROOT / "config/release_v0_1.json", tmp_path / "new_review")


def test_rejects_missing_municipality(tmp_path):
    drafts, sources = make_case(tmp_path)
    qa_path = drafts["dea_accessibility"] / "dea_accessibility_qa.json"
    qa = json.loads(qa_path.read_text())
    data_path = drafts["dea_accessibility"] / "dea_accessibility_minutes.csv"
    rows = data_path.read_text().splitlines()[:-1]
    qa["data_csv_sha256"] = write(data_path, ("\n".join(rows) + "\n").encode())
    write(qa_path, json.dumps(qa).encode())
    with pytest.raises(ValueError, match="coverage"):
        MODULE.build_packets(drafts, sources, ROOT / "config/indicators.json",
                             ROOT / "config/release_v0_1.json", tmp_path / "new_review")


def test_refuses_overwriting_previous_packet(tmp_path):
    drafts, sources = make_case(tmp_path)
    dst = tmp_path / "already"
    dst.mkdir()
    with pytest.raises(FileExistsError):
        MODULE.build_packets(drafts, sources, ROOT / "config/indicators.json",
                             ROOT / "config/release_v0_1.json", dst)
