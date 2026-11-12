"""Step 4: editorial semantics must not rewrite units, source data or approval."""
from __future__ import annotations

from copy import deepcopy
import json

import pytest
from pypdf import PdfReader

from epah_diagnosis.editorial_catalog_v0_4 import (
    CATALOG, CANONICAL, CANDIDATES, VERSION, annotate_v04, snapshot,
)
from epah_diagnosis.atlas_observations_v0_4 import _sha
from epah_diagnosis.municipality_sheets_v0_4 import build as build_sheets
from epah_diagnosis.output_hub_v0_4 import build as build_hub
from epah_diagnosis.review_pack_v0_4 import build as build_review
from test_v0_4_visual_atlas import mod as atlas_module
from test_atlas_observations_v0_4 import inputs


def definitions():
    values = atlas_module.v3.METRICS + atlas_module.NEW
    return [{
        "id": m.id, "name": m.name, "source": m.source,
        "unit": m.unit, "family": m.family, "description": m.description,
        "available": False, "count": 0, "years": [], "evidence": "not_available",
    } for m in values]


def test_all_sixteen_slots_harmonized_without_changing_original_fields():
    original = definitions()
    before = deepcopy(original)
    enriched = annotate_v04(original)
    assert original == before
    assert len(enriched) == len(CATALOG) == 16
    assert [m["id"] for m in enriched] == list(CANONICAL) + list(CANDIDATES)
    for a, b in zip(original, enriched):
        assert all(b[key] == a[key] for key in a)
        editorial = b["editorial"]
        assert editorial["publication_allowed"] is False
        assert editorial["editorial_review"] == "technical_only_not_scientifically_approved"
        assert all(editorial[k].strip() for k in (
            "role", "population_reference", "short_population_reference",
            "operational_meaning", "interpretation_limit", "epah_dimension",
        ))
    receipt = snapshot(enriched)
    assert receipt["schema_version"] == VERSION
    assert receipt["scientific_approval"] is False
    assert receipt["publication_allowed"] is False
    assert receipt["semantic_only"] is True
    assert len(receipt["indicators"]) == 16
    assert len(receipt["indicators"][0]["editorial"]["population_reference"]) > 3
    assert "original" not in receipt


def test_h03_and_normative_gg_remain_distinct():
    assert "DPR 412" in CATALOG["heating_degree_days"]["operational_meaning"]
    assert "NON" in CATALOG["heating_degree_days"]["interpretation_limit"]
    assert "Eurostat 15/18" in CATALOG["H03"]["operational_meaning"]
    assert "Eurostat 24/21" in CATALOG["H04"]["operational_meaning"]
    assert "forze di lavoro" in CATALOG["H46"]["operational_meaning"]
    assert "APE residenziali validi" in CATALOG["H05"]["population_reference"]
    assert "Non equivale a case vuote" in CATALOG["ADD-HOUSING-01"]["interpretation_limit"]


@pytest.mark.parametrize("type_of_error", ["missing", "unknown", "reordered", "nonboolean"])
def test_invalid_atlas_editorial_inventory_blocks(type_of_error):
    source = definitions()
    if type_of_error == "missing":
        source.pop()
    elif type_of_error == "unknown":
        source[0]["id"] = "unreviewed-unknown"
    elif type_of_error == "reordered":
        source[0], source[1] = source[1], source[0]
    else:
        source[0]["available"] = "validated"
    with pytest.raises(ValueError, match="editorial|metadata"):
        annotate_v04(source)


def test_silently_edited_crosswalk_refused():
    enriched = annotate_v04(definitions())
    enriched[0]["editorial"]["population_reference"] = "invented household units"
    with pytest.raises(ValueError, match="Editorial crosswalk"):
        snapshot(enriched)


