import hashlib
import json

import pytest

from epah_diagnosis.provenance import build_manifest, sha256_file


def fixture(tmp_path):
    catalog = tmp_path / "indicators.json"
    sources = tmp_path / "sources.json"
    artifact = tmp_path / "actual.csv"
    input_file = tmp_path / "original.zip"
    catalog.write_text(
        json.dumps({"indicators": [
            {"id": "test_indicator", "source_ids": ["source_a", "source_b"]}
        ]}), encoding="utf-8"
    )
    sources.write_text(
        json.dumps({"sources": [
            {"id": "source_a", "landing_url": "https://example.org/a",
             "data_url": "https://example.org/a.zip", "reference_year": 2024,
             "license_status": "to_verify"},
            {"id": "source_b", "landing_url": "https://example.org/b",
             "data_url": "https://example.org/b.csv", "reference_year": 2021}
        ]}), encoding="utf-8"
    )
    artifact.write_bytes(b"municipality,value\nA,100\n")
    input_file.write_bytes(b"\x00\xFFtest")
    return catalog, sources, artifact, input_file


def test_manifest_hashes_real_bytes_and_does_not_claim_validation(tmp_path):
    catalog, sources, artifact, input_file = fixture(tmp_path)
    result = build_manifest(
        artifact, "test_indicator", catalog, sources, reference_year="2024",
        source_files={"source_a": input_file}, git_commit="abc123",
        entrypoint="scripts/example.py",
    )
    assert result["artifact"]["sha256"] == hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert result["sources"][0]["source_file_sha256"] == hashlib.sha256(input_file.read_bytes()).hexdigest()
    assert result["sources"][1]["source_file_sha256"] is None
    assert result["sources"][0]["license_status"] == "to_verify"
    assert result["sources"][0]["retrieved_at"] is None
    assert result["quality"]["qa_result"] == "not_assessed"
    assert result["publication"]["status"] == "draft"
    assert result["publication"]["approved_by"] is None


def test_sha256_file_changes_when_bytes_change(tmp_path):
    path = tmp_path / "data.bin"
    path.write_bytes(b"one")
    first = sha256_file(path)
    path.write_bytes(b"two")
    assert sha256_file(path) != first


def test_missing_source_bytes_fail_closed(tmp_path):
    catalog, sources, artifact, input_file = fixture(tmp_path)
    with pytest.raises(FileNotFoundError):
        build_manifest(artifact, "test_indicator", catalog, sources,
                       reference_year="2024", source_files={"source_a": tmp_path / "absent"})


def test_unknown_source_and_indicator_rejected(tmp_path):
    catalog, sources, artifact, input_file = fixture(tmp_path)
    with pytest.raises(ValueError, match="Unknown indicator"):
        build_manifest(artifact, "wrong", catalog, sources, reference_year="2024")
    with pytest.raises(ValueError, match="Source file identifiers"):
        build_manifest(artifact, "test_indicator", catalog, sources,
                       reference_year="2024", source_files={"unlisted": input_file})


def test_reference_year_is_mandatory(tmp_path):
    catalog, sources, artifact, _ = fixture(tmp_path)
    with pytest.raises(ValueError, match="reference_year"):
        build_manifest(artifact, "test_indicator", catalog, sources, reference_year="")
