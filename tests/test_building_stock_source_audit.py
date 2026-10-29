"""PR-09b: raw ISTAT CPA 2011 audit and download, using *synthetic* section data."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from epah_diagnosis.building_stock_source_audit import (
    CPA_2011_URL, _count, download_official_cpa,
    independent_r01_counts, verify_draft_independently,
)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_building_stock_source import run

HEAD = "PROCOM;E3;E8;E9;E10;E11;E12;E13;E14;E15;E16"
REGION1 = "R01_indicatori_2011_sezioni.csv"
REGION7 = "R07_indicatori_2011_sezioni.csv"


def zip_fixture(*, full=False, suppressed=False, duplicate=False, bad_ages=False):
    r01 = [HEAD]
    r07 = [HEAD]
    for i in range(1, 28):
        code = f"001{i:03d}"
        if i == 1:
            # Deliberately nontrivial numerator so an unweighted mean differs
            # sharply from the correct building-count-weighted benchmark.
            values = [100, 10, 10, 10, 10, 10, 20, 10, 10, 10]
        else:
            values = [1000, 2, 2, 2, 2, 2, 200, 200, 200, 200]
        if bad_ages and i == 2:
            values[1] = 2000
        if suppressed and i == 2:
            values[2] = ".."
        r01.append(code+";"+";".join(map(str, values)))
    if duplicate:
        r01.append(r01[2])
    if full:
        for i in range(100, 1000):
            r01.append(f"001{i:03d};100;10;10;10;10;10;10;10;10;10")
        for i in range(1, 6101):
            r07.append(f"010{i:03d};100;10;10;10;10;10;10;10;10;10")
    else:
        r01.append("002001;100;10;10;10;10;10;10;10;10;10")
        r07.append("010001;100;10;10;10;10;10;10;10;10;10")
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("Sections/"+REGION1, "\n".join(r01)+"\n")
        archive.writestr("Sections/"+REGION7, "\n".join(r07)+"\n")
    return mem.getvalue()


@pytest.fixture
def local(tmp_path):
    registry = tmp_path / "municipalities.csv"
    registry.write_text(
        "municipality,istat_code\n" +
        "".join(f"Comune {i:02d},001{i:03d}\n" for i in range(1, 28)),
        encoding="utf-8",
    )
    original = tmp_path / "dati-cpa_2011.zip"
    original.write_bytes(zip_fixture(full=True))
    return registry, original


def test_independent_raw_recount_covers_27_and_weighted_share(local):
    registry, path = local
    rows, summary = independent_r01_counts(path.read_bytes(), registry)
    assert len(rows) == 27
    assert rows[0]["municipality_code"] == "001001"
    assert rows[0]["residential_buildings_total"] == 100
    assert rows[0]["buildings_pre_1981"] == 50
    assert rows[0]["share_pre_1981_pct"] == "50.00"
    assert rows[1]["residential_buildings_total"] == 1000
    assert rows[1]["buildings_pre_1981"] == 10
    assert rows[1]["share_pre_1981_pct"] == "1.00"
    assert summary["selected_sections"] == 27
    assert summary["target_count"] == 27
    assert summary["green_community_weighted_pct"] == 1.19
    assert summary["unweighted_mean_pct"] > 2


def test_full_draft_then_independent_audit_is_staged_not_promoted(local, tmp_path):
    registry, original = local
    destination = tmp_path / "draft"
    matrix = ROOT / "data/verification_matrix.csv"
    before = hashlib.sha256(matrix.read_bytes()).hexdigest()
    result = run(original, registry, destination)
    assert result["technical_pass"] is True
    assert result["validated_for_release"] is False
    assert result["matrix_modified"] is False
    assert result["automatic_promotions"] == 0
    assert result["technical_qa"]["target_municipalities"] == 27
    assert result["technical_qa"]["italy_municipalities"] >= 7000
    assert result["technical_qa"]["piemonte_municipalities"] >= 900
    assert result["independent_qa"]["unmatched_values"] == 0
    assert result["independent_qa"]["green_community_buildings_pre_1981_pct"] == 1.19
    assert len(list(csv.DictReader((destination / "building_stock_2011.csv").open(encoding="utf-8")))) == 27
    independent = json.loads((destination / "independent_raw_r01_audit.json").read_text())
    assert independent["municipalities_compared"] == 27
    assert len(independent["municipality_rows"]) == 27
    for name, entry in result["files"].items():
        assert entry["sha256"] == hashlib.sha256((destination / name).read_bytes()).hexdigest()
    assert before == hashlib.sha256(matrix.read_bytes()).hexdigest()
    with pytest.raises(FileExistsError, match="QA already exists"):
        run(original, registry, destination)


def test_independent_detects_mutated_produced_value(local, tmp_path):
    registry, original = local
    dest = tmp_path / "qa"
    run(original, registry, dest)
    data = list(csv.DictReader((dest / "building_stock_2011.csv").open(encoding="utf-8")))
    data[0]["buildings_pre_1981"] = "999"
    benchmarks = list(csv.DictReader((dest / "building_stock_benchmarks_2011.csv").open(encoding="utf-8")))
    report = verify_draft_independently(original.read_bytes(), registry, data, benchmarks)
    assert report["technical_pass"] is False
    assert any(d.get("field") == "buildings_pre_1981" for d in report["differences"])


def test_suppressed_raw_census_value_never_becomes_zero(local, tmp_path):
    registry, _ = local
    with pytest.raises(ValueError, match="Missing/suppressed/noninteger"):
        independent_r01_counts(zip_fixture(full=True, suppressed=True), registry)
    with pytest.raises(ValueError, match="Missing/suppressed/noninteger"):
        _count("-", municipality="Alpette", field="E8")


def test_corrupt_age_bucket_rejected(local):
    registry, _ = local
    with pytest.raises(ValueError, match="Inconsistent"):
        independent_r01_counts(zip_fixture(full=True, bad_ages=True), registry)


def test_missing_or_duplicate_raw_R01_member_rejected(local):
    registry, _ = local
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(REGION7, HEAD + "\n")
    with pytest.raises(ValueError, match="exactly one Piemonte"):
        independent_r01_counts(buf.getvalue(), registry)
    # Duplicates selected row counts are not silently removed: this remains
    # a separate scientific review question, not a primary-key dedupe.


def test_cli_help_and_missing_source_fails_closed(tmp_path):
    cmd = ROOT / "scripts/audit_building_stock_source.py"
    help_result = subprocess.run([sys.executable, str(cmd), "--help"],
                                 cwd=ROOT, capture_output=True, text=True)
    assert help_result.returncode == 0, help_result.stderr
    assert "--download" in help_result.stdout
    assert "--source-zip" in help_result.stdout
    out = tmp_path / "out"
    missing = subprocess.run(
        [sys.executable, str(cmd), "--source-zip", str(tmp_path / "absent.zip"),
         "--out-dir", str(out)],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert missing.returncode != 0
    assert not out.exists()


def test_download_rejects_nonzip_html_and_does_not_save(monkeypatch, tmp_path):
    from epah_diagnosis import building_stock_source_audit as mod

    class Response:
        headers = {"Content-Type": "text/html"}
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def geturl(self): return CPA_2011_URL
        def read(self, n): return b"<html>Access denied</html>" if not hasattr(self, "read_once") else b""
        # This mock tests the non-ZIP response independently of size.

    class OnceResponse(Response):
        def __init__(self): self.read_once = False
        def read(self, n):
            if self.read_once: return b""
            self.read_once = True
            return b"<html>Access denied</html>"

    monkeypatch.setattr(mod.urllib.request, "urlopen", lambda request, timeout: OnceResponse())
    dest = tmp_path / "original.zip"
    with pytest.raises(ValueError, match="not ZIP"):
        download_official_cpa(dest)
    assert not dest.exists()
    assert not list(tmp_path.glob("*.part"))


def test_download_rejects_untrusted_redirect(monkeypatch, tmp_path):
    from epah_diagnosis import building_stock_source_audit as mod

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def geturl(self): return "https://untrusted.example.net/archives/cpa.zip"

    monkeypatch.setattr(mod.urllib.request, "urlopen", lambda request, timeout: Response())
    with pytest.raises(ValueError, match="outside official ISTAT HTTPS"):
        download_official_cpa(tmp_path / "not-downloaded.zip")


def test_download_accepts_verified_zip_and_preserves_hash(monkeypatch, tmp_path):
    from epah_diagnosis import building_stock_source_audit as mod
    data = zip_fixture()

    class Response:
        headers = {"Content-Type": "application/zip"}
        def __init__(self): self.done = False
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def geturl(self): return CPA_2011_URL
        def read(self, n):
            if self.done: return b""
            self.done = True
            return data

    monkeypatch.setattr(mod.urllib.request, "urlopen", lambda request, timeout: Response())
    dest = tmp_path / "original.zip"
    outcome = download_official_cpa(dest)
    assert dest.read_bytes() == data
    assert outcome["sha256"] == hashlib.sha256(data).hexdigest()
    assert outcome["license_reviewed"] is False
    with pytest.raises(FileExistsError):
        download_official_cpa(dest)


def test_real_matrix_building_rows_staged_for_review():
    with (ROOT / "data/verification_matrix.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    building = [x for x in rows if x["indicator_id"] == "old_building_stock"]
    assert len(building) == 27
    assert all(x["status"] == "Dato validato" and x["value"] for x in building)
