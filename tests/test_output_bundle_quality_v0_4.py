"""Step 9 end-to-end fixtures: synthetic ingestion, real v0.4 renderers and packager."""
from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import shutil

import pytest
from pypdf import PdfReader, PdfWriter

from epah_diagnosis.output_bundle_quality_v0_4 import audit_bundle, _links, _media
from epah_diagnosis.output_hub_v0_4 import build as build_hub
from epah_diagnosis.output_quality_v0_4 import _sha
from epah_diagnosis.review_pack_v0_4 import build as build_review
from epah_diagnosis.release_artifacts import NUMERIC_FIELDS
from test_v0_4_visual_atlas import mod


@pytest.fixture(scope="module")
def synthetic_hub(tmp_path_factory):
    root = tmp_path_factory.mktemp("SYNTHETIC-step9")
    registry = root / "registry.csv"
    names = {f"001{i:03d}": ("Synthetic Vallè 01" if i == 1 else f"Synthetic Comune {i:02d}")
             for i in range(1, 28)}
    registry.write_text("municipality,istat_code\n" + "".join(
        f"{name},{code}\n" for code, name in names.items()), encoding="utf-8")
    bundle = root / "SYNTHETIC-input"
    bundle.mkdir()
    features = []
    for i, (code, name) in enumerate(names.items()):
        x, y = 7 + (i % 9) * .04, 45 + (i // 9) * .04
        features.append({"type": "Feature", "properties": {
            "municipality_code": code, "municipality": name, "snai_class": "ABCDEF"[i % 6],
            **{field: float(i) for field in NUMERIC_FIELDS}}, "geometry": {
                "type": "Polygon", "coordinates": [[[x, y], [x+.035, y],
                    [x+.035, y+.035], [x, y+.035], [x, y]]]}})
    (bundle / "municipality_profile.geojson").write_text(json.dumps({
        "type": "FeatureCollection", "features": features}), encoding="utf-8")

    def synthetic_ingestion(_bundle, out, **kwargs):
        # Replace only unavailable original/pilot ingestion. HTML, PNG/SVG,
        # labels, CSV, ledger, PDFs, sheets and packaging use production code.
        out.mkdir()
        (out / "charts").mkdir()
        metrics = []
        for metric in mod.v3.METRICS:
            available = metric.id != "H03"
            period = "2026-01-01" if metric.id == "H47" else "2024"
            metrics.append({"id": metric.id, "name": metric.name, "unit": metric.unit,
                "family": metric.family, "source": metric.source,
                "description": "SYNTHETIC TEST ONLY. " + metric.description,
                "available": available, "count": 27 if available else 0,
                "years": [period] if available else [],
                "evidence": "technical_synthetic_only" if available else "not_available"})
        towns = []
        for index, (code, name) in enumerate(names.items()):
            towns.append({"code": code, "name": name, "values": {
                m["id"]: {"value": "ABCDEF"[index % 6] if m["unit"] == "categoria" else float(index),
                           "year": m["years"][0]} for m in metrics if m["available"]}})
        payload = {"status": mod.STATUS, "publication_allowed": False,
            "scientific_approval": False, "no_composite_score": True,
            "municipality_count": 27, "synthetic_fixture": True,
            "identical_numeric_series": [], "indicators": metrics, "municipalities": towns}
        data = out / "atlas_data.json"
        data.write_text(json.dumps(payload), encoding="utf-8")
        (out / "index.html").write_text(mod.v3._atlas_html(payload), encoding="utf-8")
        (out / "README_REVIEW.txt").write_text("SYNTHETIC ONLY - NON PUBBLICARE\n")
        (out / "atlas_manifest.json").write_text(json.dumps({
            "status": mod.STATUS, "publication_allowed": False, "scientific_approval": False,
            "registry_sha256": _sha(registry), "input_evidence": {},
            "output_sha256": {"atlas_data.json": _sha(data)}}))

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(mod.v3, "METRICS", tuple(replace(metric, source="SYNTHETIC TEST ONLY")
                                              for metric in mod.v3.METRICS))
        patch.setattr(mod, "NEW", tuple(replace(metric, source="SYNTHETIC TEST ONLY")
                                       for metric in mod.NEW))
        patch.setattr(mod.v3, "build", synthetic_ingestion)
        atlas = mod.build(bundle, root / "atlas", registry_path=registry)
    review = build_review(atlas, registry, root / "review")
    hub = build_hub(atlas, review, root / "hub")
    destination = os.environ.get("EPAH_SYNTHETIC_QA_DIR")
    if destination:
        # Explicit opt-in for browser/visual review; never overwrite an existing artifact.
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
