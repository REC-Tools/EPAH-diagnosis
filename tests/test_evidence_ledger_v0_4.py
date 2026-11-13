"""Step 8: synthetic provenance and adversarial cross-output integrity tests."""
import csv
import json

import pytest
from pypdf import PdfReader

from epah_diagnosis.atlas_observations_v0_4 import build as export, _sha
from epah_diagnosis.evidence_ledger_v0_4 import FILES
from epah_diagnosis.output_hub_v0_4 import build as hub
from epah_diagnosis.review_pack_v0_4 import build as review
from test_atlas_observations_v0_4 import inputs
from test_editorial_catalog_v0_4 import synthetic_atlas
from test_output_hub_v0_4 import prepare


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_full_snapshot_links_same_ledger_in_all_formats(tmp_path):
    atlas, registry = synthetic_atlas(tmp_path, with_values=True)
    target = review(atlas, registry, tmp_path / "review")
    portal = hub(atlas, target, tmp_path / "hub")
    ledger = load(target / FILES[0])
    assert ledger["indicator_slots"] == 16 and ledger["municipalities"] == 27
    assert ledger["atlas_data_sha256"] == _sha(atlas / "atlas_data.json")
    assert ledger["publication_allowed"] is ledger["scientific_approval"] is False
    with (target / "observations.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    for item, metric in zip(ledger["indicators"], load(atlas / "atlas_data.json")["indicators"]):
        assert item["source"] == metric["source"]
        assert item["reference_periods"] == metric["years"]
        assert item["population_reference"] == metric["editorial"]["population_reference"]
        assert item["present_count"] == 27 and item["missing_count"] == 0
        selected = [r for r in rows if r["indicator_id"] == item["indicator_id"]]
        assert all(r["source"] == item["source"] and r["evidence_ledger"] == FILES[0] for r in selected)
        for obs, row in zip(item["observations"], selected):
            assert obs["denominator"] == (row["denominator"] or None)
    for name in FILES:
        assert (target / name).read_bytes() == (portal / "sheets" / name).read_bytes()
        assert (target / name).read_bytes() == (portal / "review" / name).read_bytes()
    assert 'href="evidence_ledger.html"' in (target / "review.html").read_text()
    assert 'href="review/evidence_ledger.html"' in (portal / "index.html").read_text()
    report_text = "\n".join(p.extract_text() for p in PdfReader(target / "review.pdf").pages)
    assert "evidence_ledger.html" in report_text
    for pdf in (portal / "sheets" / "pdf").glob("*.pdf"):
        pages = PdfReader(pdf).pages
        assert len(pages) == 2
        assert "evidence_ledger.html" in pages[1].extract_text()
        assert any(a.get_object()["/A"]["/URI"] == "../evidence_ledger.html"
                   for a in pages[1]["/Annots"])
    combined = PdfReader(portal / "sheets" / "schede_27_comuni.pdf")
    assert len(combined.pages) == 54
    assert combined.pages[1]["/Annots"][0].get_object()["/A"]["/URI"] == "evidence_ledger.html"
    assert len(PdfReader(portal / "sintesi.pdf").pages) == 2
    for folder in (target, portal / "sheets", portal):
        receipt = load(folder / "manifest.json")
        for relative, digest in receipt["outputs_sha256"].items():
            assert _sha(folder / relative) == digest


def test_zero_and_absence_reproducible_without_originals(tmp_path):
    atlas, registry, payload, save = inputs(tmp_path)
    payload["municipalities"][0]["values"]["H46"]["value"] = 0
    save()
    one = export(atlas, registry, tmp_path / "one")
    two = export(atlas, registry, tmp_path / "two")
    for name in FILES:
        assert (one / name).read_bytes() == (two / name).read_bytes()
    present, absent = load(one / FILES[0])["indicators"]
    assert present["observations"][0]["presence"] == "observed"
    assert present["observations"][0]["denominator"] is None
    assert present["declared_input_evidence"]["preview_sha256"] == "a" * 64
    assert present["locally_verified_candidate_receipt"] is None
    assert absent["missing_count"] == 27
    assert absent["missing_reasons"] == {"not_acquired": 27}
    assert all(o["reference_period"] is None for o in absent["observations"])


@pytest.mark.parametrize("mutation", ["source", "period", "approval", "hash", "manifest"])
def test_rehashed_tampered_evidence_blocks_packaging(tmp_path, mutation):
    atlas, target = prepare(tmp_path)
    path = target / FILES[0]
    ledger = load(path)
    if mutation == "source":
        ledger["indicators"][0]["source"] = "invented"
    elif mutation == "period":
        ledger["indicators"][0]["reference_periods"] = ["1900"]
    elif mutation == "approval":
        ledger["scientific_approval"] = True
    elif mutation == "hash":
        ledger["atlas_data_sha256"] = "0" * 64
    else:
        inner = target / "observations_manifest.json"
        receipt = load(inner)
        receipt["inputs_sha256"]["atlas_manifest.json"] = "0" * 64
        inner.write_text(json.dumps(receipt))
    path.write_text(json.dumps(ledger))
    # Re-sign both local manifests: semantic comparisons must still reject this.
    inner = target / "observations_manifest.json"
    receipt = load(inner)
    receipt["outputs_sha256"][FILES[0]] = _sha(path)
    inner.write_text(json.dumps(receipt))
    manifest_file = target / "manifest.json"
    manifest = load(manifest_file)
    for name in (FILES[0], "observations_manifest.json"):
        manifest["outputs_sha256"][name] = _sha(target / name)
    manifest_file.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="ledger|binding"):
        hub(atlas, target, tmp_path / "blocked")
    assert not (tmp_path / "blocked").exists()