def synthetic_atlas(tmp_path, *, with_values=False):
    atlas, registry, payload, _ = inputs(tmp_path)
    metrics = definitions()
    for metric in metrics:
        if with_values:
            metric.update(available=True, count=27, years=["2024"],
                          evidence="technical_synthetic_only")
    payload["indicators"] = annotate_v04(metrics)
    payload["schema_version"] = "0.4-technical-atlas"
    payload["editorial_catalog_version"] = VERSION
    for town in payload["municipalities"]:
        town["values"] = {}
        if with_values:
            for metric in metrics:
                mid = metric["id"]
                obs = {"value": "B" if mid == "snai_classification" else 5.0,
                       "year": "2024"}
                if mid in ("H05", "ADD-HOUSING-01"):
                    obs.update(numerator="1", denominator="20",
                               universe=("valid_residential_ape_certificates" if mid == "H05"
                                         else "census_dwellings_2023"))
                town["values"][mid] = obs
    data_file = atlas / "atlas_data.json"
    data_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    (atlas / "index.html").write_text("<html>technical synthetic atlas</html>", encoding="utf-8")
    (atlas / "README_REVIEW.txt").write_text("test only", encoding="utf-8")
    (atlas / "catalogo_editoriale.json").write_text(
        json.dumps(snapshot(payload["indicators"]), ensure_ascii=False), encoding="utf-8")
    manifest = {
        "status": "technical_draft_do_not_publish",
        "publication_allowed": False, "scientific_approval": False,
        "no_composite_score": True, "municipalities": 27,
        "indicator_slots": 16,
        "registry_sha256": _sha(registry),
        "indicators_available": [m["id"] for m in metrics if m["available"]],
        "indicators_pending": [m["id"] for m in metrics if not m["available"]],
        "input_evidence": {},
        "output_sha256": {
            p.name: _sha(p) for p in atlas.iterdir()
            if p.is_file() and p.name not in ("atlas_manifest.json", "README_REVIEW.txt")
        },
    }
    (atlas / "atlas_manifest.json").write_text(json.dumps(manifest))
    return atlas, registry


@pytest.mark.parametrize("with_values", [False, True])
def test_16_slot_html_pdf_sheets_and_portal_share_catalog(tmp_path, with_values):
    atlas, registry = synthetic_atlas(tmp_path, with_values=with_values)
    review = tmp_path / "review"
    build_review(atlas, registry, review)
    atlas_cat = snapshot(json.loads((atlas / "atlas_data.json").read_text())["indicators"])
    review_cat = json.loads((review / "catalogo_editoriale.json").read_text())
    assert atlas_cat == review_cat
    assert "residenti" in review_cat["indicators"][0]["editorial"]["operational_meaning"].lower()
    html = (review / "review.html").read_text(encoding="utf-8")
    assert '"population_reference"' in html
    assert "interpretation" in html
    pdf = PdfReader(str(review / "review.pdf"))
    report_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    assert "Ruolo:" in report_text
    assert "Universo:" in report_text
    assert "Definizione:" in report_text
    sheets = tmp_path / "sheets"
    build_sheets(atlas, review, sheets)
    assert len(PdfReader(str(sheets / "schede_27_comuni.pdf")).pages) == 54
    assert json.loads((sheets / "catalogo_editoriale.json").read_text()) == atlas_cat
    if with_values:
        first = PdfReader(str(sheets / "pdf" / "001001.pdf"))
        assert "Universo:" in (first.pages[0].extract_text() or "")
    hub = tmp_path / "hub"
    build_hub(atlas, review, hub)
    portal = (hub / "index.html").read_text(encoding="utf-8")
    assert 'href="review/catalogo_editoriale.json"' in portal
    assert (hub / "review" / "catalogo_editoriale.json").read_bytes() == (
        review / "catalogo_editoriale.json").read_bytes()
    assert json.loads((hub / "manifest.json").read_text())["publication_allowed"] is False


def test_rehashed_mismatched_editorial_receipt_blocks_hub(tmp_path):
    atlas, registry = synthetic_atlas(tmp_path)
    review = tmp_path / "review"
    build_review(atlas, registry, review)
    path = review / "catalogo_editoriale.json"
    catalog = json.loads(path.read_text(encoding="utf-8"))
    catalog["indicators"][0]["editorial"]["population_reference"] = "invention"
    path.write_text(json.dumps(catalog), encoding="utf-8")
    receipt = review / "manifest.json"
    manifest = json.loads(receipt.read_text(encoding="utf-8"))
    manifest["outputs_sha256"]["catalogo_editoriale.json"] = _sha(path)
    receipt.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="editorial crosswalk"):
        build_hub(atlas, review, tmp_path / "blocked")
    assert not (tmp_path / "blocked").exists()
