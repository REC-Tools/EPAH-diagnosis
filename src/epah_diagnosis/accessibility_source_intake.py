"""Acquire and preflight original official accessibility inputs without promotion.

The 2021 ISTAT road-time matrix is shared by DEA, schools and rail. A valid
file checksum and correct archive type do not prove route completeness or
service operation. Those stronger gates live in the existing preparers.
"""
from __future__ import annotations

import csv
import hashlib
import http.client
import io
import os
import re
import socket
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

from epah_diagnosis.education_access import SCHOOL_REGISTRY_URL, SECONDARY_PATHWAYS_URL
from epah_diagnosis.geography import BOUNDARIES_2026_URL
from epah_diagnosis.service_access import PIEMONTE_DISTANCE_MATRIX_URL

# Source editions are intentionally distinct. Do not silently upgrade just
# the school registry to 2026/27 while using 2024/25 pathways.
SOURCE_SPECS = {
    "road": {
        "url": PIEMONTE_DISTANCE_MATRIX_URL,
        "file": "Piemonte.zip",
        "host": "www.istat.it",
        "vintage": "2021 municipality geography; 2020 road graph",
        "max_bytes": 2_500_000_000,
    },
    "boundaries": {
        "url": BOUNDARIES_2026_URL,
        "file": "Limiti01012026_g.zip",
        "host": "www.istat.it",
        "vintage": "2026 municipality boundaries",
        "max_bytes": 400_000_000,
    },
    "school_registry": {
        "url": SCHOOL_REGISTRY_URL,
        "file": "SCUANAGRAFESTAT20242520250831.csv",
        "host": "dati.istruzione.it",
        "vintage": "2024/25, data 31 Aug 2025",
        "max_bytes": 80_000_000,
    },
    "school_pathways": {
        "url": SECONDARY_PATHWAYS_URL,
        "file": "ALUSECGRADOINDSTA20242520250831.csv",
        "host": "dati.istruzione.it",
        "vintage": "2024/25, data 31 Aug 2025",
        "max_bytes": 80_000_000,
    },
}
HEALTH_PAGE = "https://www.salute.gov.it/new/it/banche-dati/elenco-strutture-della-rete-dellemergenza-ospedaliera/"
ROAD_PAGE = "https://www.istat.it/notizia/matrici-di-contiguita-distanza-e-pendolarismo/"
SCHOOL_REGISTRY_PAGE = "https://dati.istruzione.it/opendata/ricerca/?searchinput=SCUANAGRAFESTAT"
SCHOOL_PATHWAYS_PAGE = "https://dati.istruzione.it/opendata/opendata/catalog/ALUSECGRADOINDSTA"


