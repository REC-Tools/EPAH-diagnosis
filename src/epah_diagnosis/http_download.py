"""Bounded, integrity-checked HTTP retrieval for official ZIP source archives.

A truncated response never becomes an accepted data source. Resume uses HTTP
Range with Content-Range and optional If-Range validation. A server returning
200 to a ranged request triggers a fresh download, not byte concatenation.
"""
from __future__ import annotations

import http.client
import io
import logging
import re
import socket
import time
import urllib.error
import urllib.request
import zipfile


_LOG = logging.getLogger(__name__)
_CHUNK_SIZE = 256 * 1024
_MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
_CONTENT_RANGE = re.compile(r"bytes (\d+)-(\d+)/(\d+)", re.IGNORECASE)


class ArchiveDownloadError(ValueError):
    """A complete, validated official ZIP could not be retrieved."""


def validate_shapefile_zip(payload: bytes) -> None:
    """Reject truncated, non-ZIP, CRC-invalid, or non-shapefile responses."""
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            members = archive.infolist()
            if not any(member.filename.lower().endswith(".shp") for member in members):
                raise ArchiveDownloadError("Archive contains no .shp municipal boundary data")
            bad_member = archive.testzip()
            if bad_member is not None:
                raise ArchiveDownloadError(f"ZIP integrity check failed: {bad_member}")
    except (zipfile.BadZipFile, EOFError) as exc:
        raise ArchiveDownloadError("Response is not a complete, valid ZIP archive") from exc


def _content_length(headers) -> int | None:
    value = headers.get("Content-Length")
    if value is None:
        return None
    try:
        length = int(value)
    except (TypeError, ValueError) as exc:
        raise ArchiveDownloadError("Invalid HTTP Content-Length header") from exc
    if length < 0:
        raise ArchiveDownloadError("Negative HTTP Content-Length header")
    return length


def download_shapefile_zip(
    url: str,
    *,
    attempts: int = 4,
    timeout: float = 120,
    backoff_seconds: float = 1.0,
    max_archive_bytes: int = _MAX_ARCHIVE_BYTES,
) -> bytes:
    """Get an entire source ZIP, retrying interrupted transfers safely.

    The in-memory partial download is reused only inside this call; no incomplete
    archive is saved to disk. Retries use verified 206 ranges when supported.
    """
    if attempts < 1 or timeout <= 0 or backoff_seconds < 0 or max_archive_bytes < 1:
        raise ValueError("Invalid download limits")

    payload = bytearray()
    expected_total: int | None = None
    validator: str | None = None
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        offset = len(payload)
        headers = {
            "User-Agent": "Mozilla/5.0 EPAH-diagnosis/1.0",
            "Accept": "application/zip,application/octet-stream,*/*",
            "Accept-Encoding": "identity",
        }
        if offset:
            headers["Range"] = f"bytes={offset}-"
            if validator:
                headers["If-Range"] = validator
        request = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                status = getattr(response, "status", None)
                if status is None:
                    status = response.getcode()
                response_headers = response.headers
                part_size = _content_length(response_headers)

                if status == 200:
                    # Range ignored, or source changed: never append to an old copy.
                    if offset:
                        payload.clear()
                    expected_total = part_size
                    etag = response_headers.get("ETag")
                    validator = (
                        etag if etag and not etag.startswith("W/")
                        else response_headers.get("Last-Modified")
                    )
                elif status == 206:
                    match = _CONTENT_RANGE.fullmatch(
                        (response_headers.get("Content-Range") or "").strip()
                    )
                    if not offset or match is None:
                        raise ArchiveDownloadError("Unexpected HTTP partial response")
                    start, end, total = map(int, match.groups())
                    if (start != offset or end < start or end >= total or
                        (expected_total is not None and expected_total != total) or
                        (part_size is not None and part_size != end - start + 1)):
                        raise ArchiveDownloadError("Unsafe or inconsistent HTTP Content-Range")
                    expected_total = total
                    etag = response_headers.get("ETag")
                    if validator and etag and validator.startswith('"') and etag != validator:
                        raise ArchiveDownloadError("Source ETag changed during download")
                else:
                    raise ArchiveDownloadError(f"Unexpected HTTP status: {status}")

                if expected_total is not None and expected_total > max_archive_bytes:
                    raise ArchiveDownloadError("Archive exceeds configured size limit")

                received = 0
                while True:
                    try:
                        chunk = response.read(_CHUNK_SIZE)
                    except http.client.IncompleteRead as exc:
                        if exc.partial:
                            payload.extend(exc.partial)
                            received += len(exc.partial)
                        raise
                    if not chunk:
                        break
                    payload.extend(chunk)
                    received += len(chunk)
                    if len(payload) > max_archive_bytes:
                        raise ArchiveDownloadError("Archive exceeds configured size limit")

                if part_size is not None and received != part_size:
                    raise http.client.IncompleteRead(b"", part_size - received)
                if expected_total is not None and len(payload) != expected_total:
                    raise http.client.IncompleteRead(b"", expected_total - len(payload))

                try:
                    validated = bytes(payload)
                    validate_shapefile_zip(validated)
                    return validated
                except ArchiveDownloadError:
                    # Transfer may have been truncated without Content-Length.
                    # Restart rather than mix a full but invalid body with a range.
                    payload.clear()
                    expected_total = None
                    validator = None
                    raise
        except urllib.error.HTTPError as exc:
            if exc.code not in (408, 416, 429) and exc.code < 500:
                raise ArchiveDownloadError(f"HTTP {exc.code} downloading ISTAT boundaries") from exc
            if exc.code == 416:
                payload.clear()
                expected_total = None
                validator = None
            last_error = exc
        except (urllib.error.URLError, http.client.IncompleteRead,
                http.client.RemoteDisconnected, socket.timeout, TimeoutError,
                ConnectionResetError, OSError, ArchiveDownloadError) as exc:
            if isinstance(exc, ArchiveDownloadError) and (
                "exceeds configured size" in str(exc) or
                "Unsafe or inconsistent HTTP Content-Range" in str(exc) or
                "Source ETag changed" in str(exc)
            ):
                raise
            last_error = exc

        if attempt < attempts:
            _LOG.warning(
                "ISTAT boundary ZIP attempt %s/%s interrupted (%s); retrying from byte %s",
                attempt, attempts, last_error, len(payload),
            )
            time.sleep(backoff_seconds * 2 ** (attempt - 1))

    raise ArchiveDownloadError(
        f"Could not retrieve a complete ISTAT boundary ZIP after {attempts} "
        f"attempts (last error: {last_error}). Download the official ZIP "
        "with a browser and pass --source-zip PATH."
    ) from last_error
