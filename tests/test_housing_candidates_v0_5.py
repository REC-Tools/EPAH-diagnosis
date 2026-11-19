from copy import deepcopy
import json
from pathlib import Path

import pytest

from epah_diagnosis.methodology_v0_5 import check_catalog, main, prepare_protocol

ROOT = Path(__file__).resolve().parents[1]
HOUSING = ROOT / "docs/v0_5_housing_contracts.json"
ORIGINAL = ROOT / "docs/v0_5_indicator_contracts.json"


@pytest.fixture
def catalog():
    return json.loads(HOUSING.read_text(encoding="utf-8"))


@pytest.mark.parametrize("number", range(19, 24))
def test_prepare_each_housing_contract_preserves_scope_and_source(tmp_path, catalog, number):
    identifier = f"V05-{number}"
    before = HOUSING.read_bytes()
    out = prepare_protocol(HOUSING, identifier, tmp_path / identifier)
    record = json.loads((out / "protocol.json").read_text(encoding="utf-8"))
    selected = next(item for item in catalog["indicators"] if item["id"] == identifier)
    assert record["benchmark_contract"] == selected  # compatible historical key
    assert record["benchmark_source"] == catalog["sources"][selected["source_ref"]]
    assert record["collection_authorized"] is record["scientific_approval"] is False
    assert record["municipal_series_added"] == 0
    assert all(item["proposed_answer"] is None for item in record["local_decisions"].values())
    assert HOUSING.read_bytes() == before


@pytest.mark.parametrize("index,changes", [
    (0, {"geography": "municipality"}),
    (0, {"local_use": "municipal_estimate"}),
    (0, {"review_status": "approved"}),
    (0, {"data_state": "acquired"}),
    (0, {"unit": "days_per_year"}),
    (0, {"statistical_unit": "person"}),
    (0, {"id": "V05-99"}),
    (4, {"geography": "municipality_target_not_verified"}),
])
def test_reject_housing_scope_promotions_and_unit_substitutions(catalog, index, changes):
    catalog["indicators"][index].update(changes)
    with pytest.raises(ValueError):
        check_catalog(catalog)


def test_original_national_scope_cannot_use_local_housing_escape():
    original = json.loads(ORIGINAL.read_text(encoding="utf-8"))
    original["indicators"][0].update(change_type="local_housing_candidate",
        geography="municipality_target_not_verified", local_use="municipal_feasibility_not_verified")
    with pytest.raises(ValueError):
        check_catalog(original)


def test_catalogs_can_be_combined_without_duplicating_ids_or_promoting_series(catalog):
    original = json.loads(ORIGINAL.read_text(encoding="utf-8"))
    assert check_catalog(original)["proposals"] == 18
    combined = deepcopy(original)
    combined["sources"].update(catalog["sources"])
    combined["indicators"].extend(catalog["indicators"])
    result = check_catalog(combined)
    assert result["proposals"] == 23 and result["municipal_series_added"] == 0
    combined["indicators"][-1]["id"] = combined["indicators"][0]["id"]
    with pytest.raises(ValueError):
        check_catalog(combined)


def test_existing_cli_checks_housing_and_keeps_national_catalog(capsys):
    assert main(["check", "--catalog", str(HOUSING)]) == 0
    record = json.loads(capsys.readouterr().out)
    assert record["ids"] == [f"V05-{n}" for n in range(19, 24)]
    assert record["scientific_approval"] is record["publication_allowed"] is False
    assert main(["check", "--catalog", str(ORIGINAL)]) == 0
    assert json.loads(capsys.readouterr().out)["proposals"] == 18
