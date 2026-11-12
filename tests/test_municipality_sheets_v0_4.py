"""Two-page municipal sheet tests: synthetic data, exact page budget, fail-closed QA."""
from __future__ import annotations

import csv
import json
import re

import pytest
from pypdf import PdfReader

from epah_diagnosis.municipality_sheets_v0_4 import build, _read, _sha
from epah_diagnosis.output_hub_v0_4 import build as build_hub
from test_output_hub_v0_4 import prepare


def test_27_two_page_a4_profiles_and_54_page_book(tmp_path):
    atlas, review = prepare(tmp_path)
    sheets = tmp_path / "sheets"
    assert build(atlas, review, sheets) == sheets
    individual = sorted((sheets / "pdf").glob("*.pdf"))
    assert len(individual) == 27
    for path in individual:
        assert re.fullmatch(r"[0-9]{6}\.pdf", path.name)
        pdf = PdfReader(str(path))
        assert len(pdf.pages) == 2
        assert all(round(float(page.mediabox.width)) == 595 for page in pdf.pages)
        assert all(round(float(page.mediabox.height)) == 842 for page in pdf.pages)
        text_page_one = pdf.pages[0].extract_text() or ""
        text_page_two = pdf.pages[1].extract_text() or ""
        assert "BOZZA TECNICA" in text_page_one
        assert "Non acquisito" in text_page_two
        assert "Synthetic unemployment" in text_page_two
        assert "Synthetic source" in text_page_two
        assert path.stem in text_page_one and path.stem in text_page_two
    combined = PdfReader(str(sheets / "schede_27_comuni.pdf"))
    assert len(combined.pages) == 54
    listing = (sheets / "index.html").read_text(encoding="utf-8")
    assert listing.count('href="pdf/') == 27
    for path in individual:
        assert 'href="pdf/' + path.name + '"' in listing
    assert "54 pagine" in listing
    metadata = json.loads((sheets / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["pages_per_municipality"] == 2
    assert metadata["publication_allowed"] is False
    assert metadata["scientific_approval"] is False
    assert len(metadata["municipality_codes"]) == 27
    receipt = json.loads((sheets / "manifest.json").read_text(encoding="utf-8"))
    for relative, digest in receipt["outputs_sha256"].items():
        assert _sha(sheets / relative) == digest
    with pytest.raises(FileExistsError):
        build(atlas, review, sheets)


def test_portal_includes_sheets_and_full_integrity_manifest(tmp_path):
    atlas, review = prepare(tmp_path)
    hub = tmp_path / "portal"
    build_hub(atlas, review, hub)
    index = (hub / "index.html").read_text(encoding="utf-8")
    assert 'href="sheets/index.html"' in index
    assert 'href="sheets/schede_27_comuni.pdf"' in index
    assert len(list((hub / "sheets" / "pdf").glob("*.pdf"))) == 27
    receipt = json.loads((hub / "manifest.json").read_text(encoding="utf-8"))
    assert "sheets/schede_27_comuni.pdf" in receipt["outputs_sha256"]
    assert "sheets/pdf/001001.pdf" in receipt["outputs_sha256"]
    assert len(PdfReader(str(hub / "sheets/schede_27_comuni.pdf")).pages) == 54
    assert receipt["publication_allowed"] is False


def test_changed_review_value_rejected_even_if_hashes_updated(tmp_path):
    atlas, review = prepare(tmp_path)
    path = review / "observations.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        rows = list(reader)
    first = next(row for row in rows if row["indicator_id"] == "H46")
    first["value"] = "8.9"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    for receipt_file in ("observations_manifest.json", "manifest.json"):
        receipt = json.loads((review / receipt_file).read_text(encoding="utf-8"))
        receipt["outputs_sha256"]["observations.csv"] = _sha(path)
        (review / receipt_file).write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ValueError, match="Numeric observation differs"):
        build(atlas, review, tmp_path / "blocked")
    assert not (tmp_path / "blocked").exists()


def test_no_false_zero_for_missing_observations(tmp_path):
    atlas, review = prepare(tmp_path)
    data = json.loads((atlas / "atlas_data.json").read_text())
    metrics, towns, records = _read(data, review / "observations.csv")
    assert len(metrics) == 2 and len(towns) == 27
    assert all(records[t["code"]][1]["value"] == "" for t in towns)
    assert all(records[t["code"]][1]["missing_reason"] == "not_acquired" for t in towns)


def test_rejects_bad_review_or_output_overlap(tmp_path):
    atlas, review = prepare(tmp_path)
    target = atlas / "generated"
    with pytest.raises(ValueError, match="separate"):
        build(atlas, review, target)
    (review / "review.pdf").write_bytes(b"%PDF-1.0 tampered")
    with pytest.raises(ValueError, match="checksum mismatch"):
        build(atlas, review, tmp_path / "blocked")
