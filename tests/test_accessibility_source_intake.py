"""Offline source-intake regression tests: every fixture is SYNTHETIC."""
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

from epah_diagnosis import accessibility_source_intake as official

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from acquire_accessibility_inputs import run


def zipdata(files):
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w", compression=zipfile.ZIP_DEFLATED) as out:
        for filename, content in files.items():
            out.writestr(filename, content)
    return data.getvalue()


def road_data():
    return zipdata({
        "TO_2021.csv": "OR_PROCOM;DEST_PROCOM;TEP_TOT;KM_TOT\n001007;001098;21,4;14,2\n",
    })


def boundaries_data():
    return zipdata({
        "Com01012026_g_WGS84.shp": b"synthetic geometry stub",
        "Com01012026_g_WGS84.shx": b"synthetic index stub",
        "Com01012026_g_WGS84.dbf": b"synthetic attributes stub",
    })


def sample_file(tmp_path, filename, raw):
    p = tmp_path / filename
    p.write_bytes(raw)
    return p


def test_preflight_valid_archive_headers_and_hash(tmp_path):
    road = sample_file(tmp_path, "Piemonte.zip", road_data())
    checked = official.check_original("road", road)
    assert checked["technical_preflight_passed"]
    assert checked["csv_members"] == 1
    assert checked["sha256"] == hashlib.sha256(road.read_bytes()).hexdigest()
    assert checked["travel_times_verified"] is False if "travel_times_verified" in checked else True
    assert checked["data_values_validated"] is False
    boundary = sample_file(tmp_path, "Limiti01012026_g.zip", boundaries_data())
    geo = official.check_original("boundaries", boundary)
    assert geo["technical_preflight_passed"]
    assert geo["municipality_shapefile"].endswith(".shp")


def test_html_is_not_official_zip_or_csv(tmp_path):
    failed = sample_file(tmp_path, "bad.zip", b"<html>Blocked by provider</html>")
    with pytest.raises(ValueError, match="expected ZIP"):
        official.check_original("road", failed)
    bogus = sample_file(tmp_path, "data.csv", b"<html>Rate limited</html>")
    with pytest.raises(ValueError, match="returned HTML"):
        official.check_original("school_registry", bogus)


def test_schema_missing_in_road_and_school(tmp_path):
    road = sample_file(tmp_path, "road.zip", zipdata({"TO.csv": "wrong;header\n1;2\n"}))
    with pytest.raises(ValueError, match="OR_PROCOM"):
        official.check_original("road", road)
    sc = sample_file(tmp_path, "school.csv", b"NotReally;Columns\n1;2\n")
    with pytest.raises(ValueError, match="school code"):
        official.check_original("school_registry", sc)
    route = sample_file(tmp_path, "route.csv", b"CodiceScuola;DescrizioneComune\nAA0001;Ivrea\n")
    with pytest.raises(ValueError, match="pathway type"):
        official.check_original("school_pathways", route)


def test_mim_csv_headers_and_stable_school_vintage(tmp_path):
    reg = sample_file(
        tmp_path, "schools.csv",
        b"CodiceScuola;DescrizioneComune;Regione\nAA00001;Ivrea;Piemonte\n",
    )
    routes = sample_file(
        tmp_path, "paths.csv",
        b"CodiceScuola;TipoPercorso;Percorso\nAA00001;Liceo;Scientifico\n",
    )
    for sid, path in [("school_registry", reg), ("school_pathways", routes)]:
        report = official.check_original(sid, path)
        assert report["vintage"].startswith("2024/25")
        assert report["format"] == "csv"


def test_cli_local_files_reports_preflight_not_route_validation(tmp_path):
    report = run(
        tmp_path / "qa",
        selected=("road", "boundaries"),
        local={
            "road": sample_file(tmp_path, "original_road.zip", road_data()),
            "boundaries": sample_file(tmp_path, "original_boundaries.zip", boundaries_data()),
        },
    )
    assert report["all_selected_inputs_available"]
    assert report["technical_pass_count"] == 2
    assert report["travel_times_verified"] is False
    assert report["matrix_modified"] is False
    assert report["automatic_promotions"] == 0
    assert report["validated_for_release"] is False
    assert (tmp_path / "qa" / "audit.json").is_file()
    with pytest.raises(FileExistsError):
        run(tmp_path / "qa", selected=("road",))


