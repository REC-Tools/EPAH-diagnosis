"""Behavioral tests for the strict, offline v0.1 release gate."""
import csv
import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_v0_1_readiness.py"
SPEC = importlib.util.spec_from_file_location("check_v0_1_readiness", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
evaluate = MODULE.evaluate

FIELDS = [
    "municipality", "indicator_id", "status", "value", "year", "unit",
    "source_url", "quality", "limitations",
]


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


@pytest.fixture
def scenario(tmp_path):
    names = [f"Comune {i:02d}" for i in range(27)]
    municipality_file = tmp_path / "municipalities.csv"
    municipality_file.write_text(
        "municipality\n" + "\n".join(names) + "\n", encoding="utf-8"
    )
    release_file = tmp_path / "release.json"
    catalog_file = tmp_path / "catalog.json"
    reviews_file = tmp_path / "reviews.json"
    matrix_file = tmp_path / "matrix.csv"
    output_dir = tmp_path / "bundle"

    release = {
        "release": "0.1.0",
        "core_indicators": ["a", "b"],
        "release_criteria": {"municipalities": 27},
        "extensions": [],
        "required_artifacts": ["profile.csv", "maps/map.png"],
    }
    catalog = {
        "indicators": [
            {"id": "a", "unit": "%", "methodological_maturity": "OPERATIONAL"},
            {"id": "b", "unit": "minutes", "methodological_maturity": "VALIDATED"},
        ]
    }
    reviews = {
        "methodology_approvals": [
            {
                "indicator_id": item,
                "decision": "approved",
                "reviewed_by": "Test reviewer",
                "reviewed_on": "2026-10-28",
                "evidence_url": "https://example.org/reviews/123",
            }
            for item in ("a", "b")
        ]
    }
    rows = [
        {
            "municipality": name,
            "indicator_id": item,
            "status": "Dato validato",
            "value": "50" if item == "a" else "25",
            "year": "2024",
            "unit": "%" if item == "a" else "minuti",
            "source_url": "https://example.org/official-data",
            "quality": "Synthetic test fixture",
            "limitations": "Synthetic test data, not for publication",
        }
        for name in names
        for item in ("a", "b")
    ]

    write_json(release_file, release)
    write_json(catalog_file, catalog)
    write_json(reviews_file, reviews)
    write_csv(matrix_file, rows)

    kwargs = {
        "matrix_file": matrix_file,
        "municipalities_file": municipality_file,
        "release_config": release_file,
        "catalog_file": catalog_file,
        "reviews_file": reviews_file,
        "output_dir": output_dir,
    }
    return {
        "kwargs": kwargs, "rows": rows, "release": release,
        "catalog": catalog, "reviews": reviews,
        "write_rows": lambda: write_csv(matrix_file, rows),
        "save_release": lambda: write_json(release_file, release),
        "save_catalog": lambda: write_json(catalog_file, catalog),
        "save_reviews": lambda: write_json(reviews_file, reviews),
    }


def test_complete_inputs_are_ready_but_not_release_ready(scenario):
    result = evaluate(**scenario["kwargs"])
    assert result["data_ready"] is True
    assert result["methodology_approved"] is True
    assert result["inputs_ready"] is True
    assert result["ready"] is True
    assert result["release_ready"] is False
    assert result["artifacts_ready"] is None


def test_release_phase_requires_nonempty_artifacts(scenario):
    kwargs = scenario["kwargs"]
    result = evaluate(**kwargs, phase="release")
    assert result["data_ready"] and result["methodology_approved"]
    assert result["artifacts_ready"] is False
    assert result["release_ready"] is False

    output_dir = kwargs["output_dir"]
    (output_dir / "maps").mkdir(parents=True)
    (output_dir / "profile.csv").write_text("municipality\nX\n", encoding="utf-8")
    (output_dir / "maps/map.png").write_bytes(b"synthetic-fixture")
    result = evaluate(**kwargs, phase="release")
    assert result["artifacts_ready"] is True
    assert result["release_ready"] is True


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("value", "", "empty_core_values"),
        ("value", "101", "invalid_validated_rows"),
        ("value", "NaN", "invalid_validated_rows"),
        ("value", "inf", "invalid_validated_rows"),
        ("value", "abc", "invalid_validated_rows"),
        ("year", "", "invalid_validated_rows"),
        ("unit", "kg", "invalid_validated_rows"),
        ("quality", "", "invalid_validated_rows"),
        ("limitations", "", "invalid_validated_rows"),
        ("source_url", "not-a-url", "invalid_validated_rows"),
        ("status", "Dato acquisito", "unvalidated_core"),
    ],
)
def test_bad_or_incomplete_data_are_not_ready(scenario, field, value, reason):
    scenario["rows"][0][field] = value
    scenario["write_rows"]()
    result = evaluate(**scenario["kwargs"])
    assert result["data_ready"] is False
    assert result["ready"] is False
    assert result["blockers"][reason]


