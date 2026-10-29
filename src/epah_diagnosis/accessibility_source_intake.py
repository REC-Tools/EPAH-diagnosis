"""Acquire and preflight original official accessibility inputs without promotion.

The 2021 ISTAT road-time matrix is shared by DEA, schools and rail. A valid
file checksum and correct archive type do not prove route completeness or
service operation. Those stronger gates live in the existing preparers.
"""
from __future__ import annotations

import csv
import hashlib
import io
import os
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass
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


def download_original(source_id: str, destination: Path, timeout: int = 180) -> dict:
    """Streaming download; enforce HTTPS and fixed source host, no overwrite."""
    spec = SOURCE_SPECS.get(source_id)
    if spec is None:
        raise ValueError(f"Unknown source: {source_id}")
    if destination.exists():
        raise FileExistsError(f"Original already exists; do not overwrite: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(spec["url"], headers={
        "User-Agent": "EPAH-diagnosis/0.1 official data QA",
        "Accept": "application/zip,text/csv,application/octet-stream,*/*",
        "Accept-Encoding": "identity",
    })
    tmp = None
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            real_url = response.geturl()
            parsed = urlsplit(real_url)
            if parsed.scheme != "https" or parsed.hostname != spec["host"]:
                raise ValueError(f"Redirect outside official provider: {real_url}")
            mime = response.headers.get("Content-Type", "unknown") if hasattr(response, "headers") else "unknown"
            fd, filename = tempfile.mkstemp(prefix=".epah-input-", suffix=".partial", dir=destination.parent)
            tmp = Path(filename)
            length = 0
            with os.fdopen(fd, "wb") as handle:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    length += len(chunk)
                    if length > spec["max_bytes"]:
                        raise ValueError(f"Official input exceeds size limit: {source_id}")
                    handle.write(chunk)
        preflight = check_original(source_id, tmp)
        if destination.exists():
            raise FileExistsError(f"Original appeared during download: {destination}")
        os.replace(tmp, destination)
        tmp = None
        return {
            **preflight,
            "original_filename": destination.name,
            "downloaded_at_utc": datetime.now(UTC).isoformat(),
            "response_url": real_url,
            "http_content_type": mime,
        }
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def inspect_local(source_id: str, path: Path) -> dict:
    item = check_original(source_id, path)
    item["local_original_path"] = str(path)
    item["provided_original_not_fetched_by_this_tool"] = True
    return item
