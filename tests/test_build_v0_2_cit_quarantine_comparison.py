"""Purely synthetic regression for internal 26-town CIT comparison."""
import csv
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "cit_quarantine_join_v02",
    ROOT / "scripts/build_v0_2_cit_quarantine_comparison.py"
)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)
REGISTRY = ROOT / "data/municipalities.csv"


def make_sources(tmp_path):
    with REGISTRY.open(encoding="utf-8-sig", newline="") as file:
        towns = list(csv.DictReader(file))
    assert len(towns) == 27
    dirs = []
    for mode, filename in (("fuel", "cit_fuel_27.csv"),
                           ("age", "cit_generator_age_27.csv")):
        folder = tmp_path / ("source_" + mode)
        folder.mkdir()
        rows = []
        for town in towns:
            missing = town["istat_code"] == "001199"
            common = {"municipality": town["municipality"],
                      "istat_code": town["istat_code"],
                      "generator_groups_total": "" if missing else "10",
                      "snapshot_date": "2026-10-30",
                      "observation_status": (
                          "source_conflict_quarantined" if missing
                          else "technical_observation")}
            if mode == "fuel":
                common.update({
                    "classified_groups": "" if missing else "10",
                    "unclassified_groups": "" if missing else "0",
                    "natural_gas_groups": "" if missing else "7",
                    "diesel_groups": "" if missing else "2",
                    "lpg_groups": "" if missing else "1",
                    "solid_fuels_groups": "" if missing else "0",
                    "electricity_groups": "" if missing else "0",
                    "other_groups": "" if missing else "0",
                    "diesel_lpg_share_pct": "" if missing else "30.00",
                    "denominator": "classified_generator_groups"
                })
            else:
                common.update({
                    "groups_with_known_year": "" if missing else "10",
                    "groups_with_unknown_year": "" if missing else "0",
                    "groups_aged_20_or_more": "" if missing else "3",
                    "groups_ambiguous_age": "" if missing else "2",
                    "older_generator_share_pct": "" if missing else "30.00",
                    "older_upper_bound_share_pct": "" if missing else "50.00",
                    "age_metric": "conservative_lower_bound_for_20_years",
                    "denominator": "generator_groups_with_known_installation_year",
                })
            rows.append(common)
        path = folder / filename
        with path.open("w", encoding="utf-8", newline="") as file:
            w = csv.DictWriter(file, fieldnames=list(rows[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        conflict = {
            "istat_code": "001199", "status": "conflicting_counts",
            "source_records": [
                {"line": 1, "counts": {"gasolio": 1}},
                {"line": 2, "counts": {"gasolio": 2}},
            ]
        }
        qa = {
            "qa_status": "technical_incomplete_do_not_publish",
            "validated_for_release": False,
            "source_matches_user_inspection_hash": True,
            "source_csv_sha256": MOD.EXPECTED_SOURCE_HASHES[mode],
            "registry_csv_sha256": MOD.sha256(REGISTRY),
            "output_csv_sha256": MOD.sha256(path),
            "municipalities_expected": 27,
            "municipalities_with_generator_data": 26,
            "quarantined_municipalities": ["001199"],
            "source_schema": {
                "conflict_policy": "quarantine_without_resolving",
                "quarantined_duplicate_conflicts": [conflict],
            },
            "indicator_id": ("cit_diesel_lpg_generator_share" if mode == "fuel"
                             else "cit_older_generator_share"),
            "snapshot_date_operator_reported": "2026-10-30",
            "age_metric": "conservative_lower_bound_for_20_years"
                          if mode == "age" else None,
            "older_years_threshold": 20 if mode == "age" else None,
            "age_interval_uncertainty_groups": 52 if mode == "age" else None,
        }
        (folder / "cit_qa.json").write_text(json.dumps(qa), encoding="utf-8")
        review = {
            "status": "human_source_review_required",
            "quarantined_municipalities": ["001199"],
            "source_csv_sha256": MOD.EXPECTED_SOURCE_HASHES[mode],
            "conflicts": [conflict],
        }
        (folder / "cit_conflicts_for_review.json").write_text(
            json.dumps(review), encoding="utf-8"
        )
        dirs.append(folder)
    return dirs


def test_internal_26_town_comparison_no_missing_as_zero(tmp_path):
    fuel, age = make_sources(tmp_path)
    out = tmp_path / "joined"
    assert MOD.create_review(fuel, age, REGISTRY, out) == out
    with (out / "cit_26_municipality_technical_comparison.csv").open(
            encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 26
    assert all(r["istat_code"] != "001199" for r in rows)
    report = json.loads((out / "cit_26_qa_summary.json").read_text())
    assert report["status"] == "technical_QA_only_incomplete_do_not_publish"
    assert report["valid_municipalities"] == 26
    assert report["age_uncertainty_groups"] == 52
    assert report["fuel"]["pooled_pct"] == 30
    assert report["age_minimum"]["pooled_pct"] == 30
    assert report["age_pooled_upper_pct"] == 50
    review = json.loads((out / "cit_pont_canavese_source_review.json").read_text())
    assert review["fuel"]["conflicts"][0]["istat_code"] == "001199"
    assert not any(name.endswith(".png") or name.endswith(".pdf")
                   for name in (p.name for p in out.iterdir()))
    with pytest.raises(FileExistsError):
        MOD.create_review(fuel, age, REGISTRY, out)


def test_conflict_cannot_have_a_fabricated_numeric_value(tmp_path):
    fuel, age = make_sources(tmp_path)
    path = fuel / "cit_fuel_27.csv"
    csv_text = path.read_text(encoding="utf-8").replace(
        "source_conflict_quarantined", "technical_observation", 1)
    path.write_text(csv_text, encoding="utf-8")
    qa_path = fuel / "cit_qa.json"
    qa = json.loads(qa_path.read_text())
    qa["output_csv_sha256"] = MOD.sha256(path)
    qa_path.write_text(json.dumps(qa), encoding="utf-8")
    with pytest.raises(ValueError, match="quarantined value"):
        MOD.create_review(fuel, age, REGISTRY, tmp_path / "no-release")


def test_wrong_original_hash_fails_closed(tmp_path):
    fuel, age = make_sources(tmp_path)
    qa_path = age / "cit_qa.json"
    qa = json.loads(qa_path.read_text())
    qa["source_csv_sha256"] = "f" * 64
    qa_path.write_text(json.dumps(qa), encoding="utf-8")
    with pytest.raises(ValueError, match="not a verified"):
        MOD.create_review(fuel, age, REGISTRY, tmp_path / "invalid")


def test_inconsistent_age_interval_total_fails(tmp_path):
    fuel, age = make_sources(tmp_path)
    qa_path = age / "cit_qa.json"
    qa = json.loads(qa_path.read_text())
    qa["age_interval_uncertainty_groups"] = 0
    qa_path.write_text(json.dumps(qa), encoding="utf-8")
    with pytest.raises(ValueError, match="uncertainty fails"):
        MOD.create_review(fuel, age, REGISTRY, tmp_path / "bad")