def test_missing_and_duplicate_rows_fail(scenario):
    rows = scenario["rows"]
    rows.pop()
    scenario["write_rows"]()
    result = evaluate(**scenario["kwargs"])
    assert result["blockers"]["missing_core"]["b"]

    rows.append(dict(rows[0]))
    scenario["write_rows"]()
    result = evaluate(**scenario["kwargs"])
    assert result["blockers"]["duplicates"]


def test_unknown_municipality_and_unknown_indicator_fail(scenario):
    rows = scenario["rows"]
    rows.append({**rows[0], "municipality": "Unexpected"})
    rows.append({**rows[0], "indicator_id": "unknown"})
    scenario["write_rows"]()
    result = evaluate(**scenario["kwargs"])
    assert "Unexpected" in result["blockers"]["unexpected_municipalities"]
    assert "unknown" in result["blockers"]["unexpected_indicators"]


def test_catalog_must_match_release(scenario):
    scenario["release"]["core_indicators"] = ["a"]
    scenario["save_release"]()
    result = evaluate(**scenario["kwargs"])
    assert result["blockers"]["configuration"]


def test_review_is_required_even_if_all_values_are_valid(scenario):
    scenario["reviews"]["methodology_approvals"] = []
    scenario["save_reviews"]()
    result = evaluate(**scenario["kwargs"])
    assert result["data_ready"] is True
    assert result["methodology_approved"] is False
    assert result["ready"] is False
    assert result["review_blockers"]["a"]


def test_experimental_indicator_cannot_be_approved_implicitly(scenario):
    scenario["catalog"]["indicators"][0]["methodological_maturity"] = "EXPERIMENTAL"
    scenario["save_catalog"]()
    result = evaluate(**scenario["kwargs"])
    assert result["methodology_approved"] is False
    assert "maturity" in result["review_blockers"]["a"][0]


@pytest.mark.parametrize("field,value", [
    ("decision", "pending"),
    ("reviewed_by", ""),
    ("reviewed_on", "tomorrow"),
    ("evidence_url", "not-a-url"),
])
def test_invalid_human_review_does_not_pass(scenario, field, value):
    scenario["reviews"]["methodology_approvals"][0][field] = value
    scenario["save_reviews"]()
    assert evaluate(**scenario["kwargs"])["methodology_approved"] is False


def test_supertarget_snai_class_validation(scenario):
    scenario["release"]["core_indicators"] = ["a", "snai_classification"]
    scenario["catalog"]["indicators"][1] = {
        "id": "snai_classification", "unit": "class",
        "methodological_maturity": "OPERATIONAL",
    }
    scenario["reviews"]["methodology_approvals"][1]["indicator_id"] = "snai_classification"
    for row in scenario["rows"]:
        if row["indicator_id"] == "b":
            row["indicator_id"] = "snai_classification"
            row["unit"] = "classe A-F"
            row["value"] = "G"
    scenario["save_release"]()
    scenario["save_catalog"]()
    scenario["save_reviews"]()
    scenario["write_rows"]()
    result = evaluate(**scenario["kwargs"])
    assert result["data_ready"] is False
    assert "snai_classification" in result["blockers"]["invalid_validated_rows"]


def test_artifact_path_cannot_escape_bundle(scenario, tmp_path):
    scenario["release"]["required_artifacts"] = ["../secret.txt"]
    scenario["save_release"]()
    result = evaluate(**scenario["kwargs"], phase="release")
    assert result["artifacts_ready"] is False
    assert "escapes" in result["artifact_blockers"][0]


def test_missing_review_manifest_fails_closed(scenario):
    scenario["kwargs"]["reviews_file"].unlink()
    result = evaluate(**scenario["kwargs"])
    assert result["methodology_approved"] is False
    assert "manifest" in result["review_blockers"]
