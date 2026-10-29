"""Regression guard: archived PR #79 numeric evidence, not review approval."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "data/reference/priority_source_archive_20261029"
REVIEW = ROOT / "data/quality/priority_source_review_status.json"

# Immutable byte-level results from PR #79. These do not attest raw source files.
EXPECTED = {
    "mean_altitude": (
        "mean_altitude_2021.csv",
        "bf102e4a1828773120d4cc01e5d9f9cf07c16c2728a4cbf3aaa1144f9b3bc187",
        "mean_altitude_summary_2021.csv",
        "f8a5b7e59bbeda2d0a70557f6efcd333aacf16844d1ecef63da479449fc476d6",
        "2021",
        "mean_altitude_m",
    ),
    "snai_classification": (
        "snai_classification_2020.csv",
        "78ee6821543381a32e6ed891a90dca11e75869b6f223c887f3be932a8fdf6cd4",
        "snai_classification_summary_2020.csv",
        "41a3fac979ad68e74e02513683eba994519c049d7de5cab246a85a8b6f347c9f",
        "2020",
        "snai_class",
    ),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_exact_original_csv_bytes_retained() -> None:
    evidence = json.loads((ARCHIVE / "priority_81_source_evidence_original.json").read_text(encoding="utf-8"))
    assert evidence["technical_qa_status"] == "passed"
    for iid, (filename, sha, summary_filename, summary_sha, *_extra) in EXPECTED.items():
        assert hashlib.sha256((ARCHIVE / filename).read_bytes()).hexdigest() == sha
        assert hashlib.sha256((ARCHIVE / summary_filename).read_bytes()).hexdigest() == summary_sha
        original = next(entry for entry in evidence["source_files"] if entry["indicator_id"] == iid)
        assert original["derived_csv_sha256"] == sha
        assert original["summary_csv_sha256"] == summary_sha


def test_archive_code_join_is_complete_and_non_synthetic() -> None:
    municipalities = read_csv(ROOT / "data/municipalities.csv")
    expected = {(row["municipality"], row["istat_code"]) for row in municipalities}
    assert len(expected) == 27
    for iid, (filename, _sha, _summary, _summary_sha, year, value_field) in EXPECTED.items():
        rows = read_csv(ARCHIVE / filename)
        assert len(rows) == 27
        assert {(row["municipality"], row["municipality_code"]) for row in rows} == expected
        assert {row["year"] for row in rows} == {year}
        assert all(row[value_field].strip() for row in rows)
        if iid == "snai_classification":
            assert {row[value_field] for row in rows} == {"C", "D", "E", "F"}
        else:
            assert all(float(row[value_field]) >= -500 for row in rows)


def test_archive_is_explicitly_pending_and_does_not_approve_release() -> None:
    status = json.loads(REVIEW.read_text(encoding="utf-8"))
    assert status["status"] == "pending_human_review"
    assert status["data_publication_approved"] is False
    assert status["methodology_approved"] is False
    assert status["current_matrix_promoted_by_archive"] is False
    assert status["review_evidence_url"] is None
    assert status["original_binary_sources_in_repository"] is False
    evidence = json.loads((ARCHIVE / "priority_81_source_evidence_original.json").read_text(encoding="utf-8"))
    assert evidence["github_review_status"].startswith("pending")


def test_pending_evidence_must_not_be_presented_as_current_validation() -> None:
    if json.loads(REVIEW.read_text(encoding="utf-8"))["status"] != "pending_human_review":
        return  # On later approved releases a separate documented review process applies.
    matrix = read_csv(ROOT / "data/verification_matrix.csv")
    for row in matrix:
        if row["indicator_id"] in {"mean_altitude", "snai_classification"}:
            assert row["status"] != "Dato validato"