def test_v04_inventory_must_have_sixteen_slots(tmp_path):
    atlas, registry, payload, save = inputs(tmp_path)
    payload["schema_version"] = "0.4-technical-atlas"
    save()
    with pytest.raises(ValueError, match="16 indicator"):
        export(atlas, registry, tmp_path / "blocked")


@pytest.mark.parametrize("unsafe", ["../external", "/tmp/external", "charts/../../external", "charts\\external"])
def test_export_blocks_unsafe_manifest_paths(tmp_path, unsafe):
    atlas, registry, _, _ = inputs(tmp_path)
    path = atlas / "atlas_manifest.json"
    manifest = load(path)
    manifest["output_sha256"][unsafe] = "a" * 64
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Unsafe path"):
        export(atlas, registry, tmp_path / "blocked")


def test_export_blocks_symlink_with_matching_checksum(tmp_path):
    atlas, registry, _, _ = inputs(tmp_path)
    external = tmp_path / "external.txt"
    external.write_text("external evidence")
    (atlas / "linked.txt").symlink_to(external)
    path = atlas / "atlas_manifest.json"
    manifest = load(path)
    manifest["output_sha256"]["linked.txt"] = _sha(external)
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="integrity"):
        export(atlas, registry, tmp_path / "blocked")


def test_candidate_counts_and_receipts_are_preserved(tmp_path):
    from test_candidate_observations_v0_4 import fixture
    atlas, registry, previews, _, _ = fixture(tmp_path)
    result = export(atlas, registry, tmp_path / "enriched", candidate_previews=previews)
    ledger = load(result / FILES[0])
    h46 = next(i for i in ledger["indicators"] if i["indicator_id"] == "H46")
    assert h46["observations"][0]["numerator"] == "5.125"
    assert h46["observations"][0]["denominator"] == "102.500"
    assert h46["locally_verified_candidate_receipt"]["preview_sha256"] == h46["declared_input_evidence"]["preview_sha256"]
    assert h46["observations"][0]["counts_absence_reason"] is None


@pytest.mark.parametrize("field,value", [("source", "invented source"), ("reference_period", "1900")])
def test_rehashed_csv_metadata_divergence_is_rejected(tmp_path, field, value):
    atlas, target = prepare(tmp_path)
    csv_path = target / "observations.csv"
    with csv_path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames
        rows = list(reader)
    rows[0][field] = value
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    inner = target / "observations_manifest.json"
    receipt = load(inner)
    receipt["outputs_sha256"]["observations.csv"] = _sha(csv_path)
    inner.write_text(json.dumps(receipt))
    manifest_file = target / "manifest.json"
    manifest = load(manifest_file)
    for name in ("observations.csv", "observations_manifest.json"):
        manifest["outputs_sha256"][name] = _sha(target / name)
    manifest_file.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="source|period"):
        hub(atlas, target, tmp_path / "blocked")


def test_rehashed_embedded_atlas_ledger_must_match_snapshot(tmp_path):
    atlas, registry, _, _ = inputs(tmp_path)
    source = export(atlas, registry, tmp_path / "first-export")
    for name in FILES:
        (atlas / name).write_bytes((source / name).read_bytes())
    path = atlas / "atlas_manifest.json"
    manifest = load(path)
    manifest["output_sha256"].update({name: _sha(atlas / name) for name in FILES})
    path.write_text(json.dumps(manifest))
    export(atlas, registry, tmp_path / "matching-export")
    ledger_path = atlas / FILES[0]
    ledger = load(ledger_path)
    ledger["indicators"][0]["source"] = "invented source"
    ledger_path.write_text(json.dumps(ledger))
    manifest["output_sha256"][FILES[0]] = _sha(ledger_path)
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Atlas evidence ledger differs"):
        export(atlas, registry, tmp_path / "blocked")
