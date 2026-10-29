"""Independent primary-source audits for 27 Canavese municipalities.

This module can read locally preserved copies of the real authoritative source
files. It does not certify provenance merely because a filename looks official
or because a URL is reachable; that requires a reviewer.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from zipfile import is_zipfile

from epah_diagnosis.altitude import ALTITUDE_XLSX_URL
from epah_diagnosis.climate import load_reference
from epah_diagnosis.climate_verification import CURRENT_ANNEX_URL
from epah_diagnosis.snai import SNAI_2020_URL
from epah_diagnosis.territorial_context_qa import prepare as prepare_territorial
from epah_diagnosis.cli import read_municipality_codes

OFFICIAL_SOURCES = {
    "mean_altitude": {
        "url": ALTITUDE_XLSX_URL,
        "filename": "istat_altimetria_comuni_2021.xlsx",
        "hostname": "www.istat.it",
        "media_type": "xlsx",
    },
    "snai_classification": {
        "url": SNAI_2020_URL,
        "filename": "snai_mappa_aree_interne_2020.xlsx",
        "hostname": "politichecoesione.governo.it",
        "media_type": "xlsx",
    },
    "heating_degree_days": {
        "url": CURRENT_ANNEX_URL,
        "filename": "dpr412_allegato_a_2016.html",
        "hostname": "def.finanze.it",
        "media_type": "html",
    },
}
SOURCE_PAGE_URLS = {
    "mean_altitude": "https://www.istat.it/classificazione/principali-statistiche-geografiche-sui-comuni/",
    "snai_classification": (
        "https://politichecoesione.governo.it/it/politica-di-coesione/"
        "strategie-tematiche-e-territoriali/strategie-territoriali/"
        "strategia-nazionale-aree-interne-snai/le-aree-interne-2021-2027/"
        "mappa-aree-interne-2020/"
    ),
    "heating_degree_days": CURRENT_ANNEX_URL,
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_snapshot(data: bytes, source_id: str, *, actual_url: str | None = None) -> dict:
    """File-integrity evidence; domain alone cannot prove authoritativeness."""
    if source_id not in OFFICIAL_SOURCES:
        raise ValueError(f"Unknown priority source: {source_id}")
    entry = OFFICIAL_SOURCES[source_id]
    if entry["media_type"] == "xlsx" and not is_zipfile(__import__("io").BytesIO(data)):
        raise ValueError(f"Source {source_id} is not an XLSX archive")
    if entry["media_type"] == "html":
        text = data[:1024].decode("utf-8", errors="ignore").lower()
        if not text.strip() or ("<html" not in text and "<!doctype" not in text):
            raise ValueError("Expected HTML of consolidated official Annex A, not another file")
    return {
        "source_id": source_id,
        "official_landing_page": SOURCE_PAGE_URLS[source_id],
        "expected_url": entry["url"],
        "actual_url": actual_url,
        "raw_sha256": sha256_bytes(data),
        "bytes": len(data),
        "source_authenticity_reviewed": False,
        "source_license_reviewed": False,
    }


def fetch_official(source_id: str, destination: Path, *, timeout: int = 90) -> dict:
    """Download only from fixed official endpoints; never overwrite local sources.

    The caller must review response URL, content and licensing; HTTPS does not
    by itself prove that the data are the right vintage or scientific source.
    """
    entry = OFFICIAL_SOURCES[source_id]
    if destination.exists():
        raise FileExistsError(f"Original source already exists: {destination}")
    request = Request(
        entry["url"], headers={
            "User-Agent": "EPAH-diagnosis/0.1 (official-source-audit)",
            "Accept": "text/html,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        final_url = response.geturl()
        parsed = urlsplit(final_url)
        if parsed.scheme != "https" or parsed.hostname != entry["hostname"]:
            raise ValueError(f"Unexpected nonofficial redirect: {final_url}")
        data = response.read(20 * 1024 * 1024 + 1)
        if len(data) > 20 * 1024 * 1024:
            raise ValueError("Source exceeds 20 MB safety limit")
    manifest = source_snapshot(data, source_id, actual_url=final_url)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as f:
        f.write(data)
    return manifest


class _TextFromHtml(HTMLParser):
    def __init__(self):
        super().__init__()
        self.fragments: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.skip += 1
        if not self.skip and tag in {"tr", "br", "p", "pre", "div", "li"}:
            self.fragments.append("\n")
        elif not self.skip and tag in {"td", "th"}:
            self.fragments.append(" ")

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.skip = max(0, self.skip - 1)
        if not self.skip and tag in {"tr", "p", "pre", "div", "li"}:
            self.fragments.append("\n")
        elif not self.skip and tag in {"td", "th"}:
            self.fragments.append(" ")

    def handle_data(self, data):
        if not self.skip:
            self.fragments.append(data)

    def text(self) -> str:
        return html.unescape("".join(self.fragments))


def _norm_name(name: str) -> str:
    from unicodedata import normalize
    name = normalize("NFKD", name)
    return re.sub(r"[^a-z0-9]", "", "".join(
        c for c in name.lower() if not __import__("unicodedata").combining(c)
    ))


# Each published row is normally "TO F 3270 611 PRATIGLIONE".
OFFICIAL_ROW = re.compile(
    r"^\s*TO\s+([ABCDEF])\s+(\d{3,5})\s+(\d{1,4})\s+(.+?)\s*$",
    re.IGNORECASE,
)


def _decode_html(data: bytes) -> str:
    for codec in ("utf-8-sig", "iso-8859-1"):
        try:
            return data.decode(codec)
        except UnicodeDecodeError:
            continue
    raise ValueError("Cannot decode annex source")


def compare_current_annex(
    original_html: bytes,
    snapshot_path: Path,
    registry_path: Path,
) -> dict:
    """Check *all* 27 numeric GG, zone and ancillary seat-altitude readings.

    Requires saved official full-page HTML, not search-result snippets.
    The full page has to identify the edition in force since 9 Aug 2016.
    """
    html_content = _decode_html(original_html)
    parser = _TextFromHtml()
    parser.feed(html_content)
    text = parser.text()
    collapsed = re.sub(r"\s+", " ", text)
    if not re.search(r"\b09\s*/\s*08\s*/\s*2016\b", collapsed):
        raise ValueError("Current consolidated Annex A version date 09/08/2016 not found")
    if "ALLEGATO A" not in collapsed.upper():
        raise ValueError("Official Allegato A title not found")

    readings = {}
    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line.strip())
        match = OFFICIAL_ROW.fullmatch(line)
        if not match:
            continue
        zone, gg, elevation, name = match.groups()
        name = name.strip().strip(".,;:")
        key = _norm_name(name)
        if key in readings:
            raise ValueError(f"Duplicated municipal table row in legal annex: {name}")
        readings[key] = {
            "name": name, "climate_zone": zone.upper(),
            "heating_degree_days": int(gg),
            "municipal_seat_altitude_m": int(elevation),
        }
    registry = read_municipality_codes(registry_path)
    actual = load_reference(snapshot_path)
    if len(registry) != 27 or len(actual) != 27:
        raise ValueError("Expected exactly 27 municipalities in baseline")
    expected = {_norm_name(name) for name in registry}
    if {_norm_name(item.municipality) for item in actual} != expected:
        raise ValueError("Local climate snapshot and municipality registry differ")
    missing = sorted(name for name in registry if _norm_name(name) not in readings)
    differences = []
    verified_rows = []
    for item in sorted(actual, key=lambda r: r.municipality):
        original = readings.get(_norm_name(item.municipality))
        if original is None:
            continue
        changed = {}
        for key in ("climate_zone", "heating_degree_days", "municipal_seat_altitude_m"):
            value = getattr(item, key)
            if value != original[key]:
                changed[key] = {"snapshot": value, "consolidated_annex": original[key]}
        if changed:
            differences.append({"municipality": item.municipality, "fields": changed})
        verified_rows.append({
            "municipality": item.municipality, "official_name": original["name"],
            "climate_zone": original["climate_zone"],
            "heating_degree_days": original["heating_degree_days"],
            "municipal_seat_altitude_m": original["municipal_seat_altitude_m"],
        })

    complete = len(verified_rows) == 27 and not missing
    return {
        "indicator_id": "heating_degree_days",
        "source_url": CURRENT_ANNEX_URL,
        "official_edition": "in vigore dal 09/08/2016",
        "official_file_sha256": sha256_bytes(original_html),
        "snapshot_sha256": sha256_bytes(snapshot_path.read_bytes()),
        "municipality_registry_sha256": sha256_bytes(registry_path.read_bytes()),
        "rows_examined": len(verified_rows),
        "missing_municipalities": missing,
        "differences": differences,
        "official_readings": verified_rows,
        "technical_crosscheck_passed": complete and not differences,
        "qa_status": "technical_checks_only" if complete and not differences else "blocked",
        "human_source_reviewed": False,
        "validated_for_release": False,
        "notes": (
            "Full original HTML required; downloaded/saved page still needs "
            "human confirmation of the official edition and source licensing."
        ),
    }


def audit_workbook(
    indicator: str, path: Path, municipality_registry: Path,
) -> tuple[list[dict], list[dict], dict]:
    if indicator not in {"mean_altitude", "snai_classification"}:
        raise ValueError("Expected altitude or SNAI workbook")
    data = path.read_bytes()
    snapshot = source_snapshot(data, indicator)
    rows, summary, report = prepare_territorial(indicator, data, municipality_registry)
    report["official_landing_page"] = snapshot["official_landing_page"]
    report["raw_source_file"] = path.name
    report["source_authenticity_reviewed"] = False
    report["validated_for_release"] = False
    return rows, summary, report
