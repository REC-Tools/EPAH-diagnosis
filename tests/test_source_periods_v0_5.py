from copy import deepcopy
import json
from pathlib import Path

import pytest

from epah_diagnosis.source_periods_v0_5 import check_source_register
from epah_diagnosis.methodology_v0_5 import main

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "docs/v0_5_source_register.json"


@pytest.fixture
def register():
    return json.loads(REGISTER.read_text(encoding="utf-8"))


def test_full_guide_is_accounted_for_without_inheriting_its_year(register):
    result = check_source_register(register)
    assert result["sources"] == 57
    assert result["weights_applied"] is result["scientific_approval"] is False
    assert result["municipal_series_added"] == 0
    assert result["distinct_urls"] < 57  # repeated cards retain their own locator
    assert [sum(row["category"] == name for row in register["sources"])
            for name in ["policy", "knowledge_data", "practice", "network"]] == [13, 18, 16, 10]
    assert result["periods"][0]["target_minus_reference_end_years"] is None
    istat = next(row for row in register["sources"] if row["title"] == "ISTAT – Abitazioni occupate")
    assert istat["publication_year"] == 2026 and istat["reference_year_end"] == 2023
    assert next(row for row in result["periods"] if row["id"] == istat["id"])["target_minus_reference_end_years"] == 2


@pytest.mark.parametrize("end,expected", [(2025, 0), (2023, 2), (2026, -1), (None, None)])
def test_offset_uses_reference_period_not_publication_or_acquisition(register, end, expected):
    row = register["sources"][0]
    row.update(publication_year=2026, dataset_acquired_on="2026-11-19",
               reference_year_start=end, reference_year_end=end)
    before = deepcopy(register)
    assert check_source_register(register)["periods"][0]["target_minus_reference_end_years"] == expected
    assert register == before


@pytest.mark.parametrize("changes", [
    {"publication_year": True}, {"reference_year_start": 2025, "reference_year_end": 2024},
    {"reference_year_start": 2025}, {"dataset_acquired_on": "2025-02-30"},
    {"verification_status": "approved"}, {"verification_status": "metadata_checked"},
    {"temporal_weight": 0.5}, {"publication_year": "2026"},
])
def test_rejects_ambiguous_periods_dates_and_implicit_approval(register, changes):
    register["sources"][0].update(changes)
    with pytest.raises(ValueError):
        check_source_register(register)


def test_rejects_missing_cards_duplicate_ids_and_publication_claim(register):
    for mutate in [lambda d: d["sources"].pop(),
                   lambda d: d["sources"][1].update(id=d["sources"][0]["id"]),
                   lambda d: d.update(publication_allowed=True)]:
        candidate = deepcopy(register)
        mutate(candidate)
        with pytest.raises(ValueError):
            check_source_register(candidate)


def test_cli_source_register_preserves_existing_catalogue_command(capsys):
    assert main(["sources-check", "--register", str(REGISTER)]) == 0
    assert json.loads(capsys.readouterr().out)["weights_applied"] is False
    assert main(["check", "--catalog", str(ROOT / "docs/v0_5_indicator_contracts.json")]) == 0
    assert json.loads(capsys.readouterr().out)["proposals"] == 18
    with pytest.raises(SystemExit) as error:
        main(["sources-check", "--catalog", str(REGISTER)])
    assert error.value.code == 2
