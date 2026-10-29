"""Building-stock PR-04: counting, coverage, review and non-destructive writes."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from epah_diagnosis.building_stock_qa import prepare

ROOT = Path(__file__).resolve().parents[1]


def _module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


draft_script = _module("prepare_building_stock", "scripts/prepare_building_stock.py")
final_script = _module("finalize_building_stock", "scripts/finalize_building_stock_single_source.py")


def _data(total, pre):
    assert pre % 5 == 0
    old = [pre // 5] * 5
    ages = old + [total - pre, 0, 0, 0]
    return [total, *ages]


def _build_zip(large=False):
    lines1 = ["PROCOM;E3;E8;E9;E10;E11;E12;E13;E14;E15;E16"]
    lines2 = [lines1[0]]
    for n in range(1, 28):
        total, pre = (100, 50) if n == 1 else (1000, 10)
        values = _data(total, pre)
        lines1.append(f"001{n:03d};" + ";".join(map(str, values)))
    if large:
        for n in range(100, 1000):
            lines1.append(f"001{n:03d};" + ";".join(map(str, _data(100, 50))))
        for n in range(1, 6101):
            lines2.append(f"010{n:03d};" + ";".join(map(str, _data(100, 10))))
    else:
        lines1.append("002001;" + ";".join(map(str, _data(100, 50))))
        lines2.append("010001;" + ";".join(map(str, _data(100, 10))))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("R01_indicatori_2011_sezioni.csv", "\n".join(lines1) + "\n")
        z.writestr("R07_indicatori_2011_sezioni.csv", "\n".join(lines2) + "\n")
    return buf.getvalue()


@pytest.fixture
def source(tmp_path):
    registry = tmp_path / "municipalities.csv"
    registry.write_text(
        "municipality,istat_code\n" + "".join(
            f"Comune {i:02d},001{i:03d}\n" for i in range(1, 28)
        ), encoding="utf-8"
    )
    archive = tmp_path / "cpa.zip"
    archive.write_bytes(_build_zip())
    return registry, archive


def test_exact_27_and_weighted_benchmarks(source):
    registry, archive = source
    rows, benchmarks, qa = prepare(
        archive.read_bytes(), registry, min_italy=29, min_piemonte=28
    )
    assert len(rows) == 27
    assert rows[0]["share_pre_1981_pct"] == "50.00"
    assert rows[1]["share_pre_1981_pct"] == "1.00"
    assert benchmarks[0]["residential_buildings_total"] == "26100"
    assert benchmarks[0]["buildings_pre_1981"] == "310"
    assert benchmarks[0]["share_pre_1981_pct"] == "1.19"
    assert qa["validated_for_release"] is False
    assert qa["archive_sha256"] == hashlib.sha256(archive.read_bytes()).hexdigest()


def test_partial_national_archive_is_rejected_by_default(source):
    registry, archive = source
    with pytest.raises(ValueError, match="incomplete national"):
        prepare(archive.read_bytes(), registry)


def test_bad_input_and_missing_target_fail(source, tmp_path):
    registry, archive = source
    with pytest.raises(ValueError, match="ZIP"):
        prepare(b"not an archive", registry, min_italy=1, min_piemonte=1)
    registry.write_text(registry.read_text().replace("001027", "001999"), encoding="utf-8")
    with pytest.raises(ValueError, match="not found"):
        prepare(archive.read_bytes(), registry, min_italy=29, min_piemonte=28)


def test_draft_files_are_hashed_and_not_overwritten(source, tmp_path):
    registry, archive = source
    output = tmp_path / "draft"
    report = draft_script.prepare_files(
        archive, registry, output, min_italy=29, min_piemonte=28
    )
    assert report["coverage"] == 27
    stock = output / "building_stock_2011.csv"
    assert report["building_csv_sha256"] == hashlib.sha256(stock.read_bytes()).hexdigest()
    before = stock.read_bytes()
    with pytest.raises(FileExistsError):
        draft_script.prepare_files(
            archive, registry, output, min_italy=29, min_piemonte=28
        )
    assert stock.read_bytes() == before


def test_finalizer_requires_explicit_review_and_does_not_edit_matrix():
    matrix = ROOT / "data/verification_matrix.csv"
    before = matrix.read_bytes()
    command = [
        sys.executable, "scripts/finalize_building_stock_single_source.py"
    ]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert completed.returncode != 0
    assert "--approval" in completed.stderr
    assert matrix.read_bytes() == before


def test_legacy_finalizer_is_disabled():
    completed = subprocess.run(
        [sys.executable, "scripts/finalize_building_stock.py"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert completed.returncode != 0
    assert "disabled" in completed.stderr


def test_review_schema_rejects_missing_evidence(source, tmp_path):
    registry, archive = source
    output = tmp_path / "draft"
    qa = draft_script.prepare_files(archive, registry, output, min_italy=29, min_piemonte=28)
    with pytest.raises(ValueError, match="Approval metadata"):
        final_script.validate_approval(
            {}, qa, output / "building_stock_2011.csv",
            output / "building_stock_benchmarks_2011.csv", registry, archive,
        )


def test_existing_matrix_status_and_nonbuilding_rows_untouched():
    with (ROOT / "data/verification_matrix.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    building = [row for row in rows if row["indicator_id"] == "old_building_stock"]
    assert len(building) == 27
    assert all(row["status"] == "Dato validato" and row["value"] for row in building)
    assert len(rows) == 243
