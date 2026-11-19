import csv
import hashlib
import json
from pathlib import Path

import pytest

from epah_diagnosis.erp_request_v0_5 import COUNT_FIELDS, build_packet
from epah_diagnosis.methodology_v0_5 import main

REGISTRY = Path(__file__).resolve().parents[1] / "data/municipalities.csv"


def test_packet_has_exact_scope_empty_counts_and_traceable_files(tmp_path):
    before = REGISTRY.read_bytes()
    out = build_packet(REGISTRY, "2025-12-31", tmp_path / "request")
    template = json.loads((out / "response_template.json").read_text(encoding="utf-8"))
    expected = list(csv.DictReader(REGISTRY.open(encoding="utf-8")))
    assert [(r["municipality"], r["istat_code"]) for r in template["municipalities"]] == [
        (r["municipality"], r["istat_code"]) for r in expected]
    assert template["request_sent"] is template["scientific_approval"] is False
    assert template["requested_reference_date"] == "2025-12-31"
    for row in template["municipalities"]:
        assert row["response_status"] == "not_provided" and row["actual_reference_date"] is None
        assert all(row[field] is None for field in COUNT_FIELDS)
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["registry_sha256"] == hashlib.sha256(before).hexdigest()
    assert manifest["municipal_series_added"] == 0
    for name, digest in manifest["files_sha256"].items():
        assert hashlib.sha256((out / name).read_bytes()).hexdigest() == digest
    assert REGISTRY.read_bytes() == before
    assert str(REGISTRY) not in (out / "manifest.json").read_text(encoding="utf-8")


def test_packet_is_deterministic_and_never_sends_or_imputes(tmp_path):
    first = build_packet(REGISTRY, "2025-12-31", tmp_path / "one")
    second = build_packet(REGISTRY, "2025-12-31", tmp_path / "two")
    for path in first.iterdir():
        assert path.read_bytes() == (second / path.name).read_bytes()


@pytest.mark.parametrize("kind", ["file", "empty_directory"])
def test_existing_destination_is_preserved(tmp_path, kind):
    out = tmp_path / "existing"
    if kind == "file":
        out.write_bytes(b"existing evidence")
    else:
        out.mkdir()
    with pytest.raises(FileExistsError):
        build_packet(REGISTRY, "2025-12-31", out)
    assert out.read_bytes() == b"existing evidence" if kind == "file" else list(out.iterdir()) == []


@pytest.mark.parametrize("case", ["missing_municipality", "duplicate_code", "short_code"])
def test_invalid_registry_produces_no_packet(tmp_path, case):
    rows = list(csv.DictReader(REGISTRY.open(encoding="utf-8")))
    if case == "missing_municipality":
        rows.pop()
    elif case == "duplicate_code":
        rows[-1]["istat_code"] = rows[0]["istat_code"]
    else:
        rows[0]["istat_code"] = "1007"
    source = tmp_path / "registry.csv"
    with source.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["municipality", "istat_code"])
        writer.writeheader()
        writer.writerows(rows)
    out = tmp_path / "result"
    with pytest.raises(ValueError):
        build_packet(source, "2025-12-31", out)
    assert not out.exists()


@pytest.mark.parametrize("value", ["2025-02-30", "20251231", "not_a_date"])
def test_reference_date_must_be_explicit_valid_iso(tmp_path, value):
    with pytest.raises(ValueError):
        build_packet(REGISTRY, value, tmp_path / "result")
    assert not (tmp_path / "result").exists()


def test_failed_publication_exposes_no_partial_packet(tmp_path, monkeypatch):
    import epah_diagnosis.erp_request_v0_5 as module
    def fail(stage, target):
        assert (stage / "manifest.json").is_file()
        raise OSError("synthetic failure")
    monkeypatch.setattr(module, "publish_directory", fail)
    with pytest.raises(OSError):
        build_packet(REGISTRY, "2025-12-31", tmp_path / "result")
    assert not (tmp_path / "result").exists()
    assert not list(tmp_path.glob(".epah-erp-request-*"))


def test_methodology_command_dispatch_and_invalid_flags(tmp_path):
    assert main(["erp-request", "--registry", str(REGISTRY), "--reference-date", "2025-12-31",
                 "--out-dir", str(tmp_path / "result")]) == 0
    with pytest.raises(SystemExit) as error:
        main(["erp-request", "--catalog", str(REGISTRY)])
    assert error.value.code == 2
    with pytest.raises(SystemExit) as error:
        main(["check", "--registry", str(REGISTRY)])
    assert error.value.code == 2
