"""Synthetic ERP response ingestion; no entity contacts or scientific formulas."""
import csv
import json

import pytest

from epah_diagnosis import erp_response_v0_5 as erp
from epah_diagnosis.erp_request_v0_5 import COUNT_FIELDS, build_packet
from epah_diagnosis.methodology_v0_5 import main
from epah_diagnosis.provenance import sha256_file


@pytest.fixture
def inputs(tmp_path):
    registry = tmp_path / "registry.csv"
    with registry.open("w", encoding="utf-8", newline="") as handle:
        csv.writer(handle).writerows([["municipality", "istat_code"],
                                    *[(f"Comune fittizio {i}", f"000{i:03}") for i in range(1, 28)]])
    packet = build_packet(registry, "2025-12-31", tmp_path / "request")
    source = packet / "response_template.json"
    return registry, source, json.loads(source.read_text(encoding="utf-8"))


def save(source, document):
    source.write_text(json.dumps(document, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def test_blank_response_stays_unknown_and_inputs_are_copied_exactly(inputs, tmp_path):
    registry, source, document = inputs
    before = source.read_bytes(), registry.read_bytes()
    out = erp.import_response(source, registry, tmp_path / "review")
    report = json.loads((out / "review.json").read_text())
    assert report["response_status_counts"]["not_provided"] == 27
    assert report["municipalities_with_any_counts"] == 0
    assert all(row["actual_reference_date"] is None for row in report["municipalities"])
    assert all(all(row[k] is None for k in COUNT_FIELDS) for row in report["municipalities"])
    assert before == (source.read_bytes(), registry.read_bytes())
    assert (out / "inputs/response.json").read_bytes() == before[0]
    assert (out / "inputs/registry.csv").read_bytes() == before[1]
    manifest = json.loads((out / "manifest.json").read_text())
    for name, digest in manifest["files_sha256"].items():
        assert sha256_file(out / name) == digest
    with (out / "responses.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 27 and all(row["erp_total"] == "" for row in rows)
    assert report["scientific_approval"] is report["publication_allowed"] is report["indicator_calculated"] is False


def test_example_covers_zero_missing_non_management_and_mixed_years_without_sums(tmp_path):
    out = erp.create_example(tmp_path / "demo")
    report = json.loads((out / "review.json").read_text())
    assert report["input_kind"] == "synthetic_declared"
    assert report["response_status_counts"] == {"not_provided": 23, "data_provided": 1, "verified_zero": 1,
                                                 "not_managed": 1, "unavailable": 1}
    first, zero, non_manager = report["municipalities"][:3]
    assert first["actual_reference_date"] == "2024-12-31" and first["target_minus_actual_reference_year"] == 1
    assert first["erp_occupied"] == 7 and first["erp_let"] == 6
    assert first["erp_assignable"] == 2 and first["erp_vacant_total"] == 3
    assert first["erp_vacant_other_reason"] is None and "partial_count_fields" in first["review_issues"]
    assert all(zero[k] == 0 for k in COUNT_FIELDS) and zero["review_issues"] == []
    assert all(non_manager[k] is None for k in COUNT_FIELDS)
    assert report["municipal_series_added"] == report["messages_sent_by_tool"] == report["network_requests_made"] == 0
    assert report["weights_applied"] is False
    assert "DATI SINTETICI" in (out / "README_REVIEW.txt").read_text()


def test_context_and_status_conflicts_are_visible_without_filling_dates_or_counts(inputs):
    registry, source, doc = inputs
    row = doc["municipalities"][0]
    row.update(response_status="verified_zero", erp_total=0, erp_let=1)
    save(source, doc)
    report = erp.review_response(source.read_bytes(), erp.read_municipality_codes(registry))
    record = report["municipalities"][0]
    assert "positive_count_in_zero_declaration" in record["review_issues"]
    assert "missing_context:actual_reference_date" in record["review_issues"]
    assert record["actual_reference_date"] is record["target_minus_actual_reference_year"] is None
    assert record["erp_vacant_total"] is None
    row.update(response_status="not_managed")
    save(source, doc)
    record = erp.review_response(source.read_bytes(), erp.read_municipality_codes(registry))["municipalities"][0]
    assert "counts_conflict_with_response_status" in record["review_issues"]
    assert record["erp_total"] == 0


@pytest.mark.parametrize("problem", ["duplicate_code", "wrong_name", "missing_record", "unknown_state", "old_schema",
                                   "approval", "decimal", "boolean_count", "negative", "formatted_count", "bad_date"])
def test_invalid_mapping_or_exchange_types_block_before_output(inputs, tmp_path, problem):
    registry, source, doc = inputs
    row = doc["municipalities"][0]
    if problem == "duplicate_code":
        doc["municipalities"][-1] = dict(row)
    elif problem == "wrong_name":
        row["municipality"] = "Un altro Comune"
    elif problem == "missing_record":
        doc["municipalities"].pop()
    elif problem == "unknown_state":
        row["response_status"] = "approved"
    elif problem == "old_schema":
        doc["schema_version"] = "0.5-erp-response-template-draft-1"
    elif problem == "approval":
        doc["scientific_approval"] = True
    elif problem == "bad_date":
        row["actual_reference_date"] = "20251231"
    else:
        row["erp_total"] = {"decimal": 1.5, "boolean_count": False, "negative": -1, "formatted_count": "1.000"}[problem]
    save(source, doc)
    before = source.read_bytes()
    with pytest.raises(ValueError):
        erp.import_response(source, registry, tmp_path / "blocked")
    assert not (tmp_path / "blocked").exists() and source.read_bytes() == before


def test_utf8_bom_is_preserved_and_ambiguous_json_is_not_accepted(inputs, tmp_path):
    registry, source, _ = inputs
    source.write_bytes(b"\xef\xbb\xbf" + source.read_bytes())
    out = erp.import_response(source, registry, tmp_path / "bom")
    assert (out / "inputs/response.json").read_bytes() == source.read_bytes()
    raw = source.read_bytes().replace(b'"request_sent": false', b'"request_sent": false, "request_sent": true')
    source.write_bytes(raw)
    with pytest.raises(ValueError, match="Duplicate"):
        erp.import_response(source, registry, tmp_path / "duplicate")


def test_csv_literal_source_text_and_json_provenance_are_distinct(inputs, tmp_path):
    registry, source, doc = inputs
    doc["request_sent"] = True  # A source declaration is not an action by this tool.
    doc["municipalities"][0]["source_reference"] = "  =SUM(1,2)"
    save(source, doc)
    out = erp.import_response(source, registry, tmp_path / "review")
    with (out / "responses.csv").open(encoding="utf-8", newline="") as handle:
        row = next(csv.DictReader(handle))
    assert row["source_reference"] == "'  =SUM(1,2)"
    report = json.loads((out / "review.json").read_text())
    assert report["municipalities"][0]["source_reference"] == "  =SUM(1,2)"
    assert report["request_sent_as_declared"] is True and report["messages_sent_by_tool"] == 0


def test_existing_output_and_failed_publication_preserve_evidence(inputs, tmp_path, monkeypatch):
    registry, source, _ = inputs
    old = tmp_path / "old"
    old.mkdir()
    (old / "keep").write_bytes(b"prior evidence")
    with pytest.raises(FileExistsError):
        erp.import_response(source, registry, old)
    assert (old / "keep").read_bytes() == b"prior evidence"
    before = source.read_bytes()
    monkeypatch.setattr(erp, "publish_directory", lambda *args: (_ for _ in ()).throw(OSError("synthetic failure")))
    with pytest.raises(OSError):
        erp.import_response(source, registry, tmp_path / "failed")
    assert source.read_bytes() == before and not (tmp_path / "failed").exists()


def test_cli_example_and_real_input_modes_are_separate(tmp_path):
    assert main(["erp-import", "--example", "--out-dir", str(tmp_path / "example")]) == 0
    with pytest.raises(SystemExit) as exc:
        main(["erp-import", "--example", "--response", "not-used", "--out-dir", str(tmp_path / "blocked")])
    assert exc.value.code == 2 and not (tmp_path / "blocked").exists()
