"""Step 9: shared synthetic example, real v0.4 renderers and packager."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil

import pytest
from pypdf import PdfReader, PdfWriter

from epah_diagnosis.output_bundle_quality_v0_4 import audit_bundle, _links, _media
from epah_diagnosis.output_quality_v0_4 import _sha
from epah_diagnosis.synthetic_example_v0_4 import build as build_example


@pytest.fixture(scope="module")
def synthetic_example(tmp_path_factory):
    root = tmp_path_factory.mktemp("SYNTHETIC-step9")
    return build_example(root / "example")


@pytest.fixture(scope="module")
def synthetic_hub(synthetic_example):
    hub = synthetic_example / "hub"
    destination = os.environ.get("EPAH_SYNTHETIC_QA_DIR")
    if destination:
        # Historical opt-in for browser QA remains compatible; never overwrite.
        shutil.copytree(hub, Path(destination))
    return hub


@pytest.fixture
def hub(tmp_path, synthetic_hub):
    destination = tmp_path / "hub"
    shutil.copytree(synthetic_hub, destination)
    return destination


def rehash(root, name):
    path = root / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["outputs_sha256"][name] = _sha(root / name)
    path.write_text(json.dumps(manifest))


def test_real_renderers_produce_consistent_complete_synthetic_bundle(synthetic_hub):
    result = audit_bundle(synthetic_hub)
    assert result["municipalities"] == 27 and result["indicator_slots"] == 16
    assert result["observations"] == 432
    assert result["chart_files_checked"] == 48
    assert result["local_references_checked"] >= 35
    assert result["external_source_links"] == []
    assert result["combined_pages"] == 54 and result["summary_pages"] == 2
    assert result["scientific_approval"] is result["publication_allowed"] is False
    assert result["visual_review_completed"] is False
    assert "real_sources" in result["human_checks_required"]


def test_example_receipt_binds_inputs_audits_and_product_manifests(synthetic_example):
    receipt = json.loads((synthetic_example / "run.json").read_text(encoding="utf-8"))
    assert receipt["synthetic_fixture"] is True
    assert receipt["source_ingestion_performed"] is False
    assert receipt["scientific_approval"] is receipt["publication_allowed"] is False
    assert receipt["result"] == "synthetic_example_ready"
    assert receipt["entrypoint"] == "hub/index.html"
    assert len(receipt["indicators_available"]) == 12
    assert receipt["indicators_pending"] == ["H03", "H04", "H05", "ADD-HOUSING-01"]
    for name, digest in receipt["inputs_sha256"].items():
        assert _sha(synthetic_example / "inputs" / name) == digest
    for name, digest in receipt["artifacts_sha256"].items():
        assert _sha(synthetic_example / name) == digest


def test_example_inputs_are_deterministic_without_mutating_territorial_metrics(tmp_path):
    from epah_diagnosis import synthetic_example_v0_4 as example, visual_atlas_v0_4 as atlas
    original = (*atlas.v3.METRICS, *atlas.NEW)
    for name in ("first", "second"):
        example._inputs(tmp_path / name)
    for path in (tmp_path / "first").iterdir():
        assert _sha(path) == _sha(tmp_path / "second" / path.name)
        assert b"\r" not in path.read_bytes()
    payload = json.loads((tmp_path / "first/synthetic_snapshot.json").read_text(encoding="utf-8"))
    assert payload["municipalities"][0]["values"]["H47"]["value"] == 0
    assert "H03" not in payload["municipalities"][0]["values"]
    assert (*atlas.v3.METRICS, *atlas.NEW) == original
    assert all(m.source == "SYNTHETIC TEST ONLY" for m in example._inputs(tmp_path / "third")[2])


def test_example_products_visibly_identify_fictional_data(synthetic_example):
    for name in ("hub/index.html", "atlas/index.html", "review/review.html"):
        assert "ESEMPIO SINTETICO" in (synthetic_example / name).read_text(encoding="utf-8")
    for name in ("review/review.pdf", "hub/sintesi.pdf"):
        assert "ESEMPIO SINTETICO" in PdfReader(synthetic_example / name).pages[0].extract_text()
    assert "Synthetic" in PdfReader(
        synthetic_example / "hub/sheets/schede_27_comuni.pdf").pages[0].extract_text()


def test_synthetic_sheets_keep_warning_when_opened_separately(synthetic_hub):
    assert "ESEMPIO SINTETICO" in (synthetic_hub / "sheets/index.html").read_text(encoding="utf-8")
    for path in (synthetic_hub / "sheets/pdf").glob("*.pdf"):
        assert all("ESEMPIO SINTETICO" in page.extract_text() for page in PdfReader(path).pages)
    assert all("ESEMPIO SINTETICO" in page.extract_text()
               for page in PdfReader(synthetic_hub / "sheets/schede_27_comuni.pdf").pages)


def test_example_has_no_undocumented_evidence_export(synthetic_example):
    assert {p.name for p in synthetic_example.iterdir()} == {
        "inputs", "atlas", "review", "hub", "qa", "run.json", "README_REVIEW.txt"}


def test_review_template_is_snapshot_bound_blank_and_in_manifest(synthetic_hub):
    import csv
    path = synthetic_hub / "review/indicator_review_template.csv"
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 16
    assert {row["snapshot_sha256"] for row in rows} == {_sha(synthetic_hub / "atlas/atlas_data.json")}
    assert {row["technical_review_status"] for row in rows} == {"pending"}
    assert {row["stakeholder_validation_status"] for row in rows} == {"not_performed"}
    assert all(not row["reviewer"] and not row["reviewed_on"] for row in rows)
    manifest = json.loads((synthetic_hub / "review/manifest.json").read_text(encoding="utf-8"))
    assert manifest["outputs_sha256"][path.name] == _sha(path)
    portal = (synthetic_hub / "index.html").read_text(encoding="utf-8")
    assert "Situazione per indicatore" in portal and "indicator_review_template.csv" in portal


@pytest.mark.parametrize("kind", ["directory", "file"])
def test_example_never_overwrites_existing_destinations(tmp_path, kind):
    destination = tmp_path / "existing"
    if kind == "directory":
        destination.mkdir()
        marker = destination / "keep.txt"
    else:
        marker = destination
    marker.write_bytes(b"preserve existing content")
    with pytest.raises(FileExistsError, match="fresh synthetic"):
        build_example(destination)
    assert marker.read_bytes() == b"preserve existing content"


def test_failed_example_audit_does_not_publish_or_touch_neighbour(tmp_path, monkeypatch):
    from epah_diagnosis import output_bundle_quality_v0_4 as quality
    destination = tmp_path / "failed-example"
    neighbour = tmp_path / "previous-result.txt"
    neighbour.write_bytes(b"preserve previous result")

    def reject(hub):
        raise ValueError("SYNTHETIC audit rejection")

    monkeypatch.setattr(quality, "audit_bundle", reject)
    with pytest.raises(ValueError, match="SYNTHETIC audit rejection"):
        build_example(destination)
    assert not destination.exists()
    assert neighbour.read_bytes() == b"preserve previous result"


def test_broken_link_rejected_after_rehash(hub):
    path = hub / "index.html"
    path.write_text(path.read_text().replace('href="review/observations.csv"', 'href="lost.csv"'))
    rehash(hub, "index.html")
    with pytest.raises(ValueError, match="Missing or unsafe output"):
        audit_bundle(hub)


def test_rehashed_combined_pdf_wrong_page_budget_is_rejected(hub):
    pdf = hub / "sheets/schede_27_comuni.pdf"
    writer = PdfWriter()
    writer.add_page(PdfReader(pdf).pages[0])
    with pdf.open("wb") as stream:
        writer.write(stream)
    rehash(hub / "sheets", "schede_27_comuni.pdf")
    for name in ("sheets/schede_27_comuni.pdf", "sheets/manifest.json"):
        rehash(hub, name)
    with pytest.raises(ValueError, match="Wrong PDF page count"):
        audit_bundle(hub)


def test_rehashed_sheets_from_another_snapshot_are_rejected(hub):
    path = hub / "sheets/metadata.json"
    metadata = json.loads(path.read_text())
    metadata["reference_atlas_data_sha256"] = "0" * 64
    path.write_text(json.dumps(metadata))
    rehash(hub / "sheets", "metadata.json")
    for name in ("sheets/metadata.json", "sheets/manifest.json"):
        rehash(hub, name)
    with pytest.raises(ValueError, match="sheet metadata"):
        audit_bundle(hub)


def test_unlisted_file_or_symlink_is_rejected(hub, tmp_path):
    (hub / "unlisted.txt").write_text("do not package")
    with pytest.raises(ValueError, match="Unexpected or missing"):
        audit_bundle(hub)
    (hub / "unlisted.txt").unlink()


def test_symlink_is_rejected(hub, tmp_path, symlink_support):
    external = tmp_path / "external.html"
    external.write_bytes((hub / "index.html").read_bytes())
    (hub / "index.html").unlink()
    (hub / "index.html").symlink_to(external)
    with pytest.raises(ValueError, match="unsafe output"):
        audit_bundle(hub)


@pytest.mark.parametrize("address", ["../outside.html", "https://example.org/runtime.js", "javascript:alert(1)"])
def test_external_dependencies_and_escaping_links_fail(tmp_path, address):
    (tmp_path / "index.html").write_text(f'<script src="{address}"></script>')
    with pytest.raises(ValueError, match="escapes|External"):
        _links(tmp_path)


def test_missing_html_fragment_is_rejected(tmp_path):
    (tmp_path / "index.html").write_text('<a href="#lost">Go</a>')
    with pytest.raises(ValueError, match="fragment"):
        _links(tmp_path)


@pytest.mark.parametrize("extension,content", [("png", "not PNG"), ("svg", "<svg>broken")])
def test_broken_chart_structure_rejected(tmp_path, extension, content):
    path = tmp_path / ("broken." + extension)
    path.write_text(content)
    with pytest.raises(ValueError, match="Invalid"):
        _media(path)


def test_rehashed_sheet_ledger_cannot_diverge_from_review(hub):
    path = hub / "sheets/evidence_ledger.json"
    ledger = json.loads(path.read_text())
    ledger["indicators"][0]["source"] = "invented"
    path.write_text(json.dumps(ledger))
    rehash(hub / "sheets", "evidence_ledger.json")
    for name in ("sheets/evidence_ledger.json", "sheets/manifest.json"):
        rehash(hub, name)
    with pytest.raises(ValueError, match="sheet ledger"):
        audit_bundle(hub)


def test_rehashed_combined_pdf_cannot_reorder_municipalities(hub):
    path = hub / "sheets/schede_27_comuni.pdf"
    reader = PdfReader(path)
    writer = PdfWriter()
    for index in [2, 3, 0, 1, *range(4, 54)]:
        writer.add_page(reader.pages[index])
    with path.open("wb") as stream:
        writer.write(stream)
    rehash(hub / "sheets", "schede_27_comuni.pdf")
    for name in ("sheets/schede_27_comuni.pdf", "sheets/manifest.json"):
        rehash(hub, name)
    with pytest.raises(ValueError, match="Combined PDF differs"):
        audit_bundle(hub)


def test_scientific_approval_cannot_be_claimed_in_nested_manifest(hub):
    path = hub / "sheets/manifest.json"
    manifest = json.loads(path.read_text())
    manifest["scientific_approval"] = True
    path.write_text(json.dumps(manifest))
    rehash(hub, "sheets/manifest.json")
    with pytest.raises(ValueError, match="nonpublication"):
        audit_bundle(hub)


def test_rehashed_pdf_cannot_change_displayed_values(hub):
    from epah_diagnosis.output_quality_v0_4 import SCRIPT
    from epah_diagnosis.review_pack_v0_4 import _pdf
    review = hub / "review"
    embedded = json.loads(SCRIPT.search((review / "review.html").read_text()).group(1))
    rows = [{k: v for k, v in row.items() if k != "display"} for row in embedded["rows"]]
    rows[0]["value"] = "99.0"  # Only the rendered PDF changes; source CSV stays zero.
    _pdf(review / "review.pdf", rows, embedded["indicators"])
    rehash(review, "review.pdf")
    for name in ("review/review.pdf", "review/manifest.json"):
        rehash(hub, name)
    path = hub / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["review_manifest_sha256"] = _sha(review / "manifest.json")
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="PDF report displayed observation"):
        audit_bundle(hub)


def test_pdf_link_cannot_escape_bundle(tmp_path):
    from reportlab.pdfgen import canvas
    pdf = canvas.Canvas(str(tmp_path / "link.pdf"))
    pdf.linkURL("../external.html", (40, 40, 200, 60))
    pdf.showPage()
    pdf.save()
    with pytest.raises(ValueError, match="escapes"):
        _links(tmp_path)


def test_cli_cannot_write_qa_report_inside_input_snapshot(synthetic_hub):
    import subprocess
    import sys
    command = Path(__file__).resolve().parents[1] / "scripts/audit_v0_4_output_quality.py"
    output = synthetic_hub / "must-not-be-created.json"
    result = subprocess.run([sys.executable, str(command), "--hub", str(synthetic_hub),
                             "--json-out", str(output)], capture_output=True, text=True)
    assert result.returncode == 2
    assert "outside input snapshot" in result.stderr
    assert not output.exists()


@pytest.mark.parametrize("page,field,wrong,index", [
    (1, "value", "999.0", 0), (2, "value", "999.0", 0),
    (2, "reference_period", "1900", 0), (2, "unit", "invented", 0),
    (2, "source", "OTHER SOURCE", 0),
    (2, "numerator", "10", 0), (2, "missing_reason", "not_acquired", 0),
    (2, "value", "F", 8),  # A categorical value cannot borrow another slot.
    (2, "missing_reason", "", 12),  # An absent slot cannot display a value.
])
def test_rehashed_municipal_pdfs_must_match_csv(hub, page, field, wrong, index):
    from copy import deepcopy
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from pypdf.generic import NameObject, TextStringObject
    from epah_diagnosis.municipality_sheets_v0_4 import (
        _read, _draw_page_one, _draw_page_two,
    )
    payload = json.loads((hub / "atlas/atlas_data.json").read_text())
    metrics, towns, per_code = _read(payload, hub / "review/observations.csv")
    town = towns[0]
    rows = per_code[town["code"]]
    changed = deepcopy(rows)
    changed[index][field] = wrong
    if field == "numerator":
        changed[index]["denominator"] = "20"
    if index == 12:
        changed[index]["value"] = "0.0"
    sheet = hub / "sheets/pdf" / (town["code"] + ".pdf")
    pdf = canvas.Canvas(str(sheet), pagesize=A4)
    _draw_page_one(pdf, town, metrics, changed if page == 1 else rows)
    _draw_page_two(pdf, town, metrics, changed if page == 2 else rows, has_evidence=True)
    pdf.save()
    # Rewrite the matching volume as well: text identity and fresh hashes alone
    # must not certify a value/period/source which disagrees with the CSV.
    combined = PdfWriter()
    for item in towns:
        combined.append(hub / "sheets/pdf" / (item["code"] + ".pdf"))
        for annotation in combined.pages[-1].get("/Annots", []):
            action = annotation.get_object().get("/A")
            if action and action.get("/URI") == "../evidence_ledger.html":
                action[NameObject("/URI")] = TextStringObject("evidence_ledger.html")
    with (hub / "sheets/schede_27_comuni.pdf").open("wb") as stream:
        combined.write(stream)
    combined.close()
    for name in ("pdf/" + town["code"] + ".pdf", "schede_27_comuni.pdf"):
        rehash(hub / "sheets", name)
        rehash(hub, "sheets/" + name)
    rehash(hub, "sheets/manifest.json")
    with pytest.raises(ValueError, match="Municipal PDF.*CSV"):
        audit_bundle(hub)


def test_sheet_csv_comparison_preserves_zero_and_fractional_counts(tmp_path, synthetic_hub):
    from epah_diagnosis.municipality_sheets_v0_4 import _read, _one_pdf
    from epah_diagnosis.output_bundle_quality_v0_4 import _sheet_pdf_matches
    payload = json.loads((synthetic_hub / "atlas/atlas_data.json").read_text())
    metrics, towns, per_code = _read(payload, synthetic_hub / "review/observations.csv")
    town = towns[0]
    rows = per_code[town["code"]]
    # Synthetic estimated counts are intentionally not rounded to integers.
    row = next(row for row in rows if row["indicator_id"] == "H46")
    row.update(numerator="0.0", denominator="7.5")
    pdf = tmp_path / "fractional-counts.pdf"
    _one_pdf(pdf, town, metrics, rows)
    texts = [page.extract_text() for page in PdfReader(pdf).pages]
    _sheet_pdf_matches(texts, town, rows)
    row["denominator"] = "8.5"
    with pytest.raises(ValueError, match="Municipal PDF.*CSV"):
        _sheet_pdf_matches(texts, town, rows)
