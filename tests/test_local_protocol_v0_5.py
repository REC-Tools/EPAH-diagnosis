"""A review scaffold preserves source identity and never creates local estimates."""
import hashlib
import json
from pathlib import Path

import pytest

from epah_diagnosis.methodology_v0_5 import LOCAL_DECISIONS, main, prepare_protocol

CATALOG = Path(__file__).resolve().parents[1] / "docs/v0_5_indicator_contracts.json"


@pytest.mark.parametrize("indicator_id", [f"V05-{n:02d}" for n in range(1, 19)])
def test_each_proposal_keeps_benchmark_and_local_choices_separate(tmp_path, indicator_id):
    raw = CATALOG.read_bytes()
    document = json.loads(raw)
    output = prepare_protocol(CATALOG, indicator_id, tmp_path / "protocol")
    record = json.loads((output / "protocol.json").read_text(encoding="utf-8"))
    selected = next(item for item in document["indicators"] if item["id"] == indicator_id)
    assert record["benchmark_contract"] == selected
    assert record["benchmark_source"] == document["sources"][selected["source_ref"]]
    assert record["catalog_sha256"] == hashlib.sha256(raw).hexdigest()
    assert record["municipal_series_added"] == 0
    for key in ("collection_authorized", "scientific_approval", "publication_allowed", "source_ingestion_performed"):
        assert record[key] is False
    assert set(record["local_decisions"]) == set(LOCAL_DECISIONS)
    assert all(item["proposed_answer"] is item["evidence_reference"] is None
               for item in record["local_decisions"].values())
    assert CATALOG.read_bytes() == raw


@pytest.mark.parametrize("existing", ["directory", "file"])
def test_refuses_existing_destination_without_changes(tmp_path, existing):
    output = tmp_path / "existing"
    if existing == "directory":
        output.mkdir()
        sentinel = output / "review.json"
    else:
        sentinel = output
    sentinel.write_bytes(b"previous evidence")
    with pytest.raises(FileExistsError):
        prepare_protocol(CATALOG, "V05-02", output)
    assert sentinel.read_bytes() == b"previous evidence"


@pytest.mark.parametrize("corruption", ["unknown_id", "approved_catalog", "municipal_benchmark"])
def test_invalid_input_leaves_no_dossier(tmp_path, corruption):
    catalog = tmp_path / "catalog.json"
    document = json.loads(CATALOG.read_bytes())
    indicator_id = "V05-99" if corruption == "unknown_id" else "V05-02"
    if corruption == "approved_catalog":
        document["scientific_approval"] = True
    if corruption == "municipal_benchmark":
        document["indicators"][1]["geography"] = "municipality"
    catalog.write_text(json.dumps(document), encoding="utf-8")
    output = tmp_path / "uncreated" / "protocol"
    with pytest.raises(ValueError):
        prepare_protocol(catalog, indicator_id, output)
    assert not output.parent.exists()


def test_same_inputs_produce_same_files_and_no_private_source_path(tmp_path):
    first = prepare_protocol(CATALOG, "V05-02", tmp_path / "first")
    second = prepare_protocol(CATALOG, "V05-02", tmp_path / "second")
    for name in ("protocol.json", "README_REVIEW.md"):
        assert (first / name).read_bytes() == (second / name).read_bytes()
        assert str(CATALOG).encode() not in (first / name).read_bytes()


def test_publish_failure_does_not_expose_partial_dossier(tmp_path, monkeypatch):
    import epah_diagnosis.methodology_v0_5 as module
    def fail(stage, destination):
        assert (stage / "protocol.json").is_file()
        raise OSError("synthetic publication failure")
    monkeypatch.setattr(module, "publish_directory", fail)
    output = tmp_path / "result"
    with pytest.raises(OSError):
        prepare_protocol(CATALOG, "V05-02", output)
    assert not output.exists()
    assert not list(tmp_path.glob(".epah-protocol-*"))


def test_cli_prepare_and_existing_check_are_distinct(tmp_path, capsys):
    assert main(["check", "--catalog", str(CATALOG)]) == 0
    assert json.loads(capsys.readouterr().out)["proposals"] == 18
    assert main(["prepare", "--catalog", str(CATALOG), "--indicator", "V05-02",
                 "--out-dir", str(tmp_path / "protocol")]) == 0
    assert "RACCOLTA NON AUTORIZZATA" in capsys.readouterr().out
    for args in (["prepare", "--catalog", str(CATALOG)],
                 ["check", "--catalog", str(CATALOG), "--indicator", "V05-02"]):
        with pytest.raises(SystemExit) as error:
            main(args)
        assert error.value.code == 2