def sha256_file(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def _header(handle) -> list[str]:
    sample = handle.read(20000)
    text = sample.decode("utf-8-sig", errors="replace")
    try:
        delimiter = csv.Sniffer().sniff(text[:4096], delimiters=";,\t|").delimiter
    except csv.Error:
        delimiter = ";" if text.count(";") > text.count(",") else ","
    row = next(csv.reader(io.StringIO(text), delimiter=delimiter), [])
    return [x.strip().upper() for x in row]


def check_original(source_id: str, path: Path) -> dict:
    """Fast, conservative format + schema preflight; no source approval."""
    if source_id not in SOURCE_SPECS:
        raise ValueError(f"Unknown source: {source_id}")
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"Missing/empty original input: {path}")
    if path.stat().st_size > SOURCE_SPECS[source_id]["max_bytes"]:
        raise ValueError("Official input exceeds configured size cap")
    observation = {"source_id": source_id, "bytes": path.stat().st_size}
    if source_id in {"road", "boundaries"}:
        if not zipfile.is_zipfile(path):
            raise ValueError(f"{source_id} expected ZIP, not HTML/portal error")
        with zipfile.ZipFile(path) as archive:
            members = archive.namelist()
            if source_id == "road":
                csvs = [n for n in members if n.lower().endswith(".csv")]
                if not csvs:
                    raise ValueError("ISTAT Piemonte ZIP has no regional distance CSVs")
                accepted = None
                for name in csvs[:20]:
                    with archive.open(name) as file:
                        columns = set(_header(file))
                    if {"OR_PROCOM", "DEST_PROCOM", "TEP_TOT"} <= columns:
                        accepted = name
                        break
                if accepted is None:
                    raise ValueError("No ISTAT road CSV with OR_PROCOM / DEST_PROCOM / TEP_TOT")
                observation.update({"csv_members": len(csvs), "sample_member": accepted})
            else:
                candidates = [name for name in members
                              if Path(name).name.lower().startswith("com")
                              and name.lower().endswith(".shp")]
                if not candidates:
                    raise ValueError("ISTAT boundaries ZIP missing municipality .shp")
                stem = candidates[0].rsplit(".", 1)[0].lower()
                endings = {name.rsplit(".", 1)[-1].lower()
                           for name in members if name.rsplit(".", 1)[0].lower() == stem}
                if not {"shp", "dbf", "shx"} <= endings:
                    raise ValueError("ISTAT boundary shapefile is missing DBF/SHX companions")
                observation.update({"municipality_shapefile": candidates[0]})
        observation["format"] = "zip"
    else:
        with path.open("rb") as handle:
            prefix = handle.read(256)
        if prefix.lstrip().lower().startswith((b"<!doctype", b"<html")):
            raise ValueError("MIM download returned HTML instead of CSV")
        with path.open("rb") as handle:
            columns = set(_header(handle))
        if source_id == "school_registry":
            required = {"CODICESCUOLA", "CODICEISTITUTO", "CODICEMECCANOGRAFICO"}
            if not (columns & required):
                raise ValueError("School registry CSV missing school code column")
        else:
            if not (columns & {"CODICESCUOLA", "CODICEISTITUTO", "CODICEMECCANOGRAFICO"}):
                raise ValueError("MIM pathways CSV missing school code")
            if not (columns & {"TIPOPERCORSO", "TIPOLOGIAPERCORSO", "TIPOISTITUTO"}):
                raise ValueError("MIM pathways CSV missing pathway type")
        observation.update({"format": "csv", "header_columns": len(columns)})
    observation.update({
        "sha256": sha256_file(path),
        "original_filename": path.name,
        "source_url": SOURCE_SPECS[source_id]["url"],
        "vintage": SOURCE_SPECS[source_id]["vintage"],
        "technical_preflight_passed": True,
        "data_values_validated": False,
        "source_authenticity_reviewed": False,
        "human_approval": False,
    })
    return observation



_CONTENT_RANGE = re.compile(r"bytes (\d+)-(\d+)/(\d+)", flags=re.IGNORECASE)


def _http_length(headers) -> int | None:
    raw = headers.get("Content-Length")
    if raw is None:
        return None
    try:
        length = int(raw)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid official HTTP Content-Length: {raw!r}") from exc
    if length < 0:
        raise ValueError("Negative official HTTP Content-Length")
    return length


