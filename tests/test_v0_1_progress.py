"""Synthetic tests for the read-only progress report."""
import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "summarize_v0_1_progress.py"
SPEC = importlib.util.spec_from_file_location("summarize_v0_1_progress", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def fixture_report():
    return {
        "municipalities": 3,
        "blockers": {
            "missing_core": {"access": ["A"]},
            "unvalidated_core": {"access": ["B"]},
            "empty_core_values": {"access": ["A", "B"]},
            "invalid_validated_rows": {"population": {"C": ["invalid URL"]}},
        },
        "review_blockers": {"population": ["no review"], "access": ["no review"]},
        "methodology_approved": False,
        "inputs_ready": False,
        "release_ready": False,
    }


def test_overlapping_blockers_are_counted_once():
    summary = MODULE.indicator_progress(fixture_report(), ["population", "access"])
    assert [item["passed"] for item in summary] == [2, 1]
    assert summary[1]["blocked"] == 2


def test_reports_data_and_methodology_separately():
    report = MODULE.render_markdown(
        fixture_report(), {"core_indicators": ["population", "access"]}
    )
    assert "3/6 core observations (50.0%)" in report
    assert "| access | 1/3 | pending |" in report
    assert "Input gate:** BLOCKED" in report
    assert "Release gate:** BLOCKED" in report


def test_complete_example_passes():
    r = fixture_report()
    r.update(blockers={}, review_blockers={}, methodology_approved=True,
             inputs_ready=True, release_ready=True)
    report = MODULE.render_markdown(r, {"core_indicators": ["population"]})
    assert "3/3 core observations (100.0%)" in report
    assert "| population | 3/3 | PASS |" in report
    assert "Release gate:** PASS" in report


def test_additional_integrity_blockers_are_visible():
    r = fixture_report()
    r["blockers"]["duplicates"] = [["A", "population"]]
    output = MODULE.render_markdown(r, {"core_indicators": ["population", "access"]})
    assert "**Additional integrity blockers:** duplicates." in output
