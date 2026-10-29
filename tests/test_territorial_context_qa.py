"""PR-05: offline, code-matched altitude and categorical SNAI QA."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest
from openpyxl import Workbook

from epah_diagnosis.altitude import parse_altitude_workbook
from epah_diagnosis.snai import parse_snai_workbook
from epah_diagnosis.territorial_context_qa import CONFIG, prepare, write_draft

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data/municipalities.csv"


def _official_like(indicator, *, edit=None, include_extra=0):
    wb = Workbook()
    sheet = wb.active
    if indicator == "mean_altitude":
        sheet.append([
            "PRO_COM", "COMUNE", "ALT MIN", "ALT MAX", "MEDIA",
        ])
    else:
        sheet.append([
            "PROCOM_T", "COMUNE_30sett20", "MAPPA AI 2020\n\nCOD_AI_2020",
        ])
    with REGISTRY.open(encoding="utf-8", newline="") as handle:
        names = list(csv.DictReader(handle))
    for i, target in enumerate(names):
        if indicator == "mean_altitude":
            row = [int(target["istat_code"]), target["municipality"], 100, 1900, 500 + i]
        else:
            row = [target["istat_code"], target["municipality"], "E" if i < 12 else "C"]
        if edit is not None:
            row = edit(i, row)
        sheet.append(row)
    for i in range(include_extra):
        code = str(100000 + i)
        if indicator == "mean_altitude":
            sheet.append([int(code), "Extra " + str(i), 20, 1000, 250])
        else:
            sheet.append([code, "Extra " + str(i), "B"])
    dest = io.BytesIO()
    wb.save(dest)
    return dest.getvalue()


@pytest.mark.parametrize("indicator", sorted(CONFIG))
def test_full_code_join_27_municipalities(indicator):
    payload = _official_like(indicator)
    rows, summary, report = prepare(
        indicator, payload, REGISTRY, minimum_national_records=27,
    )
    assert len(rows) == report["target_municipalities"] == 27
    assert report["source_file_sha256"] == hashlib.sha256(payload).hexdigest()
    assert report["validated_for_release"] is False
    assert report["verified_source_authenticity"] is False
    assert all(len(row["municipality_code"]) == 6 for row in rows)
    if indicator == "mean_altitude":
        assert rows[0]["mean_altitude_m"] == "500.00"
        assert summary[0]["municipality_count"] == "27"
        assert float(summary[0]["mean_of_municipal_mean_altitude_m"]) > 500
    else:
        assert rows[0]["snai_class"] == "E"
        assert summary[0]["class_E"] == "12"
        assert summary[0]["class_C"] == "15"
        assert summary[0]["inner_area_municipalities_D_E_F"] == "12"
        assert {row["snai_class"] for row in rows} == {"E", "C"}


def test_altitude_and_snai_parse_six_digit_istat_codes():
    a = parse_altitude_workbook(_official_like("mean_altitude"))
    s = parse_snai_workbook(_official_like("snai_classification"))
    assert a[0].municipality_code == "001007"
    assert s[0].municipality_code == "001007"


@pytest.mark.parametrize("indicator", sorted(CONFIG))
def test_partial_national_workbook_cannot_be_accepted_by_default(indicator):
    with pytest.raises(ValueError, match="Incomplete national workbook"):
        prepare(indicator, _official_like(indicator), REGISTRY)


@pytest.mark.parametrize("indicator", sorted(CONFIG))
def test_duplicate_istat_code_fails(indicator):
    def edit(i, row):
        if i == 1:
            row[0] = "001007" if indicator == "snai_classification" else 1007
        return row
    with pytest.raises(ValueError, match="Duplicate ISTAT"):
        prepare(indicator, _official_like(indicator, edit=edit),
                REGISTRY, minimum_national_records=27)


@pytest.mark.parametrize("indicator", sorted(CONFIG))
def test_inconsistent_name_code_join_fails(indicator):
    def edit(i, row):
        if i == 0:
            row[1] = "Wrong Municipality"
        return row
    with pytest.raises(ValueError, match="Name/code mismatch"):
        prepare(indicator, _official_like(indicator, edit=edit),
                REGISTRY, minimum_national_records=27)


@pytest.mark.parametrize("indicator", sorted(CONFIG))
def test_missing_code_fails(indicator):
    def edit(i, row):
        if i == 0:
            row[0] = None
        return row
    with pytest.raises(ValueError, match="Target ISTAT codes absent"):
        prepare(indicator, _official_like(indicator, edit=edit),
                REGISTRY, minimum_national_records=27)


def test_altitude_out_of_min_max_bounds_fails():
    def bad(i, row):
        if i == 0:
            row[4] = 3000
        return row
    with pytest.raises(ValueError, match="Mean above maximum"):
        prepare("mean_altitude", _official_like("mean_altitude", edit=bad),
                REGISTRY, minimum_national_records=27)


def test_invalid_snai_category_never_silently_accepted():
    def bad(i, row):
        if i == 0:
            row[2] = "Z"
        return row
    with pytest.raises(ValueError, match="Target ISTAT codes absent"):
        prepare("snai_classification", _official_like("snai_classification", edit=bad),
                REGISTRY, minimum_national_records=26)


@pytest.mark.parametrize("indicator", sorted(CONFIG))
def test_draft_outputs_and_hashes_no_overwrite(indicator, tmp_path):
    source = tmp_path / "source.xlsx"
    source.write_bytes(_official_like(indicator))
    dest = tmp_path / "draft"
    qa = write_draft(indicator, source, REGISTRY, dest, minimum_national_records=27)
    obs = (dest / CONFIG[indicator]["output"]).read_bytes()
    assert qa["data_csv_sha256"] == hashlib.sha256(obs).hexdigest()
    assert qa["qa_status"] == "technical_checks_only"
    with pytest.raises(FileExistsError):
        write_draft(indicator, source, REGISTRY, dest, minimum_national_records=27)
    assert (dest / CONFIG[indicator]["output"]).read_bytes() == obs


@pytest.mark.parametrize("script", [
    "scripts/finalize_mean_altitude.py",
    "scripts/finalize_snai_classification.py",
])
def test_promoters_require_explicit_human_approval_without_writing(script):
    matrix = ROOT / "data/verification_matrix.csv"
    before = matrix.read_bytes()
    command = subprocess.run(
        [sys.executable, script], cwd=ROOT, capture_output=True, text=True,
    )
    assert command.returncode != 0
    assert "--approval" in command.stderr
    assert matrix.read_bytes() == before


def test_existing_matrix_has_27_evidence_checked_rows_per_indicator():
    with (ROOT / "data/verification_matrix.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 243
    for indicator in CONFIG:
        selected = [r for r in rows if r["indicator_id"] == indicator]
        assert len(selected) == 27
        assert all(r["status"] == "Dato validato" and r["value"] for r in selected)


def test_review_fails_closed_without_evidence(tmp_path):
    from epah_diagnosis.territorial_context_qa import promote
    indicator = "snai_classification"
    source = tmp_path / "source.xlsx"
    source.write_bytes(_official_like(indicator))
    draft = tmp_path / "draft"
    write_draft(indicator, source, REGISTRY, draft, minimum_national_records=27)
    approval = tmp_path / "approval.json"
    approval.write_text(json.dumps({"decision": "approved"}), encoding="utf-8")
    with pytest.raises(ValueError, match="metadata"):
        promote(indicator, source, REGISTRY, draft, approval,
                ROOT / "data/verification_matrix.csv", tmp_path / "published")
    assert not (tmp_path / "published").exists()