def test_cli_reports_missing_download_or_file_fail_closed(tmp_path):
    report = run(tmp_path / "incomplete", selected=("road", "boundaries"))
    assert not report["all_selected_inputs_available"]
    assert report["technical_pass_count"] == 0
    assert all(x["status"] == "not_acquired"
               for x in report["original_source_results"].values())
    got = run(
        tmp_path / "missing",
        selected=("road",),
        local={"road": tmp_path / "no-file.zip"},
    )
    assert got["original_source_results"]["road"]["status"] == "blocked"
    assert "ValueError" in got["original_source_results"]["road"]["error"]


def test_downloader_rejects_nonofficial_redirect_before_saving(monkeypatch, tmp_path):
    class FakeResponse:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def geturl(self): return "https://evil.example.com/redirected.zip"
    monkeypatch.setattr(official.urllib.request, "urlopen",
                        lambda req, timeout: FakeResponse())
    dest = tmp_path / "out.zip"
    with pytest.raises(ValueError, match="Redirect outside official"):
        official.download_original("road", dest)
    assert not dest.exists()


def test_downloader_rejects_login_page_and_cleans_part_file(monkeypatch, tmp_path):
    class FakeResponse:
        headers = {"Content-Type": "text/html"}
        def __init__(self): self.stream = io.BytesIO(b"<html>Please log in</html>")
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def geturl(self): return official.SOURCE_SPECS["road"]["url"]
        def read(self, n): return self.stream.read(n)
    monkeypatch.setattr(official.urllib.request, "urlopen",
                        lambda req, timeout: FakeResponse())
    dest = tmp_path / "orig.zip"
    with pytest.raises(ValueError, match="expected ZIP"):
        official.download_original("road", dest)
    assert not dest.exists()
    assert not list(tmp_path.glob("*.partial"))


def test_downloader_preserves_verbatim_bytes_and_never_overwrites(monkeypatch, tmp_path):
    original = road_data()
    class FakeResponse:
        headers = {"Content-Type": "application/zip"}
        def __init__(self): self.stream = io.BytesIO(original)
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def geturl(self): return official.SOURCE_SPECS["road"]["url"]
        def read(self, n): return self.stream.read(n)
    monkeypatch.setattr(official.urllib.request, "urlopen",
                        lambda req, timeout: FakeResponse())
    dest = tmp_path / "Piemonte.zip"
    item = official.download_original("road", dest)
    assert dest.read_bytes() == original
    assert item["sha256"] == hashlib.sha256(original).hexdigest()
    assert item["data_values_validated"] is False
    with pytest.raises(FileExistsError):
        official.download_original("road", dest)