def _stream_retrying(
    source_id: str, partial: Path, *, attempts: int, timeout: float,
    backoff: float,
) -> tuple[str, str, int]:
    """Retry connect/SSL EOF and resume only with a real HTTP validator.

    A ranged reply must be HTTP 206 and cover *exactly* the previous bytes;
    when a server ignores Range, restart from zero. No insecure HTTP or
    certificate-verification exceptions are ever introduced.
    """
    if not 1 <= attempts <= 6 or timeout <= 0 or backoff < 0:
        raise ValueError("Expected attempts 1..6, positive timeout, nonnegative backoff")
    spec = SOURCE_SPECS[source_id]
    validator: str | None = None
    expected_total: int | None = None
    last_error: Exception | None = None
    result_url = spec["url"]
    mime = "unknown"
    for attempt in range(1, attempts + 1):
        current_bytes = partial.stat().st_size
        # Without a strong ETag or Last-Modified, resuming the same dataset
        # is unsafe: a new response might contain different source bytes.
        resume = bool(current_bytes and validator)
        if not resume and current_bytes:
            with partial.open("wb"):
                pass
            current_bytes = 0
            expected_total = None
        headers = {
            "User-Agent": "Mozilla/5.0 EPAH-diagnosis/1.0",
            "Accept": "application/zip,text/csv,application/octet-stream,*/*",
            "Accept-Encoding": "identity",
        }
        if resume:
            headers["Range"] = f"bytes={current_bytes}-"
            headers["If-Range"] = validator
        request = urllib.request.Request(spec["url"], headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                result_url = response.geturl()
                parsed = urlsplit(result_url)
                if parsed.scheme != "https" or parsed.hostname != spec["host"]:
                    raise ValueError(f"Redirect outside official provider: {result_url}")
                status = getattr(response, "status", None) or 200
                response_headers = getattr(response, "headers", {})
                mime = response_headers.get("Content-Type", "unknown")
                if response_headers.get("Content-Encoding", "identity").lower() != "identity":
                    raise ValueError("Unexpected compressed HTTP transfer; expected identity")
                part_length = _http_length(response_headers)
                if status == 200:
                    if resume:
                        # Range not honoured: do not append a second full body.
                        with partial.open("wb"):
                            pass
                        current_bytes = 0
                    expected_total = part_length
                    etag = response_headers.get("ETag")
                    validator = (etag if etag and not etag.startswith("W/")
                                 else response_headers.get("Last-Modified"))
                elif status == 206 and resume:
                    interval = _CONTENT_RANGE.fullmatch(
                        str(response_headers.get("Content-Range", "")).strip()
                    )
                    if interval is None:
                        raise ValueError("HTTP 206 missing valid Content-Range")
                    start, end, total = map(int, interval.groups())
                    if (start != current_bytes or end < start or end >= total or
                        (expected_total is not None and total != expected_total) or
                        (part_length is not None and part_length != end - start + 1)):
                        raise ValueError("Unsafe HTTP 206 Content-Range; refusing mixed originals")
                    expected_total = total
                    if validator.startswith('"'):
                        new_etag = response_headers.get("ETag")
                        if new_etag and new_etag != validator:
                            raise ValueError("Official ETag changed during ZIP resume")
                else:
                    raise ValueError(f"Unexpected official HTTP status: {status}")
                if expected_total is not None and expected_total > spec["max_bytes"]:
                    raise ValueError("Reported official source is larger than size cap")
                received = 0
                with partial.open("ab") as handle:
                    while True:
                        try:
                            chunk = response.read(256 * 1024)
                        except http.client.IncompleteRead as exc:
                            if exc.partial:
                                received += len(exc.partial)
                                handle.write(exc.partial)
                            raise
                        if not chunk:
                            break
                        received += len(chunk)
                        if handle.tell() + len(chunk) > spec["max_bytes"]:
                            raise ValueError("Official download exceeds configured size cap")
                        handle.write(chunk)
                if part_length is not None and received != part_length:
                    raise http.client.IncompleteRead(b"", part_length - received)
                saved = partial.stat().st_size
                if expected_total is not None and saved != expected_total:
                    raise http.client.IncompleteRead(b"", expected_total - saved)
                return result_url, mime, attempt
        except urllib.error.HTTPError as exc:
            if exc.code not in (408, 416, 429) and exc.code < 500:
                raise ValueError(f"Official host returned HTTP {exc.code}") from exc
            if exc.code == 416:
                validator = None
                expected_total = None
            last_error = exc
        except (urllib.error.URLError, http.client.IncompleteRead,
                http.client.RemoteDisconnected, socket.timeout,
                TimeoutError, ConnectionResetError, ConnectionAbortedError, OSError) as exc:
            # URLError(SSL: UNEXPECTED_EOF...), WinError 10060 and network
            # timeouts are transport failures, not errors in municipal data.
            last_error = exc
        if attempt < attempts:
            time.sleep(backoff * 2 ** (attempt - 1))
    raise ConnectionError(
        f"{source_id}: official HTTPS download failed after {attempts} attempt(s) "
        f"(last error: {last_error}). Use the official ISTAT browser download "
        "and --road-zip/--boundaries-zip with a NEW --out-dir. "
        "Do not disable SSL verification."
    ) from last_error


def download_original(
    source_id: str, destination: Path, timeout: float = 45,
    *, attempts: int = 3, backoff: float = 1.0,
) -> dict:
    """Resilient official HTTPS transfer; original is saved only after QA.

    Interrupted bytes are held in a temporary file and deleted on total
    failure. A complete response is always rechecked via check_original.
    """
    if source_id not in SOURCE_SPECS:
        raise ValueError(f"Unknown source: {source_id}")
    if destination.exists():
        raise FileExistsError(f"Original already exists; do not overwrite: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, filename = tempfile.mkstemp(
        prefix=".epah-input-", suffix=".partial", dir=destination.parent,
    )
    os.close(fd)
    tmp = Path(filename)
    try:
        url, content_type, tries = _stream_retrying(
            source_id, tmp, attempts=attempts, timeout=timeout, backoff=backoff,
        )
        preflight = check_original(source_id, tmp)
        if destination.exists():
            raise FileExistsError(f"Original appeared during download: {destination}")
        os.replace(tmp, destination)
        return {
            **preflight,
            "original_filename": destination.name,
            "downloaded_at_utc": datetime.now(UTC).isoformat(),
            "response_url": url,
            "http_content_type": content_type,
            "network_attempts": tries,
        }
    finally:
        tmp.unlink(missing_ok=True)


def inspect_local(source_id: str, path: Path) -> dict:
    item = check_original(source_id, path)
    item["local_original_path"] = str(path)
    item["provided_original_not_fetched_by_this_tool"] = True
    return item
