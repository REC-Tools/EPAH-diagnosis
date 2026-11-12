"""Synthetic H46/H50/H47 preview receipts: text precision and adversarial checks."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile

import pytest

from epah_diagnosis.atlas_observations_v0_4 import build, _sha
from epah_diagnosis.candidate_observations_v0_4 import enrich


def sha(data):
    return hashlib.sha256(data).hexdigest()


def csv_bytes(rows):
    with io.StringIO(newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        return stream.getvalue().encode()


def fixture(tmp_path):
    registry = tmp_path / "registry.csv"
    registry.write_text("municipality,istat_code\n" + "".join(
        f"Synthetic {i},001{i:03d}\n" for i in range(1, 28)))
    codes = [(f"001{i:03d}", f"Synthetic {i}") for i in range(1, 28)]
    atlas = tmp_path / "atlas"
    atlas.mkdir()
    previews = {}
    evidence = {}
    for kind in ("H46", "H50", "H47"):
        if kind == "H46":
            filename = "unemployment_15_plus_preview.csv"
            rows = [{
                "municipality_code": code, "municipality": name,
                "reference_year": "2024", "unemployed_15_plus": "5.125",
                "labour_force_15_plus": "102.500", "employed_15_plus": "97.375",
                "unemployment_rate_15_plus_pct": "5.00",
                "status": "technical_draft_do_not_publish",
            } for code, name in codes]
        elif kind == "H50":
            filename = "low_education_25_64_preview.csv"
            rows = [{
                "municipality_code": code, "municipality": name,
                "reference_year": "2024",
                "residents_below_lower_secondary_25_64": "5",
                "residents_25_64_total": "100",
                "share_below_lower_secondary_25_64_pct": "5.00",
                "status": "technical_draft_do_not_publish",
            } for code, name in codes]
        else:
            filename = "population_0_11_preview.csv"
            rows = [{
                "municipality_code": code, "municipality": name,
                "reference_date": "2026-01-01",
                "population_0_11": "5", "population_total": "100",
                "share_0_11_pct": "5.00",
                "status": "technical_draft_do_not_publish",
            } for code, name in codes]
        source = csv_bytes(rows)
        qa = {"status": "technical_draft_do_not_publish",
              "epah_inventory_id": kind}
        if kind == "H47":
            qa["sex_totals_verified"] = True
        qa_bytes = json.dumps(qa).encode()
        manifest = {
            "status": "technical_draft_do_not_publish",
            "scientific_approval": False,
            "municipality_registry_sha256": _sha(registry),
            "outputs_sha256": {filename: sha(source), "qa.json": sha(qa_bytes)},
        }
        if kind == "H46":
            manifest.update(canonical_data_modified=False, official_source_mapping_verified=False)
        elif kind == "H50":
            manifest.update(canonical_data_modified=False, normalized_export_mapping_verified=False)
        else:
            manifest.update(canonical_registry_modified=False,
                            input_original_zip_sha256="b" * 64)
        if kind != "H47":
            folder = tmp_path / kind
            folder.mkdir()
            (folder / filename).write_bytes(source)
            (folder / "qa.json").write_bytes(qa_bytes)
            (folder / "manifest.json").write_text(json.dumps(manifest))
            previews[kind] = folder
            evidence[kind] = {"preview_sha256": sha(source)}
        else:
            source_observation = {"original_zip_sha256": "b" * 64,
                                  "scientific_approval": False}
            audited = {
                "h47_preview/population_0_11_preview.csv": source,
                "h47_preview/qa.json": qa_bytes,
                "h47_preview/manifest.json": json.dumps(manifest).encode(),
                "source_observation.json": json.dumps(source_observation).encode(),
            }
            audit = {"schema_version": "2.0",
                     "audited_files_sha256": {key: sha(value) for key, value in audited.items()},
                     "original_source_registry_sha256": _sha(registry),
                     "original_source_zip_sha256": "b" * 64,
                     "status": "independently_reproduced_technical_only",
                     "municipality_coverage": "27/27", "scientific_approval": False}
            zip_path = tmp_path / "H47.zip"
            with zipfile.ZipFile(zip_path, "w") as handle:
                for name, content in audited.items():
                    handle.writestr(name, content)
                handle.writestr("h47_independent_reproduction_audit.json", json.dumps(audit))
            previews[kind] = zip_path
            evidence[kind] = {"preview_sha256": sha(source),
                              "input_artifact_sha256": _sha(zip_path)}
    data = {
        "status": "technical_draft_do_not_publish", "publication_allowed": False,
        "no_composite_score": True, "municipality_count": 27,
        "indicators": [{
            "id": kind, "name": kind + " synthetic", "unit": "%", "family": "Synthetic",
            "source": "synthetic", "evidence": "technical_v0_3_candidate",
            "available": True, "count": 27,
            "years": ["2026-01-01" if kind == "H47" else "2024"],
        } for kind in ("H46", "H50", "H47")],
        "municipalities": [{
            "code": code, "name": name,
            "values": {kind: {
                "value": 5.0, "year": "2026-01-01" if kind == "H47" else "2024",
            } for kind in ("H46", "H50", "H47")},
        } for code, name in codes],
    }
    data_file = atlas / "atlas_data.json"
    data_file.write_text(json.dumps(data))
    manifest = {
        "status": "technical_draft_do_not_publish", "publication_allowed": False,
        "municipalities": 27, "indicator_slots": 3,
        "indicators_available": ["H46", "H50", "H47"], "indicators_pending": [],
        "registry_sha256": _sha(registry),
        "output_sha256": {"atlas_data.json": _sha(data_file)},
        "input_evidence": evidence,
    }
    (atlas / "atlas_manifest.json").write_text(json.dumps(manifest))
    return atlas, registry, previews, evidence, data


def test_three_candidate_adapters_preserve_counts_and_decimal_text(tmp_path):
    atlas, registry, previews, _, _ = fixture(tmp_path)
    target = tmp_path / "out"
    build(atlas, registry, target, candidate_previews=previews)
    with (target / "observations.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 81
    assert rows[0]["numerator"] == "5.125"
    assert rows[0]["denominator"] == "102.500"
    assert rows[0]["value"] == "5.00"
    assert rows[27]["numerator"] == "5"
    assert rows[54]["denominator"] == "100"
    assert rows[54]["reference_period"] == "2026-01-01"
    manifest = json.loads((target / "manifest.json").read_text())
    assert manifest["candidate_preview_integrity_receipts"]["H47"]["independent_reproduction_receipt_checked"]
    metadata = json.loads((target / "metadata.json").read_text())
    assert metadata["enriched_candidates"] == ["H46", "H47", "H50"]


def test_preview_with_valid_counts_but_wrong_atlas_hash_fails(tmp_path):
    atlas, registry, previews, _, _ = fixture(tmp_path)
    target = previews["H46"] / "unemployment_15_plus_preview.csv"
    target.write_bytes(target.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="receipt mismatch"):
        build(atlas, registry, tmp_path / "blocked", candidate_previews={"H46": previews["H46"]})
    assert not (tmp_path / "blocked").exists()


def test_malformed_or_divergent_counts_are_rejected(tmp_path):
    atlas, registry, previews, evidence, data = fixture(tmp_path)
    with pytest.raises(ValueError, match="count/rate"):
        source = (previews["H46"] / "unemployment_15_plus_preview.csv").read_text()
        source = source.replace("5.125", "5.100")
        preview_bytes = source.encode()
        folder = previews["H46"]
        (folder / "unemployment_15_plus_preview.csv").write_bytes(preview_bytes)
        mpath = folder / "manifest.json"
        manifest = json.loads(mpath.read_text())
        manifest["outputs_sha256"]["unemployment_15_plus_preview.csv"] = sha(preview_bytes)
        mpath.write_text(json.dumps(manifest))
        new_evidence = {"preview_sha256": sha(preview_bytes)}
        enrich("H46", folder,
               {r["code"]: r["name"] for r in data["municipalities"]},
               _sha(registry), new_evidence,
               {r["code"]: r for r in data["municipalities"]})


def test_h47_receipt_fails_if_zip_is_repacked(tmp_path):
    atlas, registry, previews, _, _ = fixture(tmp_path)
    with zipfile.ZipFile(previews["H47"], "a") as handle:
        handle.writestr("extra.txt", "changed")
    with pytest.raises(ValueError, match="ZIP does not match"):
        build(atlas, registry, tmp_path / "blocked", candidate_previews={"H47": previews["H47"]})


def test_candidate_input_must_match_available_metric(tmp_path):
    atlas, registry, previews, _, _ = fixture(tmp_path)
    with pytest.raises(ValueError, match="available H46/H47/H50"):
        build(atlas, registry, tmp_path / "blocked", candidate_previews={"H03": previews["H46"]})


def test_no_preview_keeps_counts_blank(tmp_path):
    atlas, registry, _, _, _ = fixture(tmp_path)
    target = tmp_path / "empty"
    build(atlas, registry, target)
    with (target / "observations.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert all(not row["numerator"] and not row["denominator"] for row in rows)