def test_script_help_and_strict_unacquired_code(tmp_path):
    path = ROOT / "scripts/acquire_accessibility_inputs.py"
    help_run = subprocess.run(
        [sys.executable, str(path), "--help"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert help_run.returncode == 0, help_run.stderr
    assert "--road-zip" in help_run.stdout
    incomplete = subprocess.run([
        sys.executable, str(path), "--out-dir", str(tmp_path / "nothing"),
        "--strict",
    ], cwd=ROOT, capture_output=True, text=True)
    assert incomplete.returncode == 1
    assert "0/2" in incomplete.stdout


class _HttpReply:
    def __init__(self, content, *, status=200, headers=None):
        self.payload = io.BytesIO(content)
        self.status = status
        self.headers = headers or {"Content-Type": "application/zip"}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def geturl(self):
        return official.SOURCE_SPECS["road"]["url"]

    def read(self, amount):
        return self.payload.read(amount)


def _fake_transport(monkeypatch, answers):
    import urllib.error
    pending = iter(answers)
    requests = []
    def fake_open(request, timeout):
        requests.append(request)
        answer = next(pending)
        if isinstance(answer, Exception):
            raise answer
        return answer
    monkeypatch.setattr(official.urllib.request, "urlopen", fake_open)
    monkeypatch.setattr(official.time, "sleep", lambda _: None)
    return requests


def test_network_winerror_10060_retries_https_then_saves_original(monkeypatch, tmp_path):
    import urllib.error
    raw = road_data()
    requests = _fake_transport(monkeypatch, [
        urllib.error.URLError("[WinError 10060] connect timeout"),
        _HttpReply(raw, headers={
            "Content-Type": "application/zip", "Content-Length": str(len(raw)),
        }),
    ])
    path = tmp_path / "Piemonte.zip"
    result = official.download_original("road", path, attempts=2, timeout=1)
    assert path.read_bytes() == raw
    assert result["network_attempts"] == 2
    assert len(requests) == 2
    assert requests[0].full_url.startswith("https://www.istat.it/")
    assert not requests[1].has_header("Range")


def test_ssl_unexpected_eof_retries_without_disabling_certificate_check(monkeypatch, tmp_path):
    import urllib.error
    raw = road_data()
    requests = _fake_transport(monkeypatch, [
        urllib.error.URLError("[SSL: UNEXPECTED_EOF_WHILE_READING]"),
        _HttpReply(raw),
    ])
    target = tmp_path / "road.zip"
    assert official.download_original("road", target, attempts=2, timeout=1)["network_attempts"] == 2
    assert target.read_bytes() == raw
    assert len(requests) == 2
    assert requests[0].get_header("Accept-encoding") == "identity"


def test_retry_resumes_partial_zip_only_with_validated_http_206(monkeypatch, tmp_path):
    raw = road_data()
    halfway = len(raw) // 2
    replies = [
        _HttpReply(raw[:halfway], headers={
            "Content-Length": str(len(raw)),
            "ETag": '"version1"',
        }),
        _HttpReply(raw[halfway:], status=206, headers={
            "Content-Length": str(len(raw) - halfway),
            "Content-Range": f"bytes {halfway}-{len(raw)-1}/{len(raw)}",
            "ETag": '"version1"',
        }),
    ]
    requests = _fake_transport(monkeypatch, replies)
    path = tmp_path / "road.zip"
    result = official.download_original("road", path, attempts=2)
    assert path.read_bytes() == raw
    assert result["network_attempts"] == 2
    assert requests[1].get_header("Range") == f"bytes={halfway}-"
    assert requests[1].get_header("If-range") == '"version1"'


def test_range_ignored_by_server_restarts_not_append(monkeypatch, tmp_path):
    raw = road_data()
    half = len(raw) // 2
    replies = [
        _HttpReply(raw[:half], headers={
            "Content-Length": str(len(raw)), "ETag": '"version1"',
        }),
        _HttpReply(raw, status=200, headers={
            "Content-Length": str(len(raw)), "ETag": '"version2"',
        }),
    ]
    requests = _fake_transport(monkeypatch, replies)
    destination = tmp_path / "road.zip"
    official.download_original("road", destination, attempts=2)
    assert destination.read_bytes() == raw
    assert requests[1].get_header("Range") == f"bytes={half}-"


def test_without_http_validator_partial_body_is_never_resumed(monkeypatch, tmp_path):
    raw = road_data()
    half = len(raw) // 2
    replies = [
        _HttpReply(raw[:half], headers={"Content-Length": str(len(raw))}),
        _HttpReply(raw, headers={"Content-Length": str(len(raw))}),
    ]
    requests = _fake_transport(monkeypatch, replies)
    destination = tmp_path / "road.zip"
    official.download_original("road", destination, attempts=2)
    assert destination.read_bytes() == raw
    assert not requests[1].has_header("Range")


def test_mismatched_206_range_aborts_and_deletes_partial(monkeypatch, tmp_path):
    raw = road_data()
    half = len(raw) // 2
    replies = [
        _HttpReply(raw[:half], headers={
            "Content-Length": str(len(raw)), "ETag": '"version1"',
        }),
        _HttpReply(raw[half:], status=206, headers={
            "Content-Length": str(len(raw)-half),
            "Content-Range": f"bytes {half-1}-{len(raw)-2}/{len(raw)}",
        }),
    ]
    _fake_transport(monkeypatch, replies)
    path = tmp_path / "road.zip"
    with pytest.raises(ValueError, match="Unsafe HTTP 206"):
        official.download_original("road", path, attempts=2)
    assert not path.exists()
    assert not list(tmp_path.glob("*.partial"))


def test_repeated_transient_error_preserves_existing_sources_and_fails_closed(monkeypatch, tmp_path):
    import urllib.error
    _fake_transport(monkeypatch, [
        urllib.error.URLError("WinError 10060"),
        urllib.error.URLError("SSL unexpected EOF"),
    ])
    path = tmp_path / "road.zip"
    with pytest.raises(ConnectionError, match="browser download"):
        official.download_original("road", path, attempts=2, timeout=1)
    assert not path.exists()
    assert not list(tmp_path.glob("*.partial"))


def test_cli_exposes_timeouts_and_retry_limits(tmp_path):
    exe = ROOT / "scripts/acquire_accessibility_inputs.py"
    help_run = subprocess.run(
        [sys.executable, str(exe), "--help"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert help_run.returncode == 0, help_run.stderr
    for option in ("--attempts", "--timeout", "--backoff", "--strict"):
        assert option in help_run.stdout

