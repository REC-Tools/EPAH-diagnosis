"""Synthetic, adversarial validation of the v0.4 observation export."""
import csv
import json

import pytest

from epah_diagnosis.atlas_observations_v0_4 import build, _sha


def inputs(tmp_path):
    atlas = tmp_path / "atlas"
    atlas.mkdir(parents=True)
    registry = tmp_path / "registry.csv"
    registry.write_text("municipality,istat_code\n" + "".join(
        f"Synthetic {i},001{i:03d}\n" for i in range(1, 28)), encoding="utf-8")
    payload = {
        "status": "technical_draft_do_not_publish", "publication_allowed": False,
        "no_composite_score": True, "municipality_count": 27,
        "indicators": [
            {"id": "H46", "name": "Synthetic unemployment", "unit": "%", "family": "Economia",
             "source": "Synthetic source", "evidence": "technical_v0_3_candidate",
             "available": True, "count": 27, "years": ["2024"]},
            {"id": "H04", "name": "Pending climate", "unit": "deg", "family": "Clima",
             "source": "Not acquired", "evidence": "not_available",
             "available": False, "count": 0, "years": []},
        ],
        "municipalities": [
            {"code": f"001{i:03d}", "name": f"Synthetic {i}",
             "values": {"H46": {"value": 1.234 + i / 1000, "year": "2024"}}}
            for i in range(1, 28)
        ],
    }
    data_file = atlas / "atlas_data.json"
    manifest_file = atlas / "atlas_manifest.json"

    def save():
        data_file.write_text(json.dumps(payload), encoding="utf-8")
        manifest_file.write_text(json.dumps({
            "status": "technical_draft_do_not_publish", "publication_allowed": False,
            "municipalities": 27, "indicator_slots": 2,
            "indicators_available": ["H46"], "indicators_pending": ["H04"],
            "registry_sha256": _sha(registry),
            "output_sha256": {"atlas_data.json": _sha(data_file)},
            "input_evidence": {"H46": {"preview_sha256": "a" * 64}},
        }), encoding="utf-8")
    save()
    return atlas, registry, payload, save


def test_export_produces_tidy_table_and_explicit_absence(tmp_path):
    atlas, registry, _, _ = inputs(tmp_path)
    target = tmp_path / "out"
    assert build(atlas, registry, target) == target
    with (target / "observations.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 54
    assert len({(r["municipality_code"], r["indicator_id"]) for r in rows}) == 54
    assert float(rows[0]["value"]) == pytest.approx(1.235)
    assert rows[0]["numerator"] == rows[0]["denominator"] == ""
    assert rows[0]["publication_allowed"] == "false"
    assert rows[27]["missing_reason"] == "not_acquired"
    assert rows[27]["value"] == ""
    metadata = json.loads((target / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["publication_allowed"] is False
    assert "original_decimal_precision" in metadata["not_preserved_in_source"]
    receipt = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    assert receipt["outputs_sha256"]["observations.csv"] == _sha(target / "observations.csv")
    with pytest.raises(FileExistsError):
        build(atlas, registry, target)


@pytest.mark.parametrize("mutation,expected", [
    (lambda p: p["municipalities"].pop(), "municipality"),
    (lambda p: p["municipalities"][1].update(code=p["municipalities"][0]["code"]), "municipality"),
    (lambda p: p["municipalities"][0]["values"]["H46"].update(value=float("nan")), "invalid numeric"),
    (lambda p: p["municipalities"][0]["values"]["H46"].update(value=101.0), "invalid numeric"),
    (lambda p: p["municipalities"][0]["values"]["H46"].update(year="2023"), "reference-period"),
    (lambda p: p["municipalities"][0]["values"].update(H04={"value": 1, "year": "2024"}), "coverage"),
    (lambda p: p["municipalities"][0]["values"].pop("H46"), "coverage"),
])
def test_invalid_inputs_fail_before_writing(tmp_path, mutation, expected):
    atlas, registry, payload, save = inputs(tmp_path)
    mutation(payload)
    save()
    with pytest.raises(ValueError, match=expected):
        build(atlas, registry, tmp_path / "blocked")
    assert not (tmp_path / "blocked").exists()


def test_tampered_input_or_registry_is_rejected(tmp_path):
    atlas, registry, _, _ = inputs(tmp_path)
    (atlas / "atlas_data.json").write_text((atlas / "atlas_data.json").read_text() + "\n")
    with pytest.raises(ValueError, match="checksum"):
        build(atlas, registry, tmp_path / "blocked")
    atlas, registry, _, _ = inputs(tmp_path / "another")
    registry.write_text(registry.read_text() + "\n")
    with pytest.raises(ValueError, match="checksum"):
        build(atlas, registry, tmp_path / "blocked2")
