"""Review pack is generated exclusively from verified synthetic atlas fixtures."""
from __future__ import annotations

import csv
import json

import pytest

from epah_diagnosis.review_pack_v0_4 import build, _sha, _html
from test_atlas_observations_v0_4 import inputs


def fixture(tmp_path):
    atlas, registry, data, save = inputs(tmp_path)
    (atlas / "index.html").write_text("<html>synthetic atlas</html>", encoding="utf-8")
    manifest_file = atlas / "atlas_manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    manifest["output_sha256"]["index.html"] = _sha(atlas / "index.html")
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
    return atlas, registry, data, save


def test_pdf_html_csv_share_same_27_by_2_observations(tmp_path):
    atlas, registry, _, _ = fixture(tmp_path)
    out = tmp_path / "reviews" / "run"
    assert build(atlas, registry, out) == out
    assert (out / "review.pdf").read_bytes().startswith(b"%PDF")
    html = (out / "review.html").read_text(encoding="utf-8")
    assert "Fascicolo territoriale v0.4" in html
    assert "non acquisito" in html
    with (out / "observations.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 54
    assert {r["municipality_code"] for r in rows} == {f"001{i:03d}" for i in range(1, 28)}
    assert all(r["publication_allowed"] == "false" for r in rows)
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["indicator_slots"] == 2 and manifest["publication_allowed"] is False
    for filename, digest in manifest["outputs_sha256"].items():
        assert _sha(out / filename) == digest
    with pytest.raises(FileExistsError):
        build(atlas, registry, out)


def test_missing_or_tampered_atlas_html_blocks_entire_pack(tmp_path):
    atlas, registry, _, _ = fixture(tmp_path)
    (atlas / "index.html").write_text("modified without updating manifest", encoding="utf-8")
    out = tmp_path / "blocked"
    with pytest.raises(ValueError, match="integrity mismatch"):
        build(atlas, registry, out)
    assert not out.exists()


def test_missing_chart_reported_in_manifest_blocks_pack(tmp_path):
    atlas, registry, _, _ = fixture(tmp_path)
    manifest_file = atlas / "atlas_manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    manifest["output_sha256"]["charts/H46_map.png"] = "0" * 64
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="integrity mismatch"):
        build(atlas, registry, tmp_path / "blocked")


def test_unsafe_manifest_relative_path_rejected(tmp_path):
    atlas, registry, _, _ = fixture(tmp_path)
    manifest_file = atlas / "atlas_manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    manifest["output_sha256"]["../registry.csv"] = "a" * 64
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="Unsafe path"):
        build(atlas, registry, tmp_path / "blocked")


def test_browser_embedding_escapes_script_terminator():
    rows = [{
        "municipality": "</script><script>alert(1)</script>",
        "municipality_code": "001001", "reference_period": "2024",
        "value": "3", "unit": "%", "missing_reason": "", "numerator": "",
        "denominator": "", "indicator_id": "H46", "publication_allowed": "false",
    }]
    metrics = [{
        "indicator_id": "H46", "name": "Synthetic", "source": "source",
        "unit": "%", "available": True, "reference_periods": ["2024"],
    }]
    result = _html(rows, metrics)
    assert "<script>alert(1)</script>" not in result
    assert "\\u003c/script" in result


def test_input_overlap_rejected(tmp_path):
    atlas, registry, _, _ = fixture(tmp_path)
    with pytest.raises(ValueError, match="cannot overwrite"):
        build(atlas, registry, atlas / "nested")
