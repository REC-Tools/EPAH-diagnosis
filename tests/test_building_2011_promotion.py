"""PR-09c real source-promotion guard: staged source evidence, no fake approval."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/indicators/building_stock_2011.csv"
SUMMARY = ROOT / "data/indicators/building_stock_benchmarks_2011.csv"
EVIDENCE = ROOT / "data/quality/building_stock_2011_source_evidence.json"
MATRIX = ROOT / "data/verification_matrix.csv"
BASELINE = ROOT / "data/reference/verification_matrix_baseline_81.csv"
OLD_HASH = "c62af5f6cddf59623e59a4cc44b8df7e39e3f729cc19b2d720c2596886af9bcd"


def rows(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_published_2011_outputs_match_original_user_audit_checksums():
    e = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert e["original_zip_sha256"] == OLD_HASH
    assert hashlib.sha256(DATA.read_bytes()).hexdigest() == e["derived_csv_sha256"]
    assert hashlib.sha256(SUMMARY.read_bytes()).hexdigest() == e["benchmark_csv_sha256"]
    assert e["derived_csv_sha256"] == "3e57f8ee85458d82ff8d3c9b031bb063bf9e73b86fa3d621875ba8e1765ac9d1"
    assert e["benchmark_csv_sha256"] == "5aca08da60931876c70800c8079b1ec5180f51f0225959697378b0614ac20021"
    assert e["reviewed_by"] is None and e["approved_for_merge"] is False


def test_every_building_value_exactly_matches_its_denominator_and_age_bins():
    data = rows(DATA)
    assert len(data) == 27
    assert len({r["municipality_code"] for r in data}) == 27
    assert {r["year"] for r in data} == {"2011"}
    bins = (
        "buildings_pre_1919", "buildings_1919_1945", "buildings_1946_1960",
        "buildings_1961_1970", "buildings_1971_1980", "buildings_1981_1990",
        "buildings_1991_2000", "buildings_2001_2005", "buildings_after_2005",
    )
    total_e3 = old_e3 = 0
    for r in data:
        total = int(r["residential_buildings_total"])
        old = int(r["buildings_pre_1981"])
        ages = [int(r[k]) for k in bins]
        assert all(age >= 0 for age in ages)
        assert sum(ages[:5]) == old
        assert sum(ages) == total
        assert f"{old / total * 100:.2f}" == r["share_pre_1981_pct"]
        total_e3 += total
        old_e3 += old
    assert (total_e3, old_e3) == (18272, 16218)


def test_benchmarks_match_source_counts_and_weighted_aggregation():
    data = rows(SUMMARY)
    by_name = {r["territory"]: r for r in data}
    assert len(data) == 3
    expected = {
        "Green Community Sinergie in Canavese": (27, 18272, 16218, "88.76"),
        "Piemonte": (1206, 944690, 780465, "82.62"),
        "Italia": (8092, 12187698, 9028831, "74.08"),
    }
    for territory, (n, total, older, share) in expected.items():
        row = by_name[territory]
        assert int(row["municipality_count"]) == n
        assert int(row["residential_buildings_total"]) == total
        assert int(row["buildings_pre_1981"]) == older
        assert row["share_pre_1981_pct"] == f"{older / total * 100:.2f}" == share


def test_staged_matrix_changes_only_27_building_rows_and_legacy_baseline_untouched():
    matrix = rows(MATRIX)
    assert len(matrix) == 243
    baseline = rows(BASELINE)
    assert [(r["municipality"], r["indicator_id"]) for r in matrix[:81]] == [
        (r["municipality"], r["indicator_id"]) for r in baseline
    ]
    preserved = [(old, new) for old, new in zip(baseline, matrix[:81])
                 if old["indicator_id"] != "old_building_stock"]
    assert len(preserved) == 54
    assert all(old == new for old, new in preserved)
    assert Counter(r["status"] for r in matrix) == {"Dato validato": 162, "Da verificare": 81}
    records = {(r["municipality"], r["indicator_id"]): r for r in matrix}
    data = rows(DATA)
    for item in data:
        r = records[(item["municipality"], "old_building_stock")]
        assert r["status"] == "Dato validato"
        assert r["year"] == "2011" and r["unit"] == "%"
        assert r["value"] == item["share_pre_1981_pct"]
        assert r["source_url"].startswith("https://")
        assert "review pending" in r["notes"]
    for iid in ("dea_accessibility", "upper_secondary_accessibility", "rail_accessibility"):
        subset = [r for r in matrix if r["indicator_id"] == iid]
        assert len(subset) == 27
        assert all(r["status"] == "Da verificare" and not r["value"] for r in subset)


def test_release_not_unblocked_without_nine_human_methodology_reviews():
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from check_v0_1_readiness import evaluate
    readiness = evaluate(phase="inputs")
    assert readiness["inputs_ready"] is False
    assert readiness["data_ready"] is False
    assert readiness["methodology_approved"] is False
    assert "old_building_stock" not in readiness["blockers"]["unvalidated_core"]
    assert len(readiness["blockers"]["unvalidated_core"]) == 3
