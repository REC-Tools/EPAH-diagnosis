"""Synthetic analytical regressions; never infer territorial poverty prevalence."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

from epah_diagnosis.provenance import sha256_file
from epah_diagnosis.thematic_scenarios import THEMES, analyse, competition_ranks, normalise


def towns():
    fields = {field for _, indicators in THEMES.values() for field in indicators}
    return [{"code": f"001{i:03d}", "name": f"Synthetic {i:02d}",
             "values": {field: {"value": float(i), "year": "2025"} for field in fields}}
            for i in range(1,28)]


def test_ties_are_shared_and_constant_series_are_neutral():
    assert normalise([10,10,30]) == [25,25,100]
    assert normalise([7,7,7]) == [50,50,50]
    assert competition_ranks([100,100,50]) == [1,1,3]


def test_no_global_ranking_without_explicit_opt_in():
    result = analyse(towns(), ["economic", "accessibility"])
    assert not result["global_scenario_enabled"]
    assert result["global_sensitivity_scenarios"] == []
    assert "global_selected_themes" not in result["municipalities"][0]
    assert result["publication_allowed"] is False
    assert result["contains_composite_scores"] is True
    assert "no_composite_score" not in result


def test_identical_access_series_share_one_weight_instead_of_double_counting():
    data = towns()
    for i, row in enumerate(data):
        row["values"]["dea_accessibility"]["value"] = 27-i
        row["values"]["upper_secondary_accessibility"]["value"] = i
        row["values"]["rail_accessibility"]["value"] = i
    result = analyse(data, ["accessibility"])
    definition = result["themes"]["accessibility"]
    assert definition["indicator_groups"] == [["dea_accessibility"],
        ["upper_secondary_accessibility", "rail_accessibility"]]
    assert definition["group_weights"] == [.5,.5]
    assert all(abs(r["themes"]["accessibility"]["percentile_score"]-50) < 1e-9
               for r in result["municipalities"])
    assert all(r["themes"]["accessibility"]["percentile_rank"] == 1 for r in result["municipalities"])


def test_global_equal_theme_weight_and_sensitivity_are_explicit():
    data = towns()
    for row in data:
        row["values"]["income_vulnerability"]["value"] *= 2
        row["values"]["dea_accessibility"]["value"] = 28-row["values"]["dea_accessibility"]["value"]
        row["values"]["upper_secondary_accessibility"]["value"] = row["values"]["dea_accessibility"]["value"]
        row["values"]["rail_accessibility"]["value"] = row["values"]["dea_accessibility"]["value"]
    result = analyse(data, ["economic", "accessibility"], global_scenario=True)
    assert len(result["global_sensitivity_scenarios"]) == 10
    assert result["global_sensitivity_scenarios"][0]["theme_weights"] == {"economic":.5,"accessibility":.5}
    for row in result["municipalities"]:
        expected = sum(t["percentile_score"] for t in row["themes"].values())/2
        global_row = row["global_selected_themes"]
        assert global_row["baseline_score"] == pytest.approx(expected)
        assert global_row["best_scenario_rank"] <= global_row["baseline_rank"] <= global_row["worst_scenario_rank"]
    assert result["spearman"]["H46"]["dea_accessibility"] == pytest.approx(-1)


@pytest.mark.parametrize("bad", [None, float("nan"), float("inf"), -1, 101, True])
def test_missing_suppressed_or_invalid_values_are_never_filled(bad):
    data = towns()
    data[0]["values"]["H46"]["value"] = bad
    with pytest.raises(ValueError):
        analyse(data, ["economic"])


def test_period_and_scope_checks():
    data = towns()
    data[0]["values"]["H03"]["year"] = "2024"
    with pytest.raises(ValueError, match="Mixed municipal periods"):
        analyse(data,["climate"])
    data = towns()
    for row in data:
        row["values"]["H04"]["year"] = "2024"
    with pytest.raises(ValueError, match="same calendar year"):
        analyse(data,["climate"])
    with pytest.raises(ValueError, match="27 unique"):
        analyse(towns()[:-1],["economic"])


def test_analysis_is_order_invariant_and_does_not_modify_source():
    data = towns()
    original = copy.deepcopy(data)
    assert analyse(data,["economic"]) == analyse(list(reversed(data)),["economic"])
    assert data == original


def test_constant_correlation_is_undefined_not_zero():
    data = towns()
    for row in data:
        row["values"]["H46"]["value"] = 20
    result = analyse(data,["economic"])
    assert result["spearman"]["H46"]["H50"] is None
    assert "H46" in result["constant_indicators"]


def builder():
    spec = importlib.util.spec_from_file_location("thematic_builder", Path(__file__).resolve().parents[1]/"scripts/build_v0_4_thematic_scenarios.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_verified_atlas_build_and_tampering_rejected(tmp_path):
    mod = builder()
    inputs = tmp_path/"inputs"
    atlas = inputs/"atlas"
    atlas.mkdir(parents=True)
    registry = inputs/"registry.csv"
    registry.write_text("municipality,istat_code\n"+"".join(f"{r['name']},{r['code']}\n" for r in towns()))
    data = atlas/"atlas_data.json"
    data.write_text(json.dumps({"status":"technical_draft_do_not_publish","publication_allowed":False,
                                "synthetic_input":True,"municipalities":towns()}))
    manifest = atlas/"atlas_manifest.json"
    manifest.write_text(json.dumps({"status":"technical_draft_do_not_publish","publication_allowed":False,
                                   "registry_sha256":sha256_file(registry),
                                   "output_sha256":{"atlas_data.json":sha256_file(data)}}))
    out = mod.build(atlas,registry,tmp_path/"result",["economic","accessibility"],global_scenario=True)
    result = json.loads((out/"summary.json").read_text())
    assert result["synthetic_input"] is True
    assert len(result["municipalities"]) == 27
    assert "global_baseline_rank" in (out/"preview.csv").read_text()
    with pytest.raises(FileExistsError):
        mod.build(atlas,registry,out,["economic"])
    data.write_text(data.read_text()+"\n")
    with pytest.raises(ValueError,match="hash mismatch"):
        mod.build(atlas,registry,tmp_path/"blocked",["economic"])
    assert not (tmp_path/"blocked").exists()
