"""Metadata consistency is explicitly separate from scientific approval."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from epah_diagnosis.methodology_v0_5 import check_catalog

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def catalogue():
    return json.loads((ROOT / "docs/v0_5_indicator_contracts.json").read_text(encoding="utf-8"))


def test_official_sources_are_registered_but_no_municipal_observations_are_added(catalogue):
    result = check_catalog(catalogue)
    assert result["proposals"] == 18
    assert result["scientific_approval"] is result["publication_allowed"] is False
    assert result["municipal_series_added"] == 0
    kinds = [item["change_type"] for item in catalogue["indicators"]]
    assert kinds.count("new_epah_2026") == 9 and kinds.count("updated_epah_2026") == 5


@pytest.mark.parametrize("field", ["unit", "universe", "numerator", "denominator", "reference_period", "source_locator"])
def test_missing_or_blank_core_methodology_is_rejected(catalogue, field):
    catalogue["indicators"][0][field] = ""
    with pytest.raises(ValueError):
        check_catalog(catalogue)


@pytest.mark.parametrize("field,value", [("geography", "municipality"), ("local_use", "municipal_estimate"),
    ("review_status", "approved"), ("source_ref", "unregistered"), ("unit", "unknown")])
def test_national_benchmark_cannot_be_promoted_or_lose_its_provenance(catalogue, field, value):
    catalogue["indicators"][0][field] = value
    with pytest.raises(ValueError):
        check_catalog(catalogue)


def test_duplicate_ids_and_false_approval_claims_fail(catalogue):
    duplicate = deepcopy(catalogue)
    duplicate["indicators"][1]["id"] = duplicate["indicators"][0]["id"]
    with pytest.raises(ValueError):
        check_catalog(duplicate)
    catalogue["scientific_approval"] = True
    with pytest.raises(ValueError):
        check_catalog(catalogue)
