"""Synthetic integration tests for the v0.4 offline output hub."""
from __future__ import annotations

import json
import re

import pytest
from pypdf import PdfReader

from epah_diagnosis.atlas_observations_v0_4 import _sha
from epah_diagnosis.output_hub_v0_4 import build
from epah_diagnosis.review_pack_v0_4 import build as build_review
from test_atlas_observations_v0_4 import inputs


def prepare(tmp_path):
    atlas, registry, _, _ = inputs(tmp_path)
    (atlas / "index.html").write_text("<!doctype html><title>Synthetic atlas</title>", encoding="utf-8")
    (atlas / "README_REVIEW.txt").write_text("SYNTHETIC TECHNICAL DRAFT", encoding="utf-8")
    manifest_file = atlas / "atlas_manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    manifest["no_composite_score"] = True
    manifest["output_sha256"]["index.html"] = _sha(atlas / "index.html")
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
    review = tmp_path / "review"
    build_review(atlas, registry, review)
    return atlas, review


def test_hub_packs_offline_links_and_two_page_pdf(tmp_path):
    atlas, review = prepare(tmp_path)
    output = tmp_path / "exports" / "portal"
    assert build(atlas, review, output) == output
    index = (output / "index.html").read_text(encoding="utf-8")
    assert "Atlante interattivo" in index
    assert "BOZZA TECNICA - NON PUBBLICARE" in index
    assert "1</strong>Serie disponibili" in index
    assert "1</strong>Serie non acquisite" in index
    hrefs = re.findall(r'href="([^"]+)"', index)
    for path in hrefs:
        if path.startswith("#"):
            continue
        assert (output / path).is_file(), path
    summary = PdfReader(str(output / "sintesi.pdf"))
    assert len(summary.pages) == 2
    extracted = "\n".join(page.extract_text() or "" for page in summary.pages)
    assert "BOZZA TECNICA" in extracted
    assert "H46" in extracted and "H04" in extracted
    assert "27" in extracted
    assert b"%PDF" in (output / "sintesi.pdf").read_bytes()[:8]
    receipt = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert receipt["scientific_approval"] is False
    assert receipt["publication_allowed"] is False
    assert receipt["indicator_slots"] == 2
    assert receipt["outputs_sha256"]["atlas/atlas_data.json"] == _sha(output / "atlas/atlas_data.json")
    assert receipt["outputs_sha256"]["review/observations.csv"] == _sha(output / "review/observations.csv")
    for folder, name in ((atlas, "atlas"), (review, "review")):
        for original in folder.rglob("*"):
            if original.is_file():
                assert (output / name / original.relative_to(folder)).read_bytes() == original.read_bytes()
    with pytest.raises(FileExistsError):
        build(atlas, review, output)


def test_review_from_different_atlas_is_rejected(tmp_path):
    atlas, review = prepare(tmp_path)
    (atlas / "atlas_data.json").write_bytes((atlas / "atlas_data.json").read_bytes() + b"\n")
    manifest_file = atlas / "atlas_manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    manifest["output_sha256"]["atlas_data.json"] = _sha(atlas / "atlas_data.json")
    manifest_file.write_text(json.dumps(manifest))
    target = tmp_path / "blocked"
    with pytest.raises(ValueError, match="different atlas"):
        build(atlas, review, target)
    assert not target.exists()


def test_modified_review_pdf_blocks_packaging(tmp_path):
    atlas, review = prepare(tmp_path)
    with (review / "review.pdf").open("ab") as handle:
        handle.write(b"\nchange")
    with pytest.raises(ValueError, match="checksum mismatch"):
        build(atlas, review, tmp_path / "blocked")


def test_unlisted_input_file_or_symlink_is_rejected(tmp_path):
    atlas, review = prepare(tmp_path)
    (review / "secret-unlisted.txt").write_text("should never be repackaged")
    with pytest.raises(ValueError, match="Unexpected or missing"):
        build(atlas, review, tmp_path / "blocked")


def test_output_nested_in_source_is_rejected(tmp_path):
    atlas, review = prepare(tmp_path)
    with pytest.raises(ValueError, match="separate"):
        build(atlas, review, atlas / "portable")


def test_changed_availability_metadata_is_rejected(tmp_path):
    atlas, review = prepare(tmp_path)
    file = review / "metadata.json"
    metadata = json.loads(file.read_text())
    metadata["indicators"][0]["available"] = False
    file.write_text(json.dumps(metadata))
    manifest_file = review / "manifest.json"
    manifest = json.loads(manifest_file.read_text())
    manifest["outputs_sha256"]["metadata.json"] = _sha(file)
    manifest_file.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="indicator metadata differ"):
        build(atlas, review, tmp_path / "blocked")


def test_pdf_and_html_have_no_rankings_or_invented_values(tmp_path):
    atlas, review = prepare(tmp_path)
    output = tmp_path / "out"
    build(atlas, review, output)
    contents = (output / "index.html").read_text(encoding="utf-8")
    assert "graduatoria" not in contents.lower()
    brief = " ".join(page.extract_text() or "" for page in PdfReader(str(output / "sintesi.pdf")).pages)
    assert "2555.00" not in brief
    assert "Non acquisito" in brief
