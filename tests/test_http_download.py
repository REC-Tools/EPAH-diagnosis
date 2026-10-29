"""Offline, synthetic HTTP transfer tests: no institutional data used."""
from __future__ import annotations

import io
import zipfile

import pytest

from epah_diagnosis import http_download


def fake_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zip_file:
        zip_file.writestr("Com01012026_g_WGS84.shp", b"synthetic shapefile payload " * 25000)
        zip_file.writestr("Com01012026_g_WGS84.dbf", b"other metadata")
    return buf.getvalue()


class Reply:
    def __init__(self, body: bytes, *, status: int = 200, headers: dict | None = None):
        self.status = status
        self.headers = headers or {}
        self._body = io.BytesIO(body)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self, size: int) -> bytes:
        return self._body.read(size)


def run_with_replies(monkeypatch, replies, **kw):
    requests = []
    replies = iter(replies)

    def fake_urlopen(req, timeout):
        requests.append(req)
        return next(replies)

    monkeypatch.setattr(http_download.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(http_download.time, "sleep", lambda _: None)
    result = http_download.download_shapefile_zip(
        "https://example.org/official-shapes.zip", **kw
    )
    return result, requests


def test_success_with_complete_zip(monkeypatch):
    raw = fake_zip()
    out, reqs = run_with_replies(
        monkeypatch, [Reply(raw, headers={"Content-Length": str(len(raw))})]
    )
    assert out == raw
    assert len(reqs) == 1
    assert reqs[0].get_header("Accept-encoding") == "identity"


def test_interrupted_transfer_recovers_using_range(monkeypatch):
    raw = fake_zip()
    split = len(raw) * 3 // 4
    first = Reply(raw[:split], headers={"Content-Length": str(len(raw)), "ETag": '"original"'})
    second = Reply(raw[split:], status=206, headers={
        "Content-Length": str(len(raw) - split),
        "Content-Range": f"bytes {split}-{len(raw)-1}/{len(raw)}",
        "ETag": '"original"',
    })
    out, reqs = run_with_replies(monkeypatch, [first, second])
    assert out == raw
    assert reqs[1].get_header("Range") == f"bytes={split}-"
    assert reqs[1].get_header("If-range") == '"original"'


def test_ignored_range_200_restarts_without_appending(monkeypatch):
    raw = fake_zip()
    split = len(raw) // 2
    out, reqs = run_with_replies(monkeypatch, [
        Reply(raw[:split], headers={"Content-Length": str(len(raw))}),
        Reply(raw, headers={"Content-Length": str(len(raw))}),
    ])
    assert out == raw
    assert len(reqs) == 2


def test_range_from_wrong_start_rejected(monkeypatch):
    raw = fake_zip()
    split = len(raw) // 2
    with pytest.raises(http_download.ArchiveDownloadError, match="Unsafe or inconsistent HTTP Content-Range"):
        run_with_replies(monkeypatch, [
            Reply(raw[:split], headers={"Content-Length": str(len(raw))}),
            Reply(raw[split:], status=206, headers={
                "Content-Length": str(len(raw) - split),
                "Content-Range": f"bytes {split-1}-{len(raw)-2}/{len(raw)}",
            }),
        ])


def test_never_accepts_truncated_zip(monkeypatch):
    raw = fake_zip()
    split = len(raw) // 2
    with pytest.raises(http_download.ArchiveDownloadError, match="after 2 attempts"):
        run_with_replies(monkeypatch, [
            Reply(raw[:split], headers={"Content-Length": str(len(raw))}),
            Reply(raw[:split], headers={"Content-Length": str(len(raw))}),
        ], attempts=2)


def test_rejects_portal_html_even_if_http_200(monkeypatch):
    html = b"<html>Too many requests</html>"
    with pytest.raises(http_download.ArchiveDownloadError, match="after 2 attempts"):
        run_with_replies(monkeypatch, [Reply(html), Reply(html)], attempts=2)


def test_rejects_invalid_zip_crc():
    raw = bytearray(fake_zip())
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        entry = z.infolist()[0]
        at = entry.header_offset + 30 + len(entry.filename.encode()) + len(entry.extra)
    raw[at + 30] ^= 1
    with pytest.raises(http_download.ArchiveDownloadError, match="integrity check"):
        http_download.validate_shapefile_zip(bytes(raw))


def test_http_client_incomplete_read_exception_is_resumed(monkeypatch):
    """The exact exception seen on Windows must not lose partial bytes."""
    import http.client

    raw = fake_zip()
    split = len(raw) // 3

    class InterruptedReply(Reply):
        def read(self, size: int) -> bytes:
            raise http.client.IncompleteRead(raw[:split], len(raw) - split)

    out, reqs = run_with_replies(monkeypatch, [
        InterruptedReply(b"", headers={"Content-Length": str(len(raw))}),
        Reply(raw[split:], status=206, headers={
            "Content-Length": str(len(raw) - split),
            "Content-Range": f"bytes {split}-{len(raw)-1}/{len(raw)}",
        }),
    ])
    assert out == raw
    assert reqs[1].get_header("Range") == f"bytes={split}-"
