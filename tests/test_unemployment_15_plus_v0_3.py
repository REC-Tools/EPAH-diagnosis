"""H46 census unemployment-rate candidate: strictly synthetic, offline fixtures."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "prepare_unemployment_15_plus_v0_3.py"
SPEC = importlib.util.spec_from_file_location("h46_candidate", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
h46 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(h46)


def registry_file(path: Path, size: int = 27) -> dict[str, str]:
    values = {f"001{number:03d}": f"Town {number}" for number in range(1, size + 1)}
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("municipality", "istat_code"))
        writer.writerows((name, code) for code, name in values.items())
    return values


def fixture_rows(registry: dict[str, str]) -> list[dict[str, str]]:
    rows = []
    counts = {"employed": 50, "unemployed": 5, "inactive": 35,
              "unknown": 0, "labour_force": 55, "population_total": 90}
    for code, name in registry.items():
        for category, count in counts.items():
            rows.append({"municipality_code": code, "municipality": name,
                         "reference_year": "2024", "age_universe": "15_plus",
                         "sex": "total", "labour_status": category, "persons": str(count)})
    return rows


def csv_file(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=h46.REQUIRED, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def setup(tmp_path: Path, count: int = 27):
    registry_path = tmp_path / "municipalities.csv"
    registry = registry_file(registry_path, size=count)
    source = tmp_path / "labor_normalized.csv"
    original = tmp_path / "census_2024_original.csv"
    original.write_bytes(b"TEST ONLY / NO REAL ISTAT OBSERVATIONS\n")
    rows = fixture_rows(registry)
    csv_file(source, rows)
    return registry_path, source, original, registry, rows


def run_cli(registry_path: Path, source: Path, original: Path, out: Path, *options: str):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--normalized-csv", str(source),
         "--original-export", str(original), "--registry", str(registry_path),
         "--out-dir", str(out), *options],
        capture_output=True, text=True, check=False,
    )


def test_formula_and_correct_denominator(tmp_path: Path) -> None:
    _, path, _, reg, _ = setup(tmp_path)
    observations, qa = h46.aggregate(path, reg)
    assert len(observations) == 27
    assert observations[0]["labour_force_15_plus"] == "55"
    assert observations[0]["population_15_plus"] == "90"
    assert observations[0]["unemployment_rate_15_plus_pct"] == "9.09"
    assert qa["weighted_unemployment_rate_15_plus_pct"] == "9.09"
    assert qa["sum_unemployed"] == "135"
    assert qa["sum_labour_force"] == "1485"
    assert qa["sum_population_15_plus"] == "2430"
    assert qa["normalized_rows"] == 162


def test_zero_unemployment_is_valid_with_positive_labour_force(tmp_path: Path) -> None:
    _, path, _, reg, rows = setup(tmp_path)
    code = next(iter(reg))
    for row in rows:
        if row["municipality_code"] == code:
            if row["labour_status"] == "unemployed":
                row["persons"] = "0"
            if row["labour_status"] == "labour_force":
                row["persons"] = "50"
            if row["labour_status"] == "population_total":
                row["persons"] = "85"
    csv_file(path, rows)
    obs, qa = h46.aggregate(path, reg)
    assert obs[0]["unemployment_rate_15_plus_pct"] == "0.00"
    assert qa["municipalities_with_zero_unemployed"] == 1


@pytest.mark.parametrize(("category", "replacement", "message"), [
    ("unemployed", "6", "labour_force does not equal"),
    ("labour_force", "56", "labour_force does not equal"),
    ("inactive", "36", "population_total not reconciled"),
    ("population_total", "91", "population_total not reconciled"),
    ("employed", "51", "labour_force does not equal"),
])
def test_reject_inconsistent_census_accounts(tmp_path: Path, category, replacement, message) -> None:
    _, path, _, reg, rows = setup(tmp_path)
    target = next(iter(reg))
    next(row for row in rows if row["municipality_code"] == target and
         row["labour_status"] == category)["persons"] = replacement
    csv_file(path, rows)
    with pytest.raises(ValueError, match=message):
        h46.aggregate(path, reg)


def test_zero_labour_force_rejected_even_with_population(tmp_path: Path) -> None:
    _, path, _, reg, rows = setup(tmp_path)
    code = next(iter(reg))
    for row in rows:
        if row["municipality_code"] == code:
            row["persons"] = {"employed": "0", "unemployed": "0", "labour_force": "0",
                              "inactive": "90", "unknown": "0", "population_total": "90"}[row["labour_status"]]
    csv_file(path, rows)
    with pytest.raises(ValueError, match="zero labour-force"):
        h46.aggregate(path, reg)


def test_missing_municipality_blocks(tmp_path: Path) -> None:
    _, path, _, reg, rows = setup(tmp_path)
    code = next(iter(reg))
    csv_file(path, [r for r in rows if r["municipality_code"] != code])
    with pytest.raises(ValueError, match="Missing municipality"):
        h46.aggregate(path, reg)


def test_missing_category_blocks_even_if_numerators_exist(tmp_path: Path) -> None:
    _, path, _, reg, rows = setup(tmp_path)
    target = next(iter(reg))
    csv_file(path, [r for r in rows if not (r["municipality_code"] == target and
                                            r["labour_status"] == "unknown")])
    with pytest.raises(ValueError, match="missing labour-status categories"):
        h46.aggregate(path, reg)


def test_duplicate_status_blocks(tmp_path: Path) -> None:
    _, path, _, reg, rows = setup(tmp_path)
    rows.append(rows[0].copy())
    csv_file(path, rows)
    with pytest.raises(ValueError, match="duplicate municipality/status"):
        h46.aggregate(path, reg)


@pytest.mark.parametrize(("field", "bad", "message"), [
    ("reference_year", "2023", "must be 2024"),
    ("age_universe", "15_64", "age universe"),
    ("sex", "male", "sex must be"),
    ("labour_status", "seeking_work_broad", "unrecognized employment"),
    ("municipality_code", "001999", "unsupported ISTAT"),
    ("municipality_code", "1001", "unsupported ISTAT"),
    ("municipality", "Not town", "municipality name"),
    ("persons", "n.d.", "non-negative decimal"),
    ("persons", "-1", "non-negative decimal"),
    ("persons", "1,200", "non-negative decimal"),
    ("persons", "0,5", "non-negative decimal"),
    ("persons", "1e3", "non-negative decimal"),
    ("persons", "NaN", "non-negative decimal"),
    ("persons", "Infinity", "non-negative decimal"),
    ("persons", ".5", "non-negative decimal"),
    ("persons", "1.", "non-negative decimal"),
])
def test_fail_closed_on_unsupported_fields(tmp_path: Path, field, bad, message) -> None:
    _, path, _, reg, rows = setup(tmp_path)
    rows[0][field] = bad
    csv_file(path, rows)
    with pytest.raises(ValueError, match=message):
        h46.aggregate(path, reg)


def test_missing_or_duplicate_header_rejected(tmp_path: Path) -> None:
    _, path, _, reg, rows = setup(tmp_path)
    raw = path.read_text(encoding="utf-8")
    path.write_text(raw.replace("age_universe,", "no_age_universe,", 1), encoding="utf-8")
    with pytest.raises(ValueError, match="unique normalized CSV fields"):
        h46.aggregate(path, reg)
    csv_file(path, rows)
    raw = path.read_text(encoding="utf-8")
    path.write_text(raw.replace("reference_year,", "sex,", 1), encoding="utf-8")
    with pytest.raises(ValueError, match="unique normalized CSV fields"):
        h46.aggregate(path, reg)


def test_empty_export_rejected(tmp_path: Path) -> None:
    _, path, _, reg, _ = setup(tmp_path)
    csv_file(path, [])
    with pytest.raises(ValueError, match="Empty normalized"):
        h46.aggregate(path, reg)


def test_unclassified_count_is_not_mistaken_for_unemployed(tmp_path: Path) -> None:
    _, path, _, reg, rows = setup(tmp_path)
    code = next(iter(reg))
    for row in rows:
        if row["municipality_code"] == code:
            if row["labour_status"] == "unknown":
                row["persons"] = "10"
            if row["labour_status"] == "population_total":
                row["persons"] = "100"
    csv_file(path, rows)
    obs, qa = h46.aggregate(path, reg)
    assert obs[0]["unemployment_rate_15_plus_pct"] == "9.09"
    assert qa["sum_unknown"] == "10"
    assert float(qa["unknown_share_of_population_15_plus_pct"]) > 0


def test_registry_requires_27_unique_names_and_six_digit_codes(tmp_path: Path) -> None:
    path, _, _, _, _ = setup(tmp_path)
    assert len(h46.read_registry(path)) == 27
    small = tmp_path / "small.csv"
    registry_file(small, 3)
    with pytest.raises(ValueError, match="Expected 27"):
        h46.read_registry(small)
    bad = path.read_text(encoding="utf-8").replace("Town 2", "Town 1")
    path.write_text(bad, encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid/duplicate"):
        h46.read_registry(path)


def test_manifest_and_27_rows_written(tmp_path: Path) -> None:
    registry, source, original, _, _ = setup(tmp_path)
    output = tmp_path / "review"
    good = run_cli(registry, source, original, output)
    assert good.returncode == 0, good.stderr
    with (output / "unemployment_15_plus_preview.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 27
    assert all(r["status"] == h46.STATUS for r in rows)
    qa = json.loads((output / "qa.json").read_text(encoding="utf-8"))
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert qa["epah_inventory_id"] == "H46"
    assert qa["qa"]["coverage"] == "27/27"
    assert qa["normalized_status_mapping_verified"] is False
    assert qa["source_values_preserved_as_decimals"] is True
    assert qa["qa"]["source_value_type"] == "non_negative_decimal_estimates"
    assert qa["qa"]["reconciliation_tolerance_persons"] == "0.000001"
    assert manifest["scientific_approval"] is False
    assert manifest["source_values_preserved_as_decimals"] is True
    assert manifest["official_source_mapping_verified"] is False
    assert manifest["original_export_sha256"] == hashlib.sha256(original.read_bytes()).hexdigest()
    assert manifest["normalized_source_csv_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert manifest["outputs_sha256"]["qa.json"] == hashlib.sha256((output / "qa.json").read_bytes()).hexdigest()


def test_out_directory_is_never_overwritten(tmp_path: Path) -> None:
    registry, source, original, _, _ = setup(tmp_path)
    output = tmp_path / "review"
    output.mkdir()
    (output / "important.txt").write_text("Keep!", encoding="utf-8")
    res = run_cli(registry, source, original, output)
    assert res.returncode != 0
    assert (output / "important.txt").read_text(encoding="utf-8") == "Keep!"


def test_wrong_sha_blocks_before_writes(tmp_path: Path) -> None:
    registry, source, original, _, _ = setup(tmp_path)
    output = tmp_path / "review"
    res = run_cli(registry, source, original, output,
                  "--expected-original-sha256", "0" * 64)
    assert res.returncode != 0 and "sha-256 mismatch" in res.stderr.lower()
    assert not output.exists()


def test_bad_expected_sha_blocks(tmp_path: Path) -> None:
    registry, source, original, _, _ = setup(tmp_path)
    output = tmp_path / "review"
    res = run_cli(registry, source, original, output,
                  "--expected-original-sha256", "wrong-format")
    assert res.returncode != 0 and "SHA" in res.stderr
    assert not output.exists()


def test_missing_original_blocks_without_output(tmp_path: Path) -> None:
    registry, source, original, _, _ = setup(tmp_path)
    original.unlink()
    out = tmp_path / "out"
    r = run_cli(registry, source, original, out)
    assert r.returncode != 0 and not out.exists()


def test_municipal_names_match_diacritics(tmp_path: Path) -> None:
    registry, source, _, reg, rows = setup(tmp_path)
    code = next(iter(reg))
    new_name = "Cuorgnè"
    for row in rows:
        if row["municipality_code"] == code:
            row["municipality"] = "Cuorgne"
    csv_file(source, rows)
    reg[code] = new_name
    observations, _ = h46.aggregate(source, reg)
    assert observations[0]["municipality"] == new_name


def test_population_not_denominator_regression(tmp_path: Path) -> None:
    _, source, _, registry, rows = setup(tmp_path)
    code = next(iter(registry))
    for row in rows:
        if row["municipality_code"] == code and row["labour_status"] == "inactive":
            row["persons"] = "435"
        if row["municipality_code"] == code and row["labour_status"] == "population_total":
            row["persons"] = "490"
    csv_file(source, rows)
    output, _ = h46.aggregate(source, registry)
    assert output[0]["unemployment_rate_15_plus_pct"] == "9.09"
    assert output[0]["population_15_plus"] == "490"

def test_fractional_estimates_preserved_and_no_intermediate_rounding(tmp_path: Path) -> None:
    _, path, _, reg, rows = setup(tmp_path)
    code = next(iter(reg))
    estimates = {
        "employed": "18",
        "unemployed": "1.499",
        "labour_force": "19.499",
        "inactive": "10.501",
        "unknown": "0",
        "population_total": "30",
    }
    for row in rows:
        if row["municipality_code"] == code:
            row["persons"] = estimates[row["labour_status"]]
    csv_file(path, rows)
    results, qa = h46.aggregate(path, reg)
    assert results[0]["unemployed_15_plus"] == "1.499"
    assert results[0]["labour_force_15_plus"] == "19.499"
    assert results[0]["unemployment_rate_15_plus_pct"] == "7.69"
    assert qa["sum_unemployed"] == "131.499"
    assert qa["sum_labour_force"] == "1449.499"
    assert Decimal(qa["weighted_unemployment_rate_15_plus_pct"]) == (
        Decimal("100") * Decimal("131.499") / Decimal("1449.499")
    ).quantize(Decimal("0.01"))


def test_decimal_representation_noise_is_tolerated_and_audited(tmp_path: Path) -> None:
    _, path, _, reg, rows = setup(tmp_path)
    code = next(iter(reg))
    for row in rows:
        if row["municipality_code"] == code and row["labour_status"] == "labour_force":
            row["persons"] = "55.0000000000004"
    csv_file(path, rows)
    results, qa = h46.aggregate(path, reg)
    assert results[0]["labour_force_15_plus"] == "55.0000000000004"
    assert Decimal(qa["max_labour_force_residual_persons"]) == Decimal("0.0000000000004")
    assert Decimal(qa["max_population_residual_persons"]) == Decimal("0.0000000000004")


def test_person_level_rounding_is_not_tolerated(tmp_path: Path) -> None:
    _, path, _, reg, rows = setup(tmp_path)
    code = next(iter(reg))
    for row in rows:
        if row["municipality_code"] == code and row["labour_status"] == "unemployed":
            row["persons"] = "5.4"
    csv_file(path, rows)
    with pytest.raises(ValueError, match="labour_force does not equal"):
        h46.aggregate(path, reg)
