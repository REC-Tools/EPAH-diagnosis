"""Real source-archive promotion regression checks, not synthetic measurements.

Inputs were independently compared against original 2020/2021 XLSX and
the 2016 consolidated official Annex A PDF. A PR comment/review is required
for a durable human approval trail; data promotion does not make v0.1 READY.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "data/verification_matrix.csv"
EVIDENCE = ROOT / "data/quality/priority_81_source_evidence.json"
BASEN = ROOT / "data/reference/verification_matrix_baseline_81.csv"
EXPECTED = {
    "mean_altitude": (
        "data/indicators/mean_altitude_2021.csv",
        "bf102e4a1828773120d4cc01e5d9f9cf07c16c2728a4cbf3aaa1144f9b3bc187",
        "data/indicators/mean_altitude_summary_2021.csv",
        "f8a5b7e59bbeda2d0a70557f6efcd333aacf16844d1ecef63da479449fc476d6",
    ),
    "snai_classification": (
        "data/indicators/snai_classification_2020.csv",
        "78ee6821543381a32e6ed891a90dca11e75869b6f223c887f3be932a8fdf6cd4",
        "data/indicators/snai_classification_summary_2020.csv",
        "41a3fac979ad68e74e02513683eba994519c049d7de5cab246a85a8b6f347c9f",
    ),
}


def csv_rows(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_published_territorial_outputs_exactly_match_user_supplied_source_qa_hashes():
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert evidence["technical_qa_status"] == "passed"
    for iid, (file, sha, summary_file, sum_sha) in EXPECTED.items():
        assert digest(ROOT / file) == sha
        assert digest(ROOT / summary_file) == sum_sha
        row = next(x for x in evidence["source_files"] if x["indicator_id"] == iid)
        assert row["derived_csv_sha256"] == sha
        assert row["summary_csv_sha256"] == sum_sha


def test_27_municipalities_9_core_rows_and_validated_units():
    matrix = csv_rows(MATRIX)
    assert len(matrix) == 243
    keys = {(r["municipality"], r["indicator_id"]) for r in matrix}
    assert len(keys) == 243
    assert Counter(r["status"] for r in matrix) == {"Dato validato": 135, "Da verificare": 108}
    by_indicator = {id: [r for r in matrix if r["indicator_id"] == id]
                    for id in {r["indicator_id"] for r in matrix}}
    for indicator in ("heating_degree_days", "mean_altitude", "snai_classification"):
        assert len(by_indicator[indicator]) == 27
        assert all(r["source_url"].startswith("https://") and r["value"]
                   for r in by_indicator[indicator])
    assert {r["value"] for r in by_indicator["snai_classification"]} == {"C", "D", "E", "F"}
    assert {r["year"] for r in by_indicator["mean_altitude"]} == {"2021"}
    assert {r["year"] for r in by_indicator["snai_classification"]} == {"2020"}


def test_exact_outputs_and_matrix_correspond_by_municipality():
    matrix = {(r["municipality"], r["indicator_id"]): r for r in csv_rows(MATRIX)}
    for iid, (file, _sha, *_unused) in EXPECTED.items():
        data = csv_rows(ROOT / file)
        assert len(data) == 27
        assert len({r["municipality_code"] for r in data}) == 27
        key = "mean_altitude_m" if iid == "mean_altitude" else "snai_class"
        for item in data:
            ref = matrix[(item["municipality"], iid)]
            assert ref["value"] == item[key]
            assert item["year"] == ref["year"]
            assert ref["status"] == "Dato validato"


def test_original_81_rows_unmodified_and_release_gate_still_blocked():
    matrix = csv_rows(MATRIX)
    baseline = csv_rows(BASEN)
    assert matrix[:81] == baseline
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from check_v0_1_readiness import evaluate
    result = evaluate(phase="inputs")
    assert result["inputs_ready"] is False
    assert result["blockers"]["unvalidated_core"]
    assert result["methodology_approved"] is False


def test_review_metadata_does_not_impersonate_durable_github_signature():
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert evidence["github_review_status"].startswith("pending")
    assert evidence["git_release_methodology_approvals"] == "not_changed"
    assert evidence["release_ready"] is False
