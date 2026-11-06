"""H50 candidate: synthetic, fail-closed QA; no official or canonical data."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/prepare_low_education_25_64_v0_3.py"
SPEC = importlib.util.spec_from_file_location("h50", SCRIPT)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def registry(tmp_path: Path, n: int = 27) -> tuple[Path, dict[str, str]]:
    path = tmp_path / "municipalities.csv"
    values = {f"001{k:03d}": f"Comune {k}" for k in range(1, n + 1)}
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(("municipality", "istat_code"))
        for code, name in values.items():
            w.writerow((name, code))
    return path, values


def dataset(registry_data: dict[str, str], *, single: bool = False) -> list[dict[str, str]]:
    result = []
    for code, name in registry_data.items():
        for age in (("25-64",) if single else mod.AGE_BANDS):
            for grade, number in {
                "none": 1, "primary": 2, "lower_secondary": 4,
                "upper_or_tertiary": 13, "unknown": 0, "total": 20,
            }.items():
                result.append({"municipality_code": code, "municipality": name,
                               "reference_year": "2024", "age_band": age,
                               "sex": "total", "education_group": grade,
                               "persons": str(number)})
    return result


def write_csv(path: Path, data: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=mod.REQUIRED, lineterminator="\n")
        writer.writeheader()
        writer.writerows(data)


def prep(tmp_path: Path, **kwargs) -> tuple[Path, Path, list[dict[str, str]]]:
    path, reg = registry(tmp_path)
    values = dataset(reg, **kwargs)
    source = tmp_path / "normalized.csv"
    write_csv(source, values)
    return source, path, values


def test_h50_strictly_below_lower_secondary_25_64(tmp_path: Path) -> None:
    src, reg, _ = prep(tmp_path)
    values, qa = mod.aggregate(src, mod.read_registry(reg))
    assert len(values) == 27
    assert values[0]["residents_25_64_total"] == "160"
    assert values[0]["residents_below_lower_secondary_25_64"] == "24"
    assert values[0]["share_below_lower_secondary_25_64_pct"] == "15.00"
    assert qa["green_community_weighted_share_pct"] == "15.00"
    assert qa["residents_25_64_total"] == 27 * 8 * 20
    assert qa["age_band_mode"] == "eight_5_year_age_bands"


def test_single_25_64_age_aggregate_allowed_without_double_count(tmp_path: Path) -> None:
    src, reg, _ = prep(tmp_path, single=True)
    values, qa = mod.aggregate(src, mod.read_registry(reg))
    assert values[0]["residents_25_64_total"] == "20"
    assert qa["age_band_mode"] == "single_25_64_age_band"


def test_unknown_education_remains_in_denominator(tmp_path: Path) -> None:
    src, reg, data = prep(tmp_path)
    for row in data:
        if row["education_group"] == "unknown":
            row["persons"] = "2"
        elif row["education_group"] == "total":
            row["persons"] = "22"
    write_csv(src, data)
    values, qa = mod.aggregate(src, mod.read_registry(reg))
    assert values[0]["residents_25_64_total"] == "176"
    assert values[0]["residents_with_unknown_education_25_64"] == "16"
    assert values[0]["share_below_lower_secondary_25_64_pct"] == "13.64"
    assert qa["residents_with_unknown_education_25_64"] == 27 * 16


@pytest.mark.parametrize(("change", "error"), [
    (lambda v: v[0].update(age_band="15-19"), "unsupported age band"),
    (lambda v: v[0].update(reference_year="2023"), "required census reference year"),
    (lambda v: v[0].update(sex="female"), "sex must be the population total"),
    (lambda v: v[0].update(municipality="Other"), "municipality mismatch"),
    (lambda v: v[0].update(education_group="middle_school_unknown"), "unknown education group"),
    (lambda v: v[0].update(persons=".."), "non-negative integer"),
    (lambda v: v[0].update(persons="-1"), "non-negative integer"),
    (lambda v: v[0].update(persons="1.234"), "non-negative integer"),
    (lambda v: v[0].update(municipality_code="001999"), "unexpected ISTAT code"),
])
def test_reject_bad_categories_and_codes(tmp_path: Path, change, error: str) -> None:
    src, reg, data = prep(tmp_path)
    change(data)
    write_csv(src, data)
    with pytest.raises(ValueError, match=error):
        mod.aggregate(src, mod.read_registry(reg))


def test_reject_duplicate_rows(tmp_path: Path) -> None:
    src, reg, data = prep(tmp_path)
    data.append(data[0].copy())
    write_csv(src, data)
    with pytest.raises(ValueError, match="duplicate"):
        mod.aggregate(src, mod.read_registry(reg))


def test_reject_missing_age_group(tmp_path: Path) -> None:
    src, reg, data = prep(tmp_path)
    data = [r for r in data if not (r["municipality_code"] == "001001" and r["age_band"] == "40-44")]
    write_csv(src, data)
    with pytest.raises(ValueError, match="incomplete or mixed"):
        mod.aggregate(src, mod.read_registry(reg))


def test_reject_missing_category_even_if_row_would_be_zero(tmp_path: Path) -> None:
    src, reg, data = prep(tmp_path)
    data = [r for r in data if not (r["municipality_code"] == "001001" and r["age_band"] == "25-29" and r["education_group"] == "unknown")]
    write_csv(src, data)
    with pytest.raises(ValueError, match="missing/extra education categories"):
        mod.aggregate(src, mod.read_registry(reg))


def test_reject_mismatch_all_levels_total(tmp_path: Path) -> None:
    src, reg, data = prep(tmp_path)
    data[5]["persons"] = "21"
    write_csv(src, data)
    with pytest.raises(ValueError, match="does not equal sum"):
        mod.aggregate(src, mod.read_registry(reg))


def test_reject_zero_denominator(tmp_path: Path) -> None:
    src, reg, data = prep(tmp_path)
    for row in data:
        if row["municipality_code"] == "001001":
            row["persons"] = "0"
    write_csv(src, data)
    with pytest.raises(ValueError, match="zero denominator"):
        mod.aggregate(src, mod.read_registry(reg))


def test_reject_mixed_aggregate_and_five_year_bins(tmp_path: Path) -> None:
    src, reg, data = prep(tmp_path)
    for row in data:
        if row["municipality_code"] == "001001":
            row["age_band"] = "25-64"
    write_csv(src, data)
    with pytest.raises(ValueError, match="duplicate|Inconsistent age aggregation"):
        mod.aggregate(src, mod.read_registry(reg))


def test_registry_requires_27_municipalities(tmp_path: Path) -> None:
    reg, _ = registry(tmp_path, n=26)
    with pytest.raises(ValueError, match="Expected 27"):
        mod.read_registry(reg)


def run_cli(tmp_path: Path, wrong_hash: bool = False, existing: bool = False):
    src, reg, _ = prep(tmp_path)
    original = tmp_path / "original_export.csv"
    original.write_bytes(b"ISTAT source export, bytes only; QA pending\n")
    out = tmp_path / "review"
    if existing:
        out.mkdir()
        (out / "keep.txt").write_text("original", encoding="utf-8")
    digest = "0" * 64 if wrong_hash else hashlib.sha256(original.read_bytes()).hexdigest()
    args = [sys.executable, str(SCRIPT), "--normalized-csv", str(src),
            "--original-export", str(original), "--registry", str(reg),
            "--expected-original-sha256", digest, "--out-dir", str(out)]
    return subprocess.run(args, text=True, capture_output=True, check=False), out, src, original, reg


def test_cli_writes_27_preview_and_provenance_only(tmp_path: Path) -> None:
    process, out, src, original, reg = run_cli(tmp_path)
    assert process.returncode == 0, process.stderr
    with (out / "low_education_25_64_preview.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 27
    assert all(r["status"] == mod.STATUS for r in rows)
    assert all(r["share_below_lower_secondary_25_64_pct"] == "15.00" for r in rows)
    qa = json.loads((out / "qa.json").read_text(encoding="utf-8"))
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert qa["epah_inventory_id"] == "H50"
    assert manifest["scientific_approval"] is False
    assert manifest["normalized_export_mapping_verified"] is False
    assert manifest["original_export_sha256"] == hashlib.sha256(original.read_bytes()).hexdigest()
    assert manifest["outputs_sha256"]["low_education_25_64_preview.csv"] == hashlib.sha256((out / "low_education_25_64_preview.csv").read_bytes()).hexdigest()


def test_cli_does_not_overwrite_prior_review(tmp_path: Path) -> None:
    proc, out, *_ = run_cli(tmp_path, existing=True)
    assert proc.returncode != 0
    assert (out / "keep.txt").read_text(encoding="utf-8") == "original"


def test_cli_rejects_wrong_original_sha_without_creating_outputs(tmp_path: Path) -> None:
    proc, out, *_ = run_cli(tmp_path, wrong_hash=True)
    assert proc.returncode != 0
    assert "SHA-256 mismatch" in proc.stderr
    assert not out.exists()
