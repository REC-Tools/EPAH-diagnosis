"""Offline synthetic POSAS 2026 source preflight tests; no measured data used."""
from __future__ import annotations

import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "check_posas_2026_source_v0_3.py"
SPEC = importlib.util.spec_from_file_location("posas_2026_source_check", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check)


def archive(path: Path, *, year: str = "2026", header: str = "Codice Comune;Comune;Età;Maschi;Femmine;Totale", members: int = 1) -> Path:
    content = f"Popolazione residente al 1 gennaio {year} (stima)\n{header}\n001007;Alpette;0;1;0;1\n"
    with zipfile.ZipFile(path, "w") as f:
        for n in range(members):
            f.writestr(f"source_{n}.csv", content.encode("utf-8"))
    return path


def test_valid_source_receipt_is_not_validation(tmp_path: Path) -> None:
    p = archive(tmp_path / "POSAS_2026_it_Comuni.zip")
    receipt = check.check_source(p)
    assert receipt["header_2026_observed"] is True
    assert receipt["status"] == "technical_draft_do_not_publish"
    assert receipt["publication_allowed"] is False
    assert receipt["scientific_approval"] is False
    assert receipt["file_origin_independently_authenticated"] is False
    assert receipt["csv_member"] == "source_0.csv"
    assert len(receipt["csv_member_sha256"]) == 64


def test_wrong_reference_year_fails(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="reference year 2026"):
        check.check_source(archive(tmp_path / "sample.zip", year="2025"))


def test_missing_year_in_preamble_fails(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="reference year 2026"):
        check.check_source(archive(tmp_path / "sample.zip", year="unspecified"))


def test_missing_required_header_fails(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="CSV header"):
        check.check_source(archive(tmp_path / "sample.zip", header="X;Y;Z;Q"))


def test_multiple_members_fail_without_selection(tmp_path: Path) -> None:
    path = archive(tmp_path / "sample.zip", members=2)
    with pytest.raises(ValueError, match="Multiple CSV members"):
        check.check_source(path)
    assert check.check_source(path, member="source_0.csv")["csv_member"] == "source_0.csv"


def test_nonzip_fails(tmp_path: Path) -> None:
    path = tmp_path / "bad.zip"
    path.write_text("<html>not source</html>")
    with pytest.raises(ValueError, match="not a ZIP"):
        check.check_source(path)


def test_cli_never_overwrites_existing_evidence(tmp_path: Path) -> None:
    path = archive(tmp_path / "sample.zip")
    output = tmp_path / "receipt.json"
    output.write_text("original", encoding="utf-8")
    assert check.main(["--source-zip", str(path), "--out-file", str(output)]) == 1
    assert output.read_text() == "original"


def test_cli_writes_receipt_for_valid_archive(tmp_path: Path) -> None:
    path = archive(tmp_path / "sample.zip")
    output = tmp_path / "receipt.json"
    assert check.main(["--source-zip", str(path), "--out-file", str(output)]) == 0
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["scientific_approval"] is False
    assert receipt["original_zip_bytes"] == path.stat().st_size
