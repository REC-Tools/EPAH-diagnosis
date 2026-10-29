"""Offline protection tests: simulate accidental PR #80-style data losses."""
from __future__ import annotations

import csv
import io
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_pr_data_guard import (
    Change, changed_protected, diff_changes, matrix_problems,
    scope_problems, valid_approval,
)


def matrix(rows):
    out = io.StringIO()
    fields = ["municipality", "indicator_id", "status", "value", "year",
              "unit", "source_url"]
    writer = csv.DictWriter(out, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def row(status="Dato validato", value="3270", indicator="heating_degree_days"):
    return dict(municipality="Pratiglione", indicator_id=indicator,
                status=status, value=value, year="2016", unit="GG",
                source_url="https://example.org/reference")


def declaration(extra=""):
    return ("Data-change: yes\n"
            "Data-evidence: docs/review/source-audit.md\n"
            "Data-review: required\n" + extra)


def test_documentation_only_pr_passes_without_data_declaration():
    assert scope_problems(
        [Change("M", "README.md"), Change("M", "src/epah_diagnosis/cartography.py")],
        "Type: docs\nNo source changes.",
    ) == []


def test_unannounced_matrix_change_is_blocked():
    problems = scope_problems(
        [Change("M", "data/verification_matrix.csv")],
        "Cartographic refactor. NON modifica dati di osservazione.",
        before=matrix([row()]), after=matrix([row(status="Dato acquisito")]),
    )
    assert any("Data-change: yes" in x for x in problems)
    assert any("asserts" in x for x in problems)
    assert any("Data-downgrade" in x for x in problems)


def test_dedicated_data_pr_requires_source_and_review_declaration():
    problems = scope_problems(
        [Change("M", "data/verification_matrix.csv")],
        "Data-change: yes\n",
        before=matrix([row(status="Dato acquisito")]),
        after=matrix([row()]),
    )
    assert any("Data-evidence" in x for x in problems)
    assert any("Data-review" in x for x in problems)


def test_explicit_promotion_can_pass_scope_qa_without_pretending_approval():
    assert scope_problems(
        [Change("M", "data/verification_matrix.csv"),
         Change("A", "data/indicators/heating_degree_days.csv")],
        declaration(),
        before=matrix([row(status="Dato acquisito")]),
        after=matrix([row()]),
    ) == []


def test_downgrade_requires_exact_indicator_declaration():
    changes = [Change("M", "data/verification_matrix.csv")]
    before, after = matrix([row()]), matrix([row(status="Dato acquisito")])
    assert any("Data-downgrade" in x for x in scope_problems(
        changes, declaration(), before=before, after=after
    ))
    assert scope_problems(
        changes, declaration("Data-downgrade: heating_degree_days\n"),
        before=before, after=after,
    ) == []


def test_revised_validated_values_require_explicit_indicator_declaration():
    old = matrix([row()])
    new = matrix([row(value="3300")])
    assert any("Data-revise" in x for x in matrix_problems(old, new, declaration()))
    assert matrix_problems(
        old, new, declaration("Data-revise: heating_degree_days\n")
    ) == []


def test_matrix_missing_key_is_never_silently_accepted():
    result = matrix_problems(matrix([row()]), matrix([]), declaration())
    assert any("key set changed" in item for item in result)


def test_protected_delete_or_rename_requires_exact_path():
    missing = scope_problems(
        [Change("D", "data/quality/priority_81_source_evidence.json")],
        declaration(),
    )
    assert any("Data-delete" in x for x in missing)
    assert scope_problems(
        [Change("D", "data/quality/priority_81_source_evidence.json")],
        declaration("Data-delete: data/quality/priority_81_source_evidence.json\n"),
    ) == []
    moved = scope_problems(
        [Change("R", "docs/renamed.md", "data/reference/original.csv")],
        declaration(),
    )
    assert any("Data-delete" in x for x in moved)


def test_protected_registry_and_methodology_are_covered():
    examples = (
        "data/municipalities.csv", "config/indicators.json",
        "config/release_reviews_v0_1.json", "data/quality/approval.json",
        "data/reference/evidence.csv", "data/indicators/annual.csv",
        "data/geography/municipalities_2026.geojson",
        "data/derived/preliminary.csv",
    )
    assert len(changed_protected([Change("M", x) for x in examples])) == len(examples)


def test_stale_and_self_approvals_are_not_sufficient():
    head = "head-current"
    author = "alice"
    reviews = [
        dict(user={"login": "alice"}, state="APPROVED", commit_id=head),
        dict(user={"login": "bob"}, state="APPROVED", commit_id="old-sha"),
    ]
    assert not valid_approval(reviews, author, head)
    reviews.append(dict(user={"login": "bob"}, state="APPROVED", commit_id=head))
    assert valid_approval(reviews, author, head)
    reviews.append(dict(user={"login": "bob"}, state="CHANGES_REQUESTED",
                        commit_id=head))
    assert not valid_approval(reviews, author, head)


def test_true_git_name_status_parser_handles_renames(tmp_path, monkeypatch):
    import subprocess
    def synthetic_output(argv):
        assert "--name-status" in argv and "-z" in argv
        return b"M\x00README.md\x00R100\x00data/reference/a.csv\x00docs/b.csv\x00"
    monkeypatch.setattr(subprocess, "check_output", synthetic_output)
    assert diff_changes("a", "b") == [
        Change("M", "README.md"),
        Change("R", "docs/b.csv", "data/reference/a.csv"),
    ]


def test_automated_updaters_only_propose_draft_prs():
    root = Path(__file__).resolve().parents[1]
    for name in ("update-mef-income.yml", "update-population-65plus.yml"):
        text = (root / ".github/workflows" / name).read_text(encoding="utf-8")
        assert "gh pr create --draft" in text
        assert 'git push --set-upstream origin "$branch"' in text
        assert "pull-requests: write" in text
        assert "git push\n" not in text
        assert "git push origin main" not in text


def test_review_workflow_uses_base_guard_and_checks_review_events():
    root = Path(__file__).resolve().parents[1]
    text = (root / ".github/workflows/protected-data-guard.yml").read_text(
        encoding="utf-8"
    )
    assert "pull_request_review:" in text
    assert "pull-requests: read" in text
    assert '${BASE_SHA}:scripts/check_pr_data_guard.py' in text
    assert "--require-review" in text
