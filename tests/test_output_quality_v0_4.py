"""Adversarial, synthetic-only tests for v0.4 output consistency audit."""
from __future__ import annotations

import csv
import json

import pytest

from epah_diagnosis.output_quality_v0_4 import audit, _sha
from epah_diagnosis.review_pack_v0_4 import build as build_pack
from test_review_pack_v0_4 import fixture as atlas_fixture


def create_pack(tmp_path):
    atlas, registry, _, _ = atlas_fixture(tmp_path)
    output = tmp_path / "review"
    build_pack(atlas, registry, output)
    return atlas, output


def rehash(pack, name):
    path = pack / "manifest.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    receipt["outputs_sha256"][name] = _sha(pack / name)
    path.write_text(json.dumps(receipt))


def test_consistent_pack_passes_but_is_not_approved(tmp_path):
    atlas, output = create_pack(tmp_path)
    result = audit(output, atlas=atlas)
    assert result["indicator_slots"] == 2
    assert result["observations"] == 54
    assert result["html_csv_semantic_match"] is True
    assert result["visual_review_completed"] is False
    assert result["publication_allowed"] is False
    assert result["scientific_approval"] is False


def test_html_tamper_rejected_even_when_manifest_is_rehashed(tmp_path):
    _, output = create_pack(tmp_path)
    html = output / "review.html"
    before = html.read_text(encoding="utf-8")
    after = before.replace('"value":"1.235"', '"value":"2.235"', 1)
    assert after != before
    html.write_text(after, encoding="utf-8")
    rehash(output, "review.html")
    with pytest.raises(ValueError, match="HTML / CSV"):
        audit(output)


def test_pdf_tamper_blocks_on_digest(tmp_path):
    _, output = create_pack(tmp_path)
    with (output / "review.pdf").open("ab") as handle:
        handle.write(b"\nmodified")
    with pytest.raises(ValueError, match="checksum mismatch"):
        audit(output)


def test_rehashed_pdf_missing_indicator_rejected(tmp_path):
    _, output = create_pack(tmp_path)
    (output / "review.pdf").write_bytes(b"%PDF-1.7\nbroken")
    rehash(output, "review.pdf")
    with pytest.raises(ValueError, match="Unreadable review PDF"):
        audit(output)


def test_missingness_cannot_be_replaced_with_fake_zero(tmp_path):
    _, output = create_pack(tmp_path)
    path = output / "observations.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = reader.fieldnames
    row = next(r for r in rows if r["indicator_id"] == "H04")
    row["value"] = "0"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    rehash(output, "observations.csv")
    nested = output / "observations_manifest.json"
    contents = json.loads(nested.read_text(encoding="utf-8"))
    contents["outputs_sha256"]["observations.csv"] = _sha(path)
    nested.write_text(json.dumps(contents))
    rehash(output, "observations_manifest.json")
    with pytest.raises(ValueError, match="Partially available"):
        audit(output)


def test_missing_output_rejected(tmp_path):
    _, output = create_pack(tmp_path)
    (output / "review.html").unlink()
    with pytest.raises(ValueError, match="Missing or unsafe output"):
        audit(output)
