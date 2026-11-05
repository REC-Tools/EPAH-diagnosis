"""Synthetic tests for immutable source-byte integrity on Windows checkout."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "source_csv_checkout", ROOT / "scripts/check_source_csv_checkout.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_exact_lf_bytes_remain_unchanged(tmp_path):
    original = b"municipality,value\nA,1\n"
    file = tmp_path / "example.csv"
    file.write_bytes(original)
    assert MODULE.check_one(file, hashlib.sha256(original).hexdigest()) == "ok"
    assert file.read_bytes() == original


def test_windows_checkout_crlf_detected_then_explicitly_repaired(tmp_path):
    original = b"municipality,value\nA,1\n"
    file = tmp_path / "example.csv"
    file.write_bytes(original.replace(b"\n", b"\r\n"))
    expected = hashlib.sha256(original).hexdigest()
    assert MODULE.check_one(file, expected) == "crlf_checkout"
    assert file.read_bytes() != original
    assert MODULE.check_one(file, expected, repair_crlf=True) == "repaired"
    assert file.read_bytes() == original


def test_modified_data_cannot_be_repaired(tmp_path):
    file = tmp_path / "example.csv"
    altered = b"municipality,value\r\nA,999\r\n"
    file.write_bytes(altered)
    original = b"municipality,value\nA,1\n"
    assert MODULE.check_one(
        file, hashlib.sha256(original).hexdigest(), repair_crlf=True
    ) == "unexpected_bytes"
    assert file.read_bytes() == altered


def test_missing_file_not_created_even_during_repair(tmp_path):
    file = tmp_path / "missing.csv"
    assert MODULE.check_one(file, "0" * 64, repair_crlf=True) == "missing"
    assert not file.exists()


def test_gitattributes_preserve_all_source_evidence_csvs_as_lf():
    lines = set((ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines())
    assert all(
        f"{relative} text eol=lf" in lines
        for relative in MODULE.REVIEWED_CSV_SHA256
    )
