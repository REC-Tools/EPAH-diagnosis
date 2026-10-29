"""Independent primary-source audits for 27 Canavese municipalities.

This module can read locally preserved copies of the real authoritative source
files. It does not certify provenance merely because a filename looks official
or because a URL is reachable; that requires a reviewer.
"""
from __future__ import annotations

import hashlib
import html
from io import BytesIO
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

# Printable authoritative 2016 Annex A (separate endpoint from the JS detail view).
# The original detail URL can return a HTML shell with zero legal table rows.
OFFICIAL_PRINT_ANNEX_URL = "https://def.finanze.it/DocTribFrontend/executePrintArticolo.do?articolo=Allegato+A&codiceOrdinamento=60A+++++0000000&id=%7B0E4DC3BD-3B00-45E2-9CA6-B4DECB631C36%7D"

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
        "url": OFFICIAL_PRINT_ANNEX_URL,
        "filename": "dpr412_allegato_a_2016.source",
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
    detected = None
    if entry["media_type"] == "html":
        visible_text, original_markup, detected = _extract_legal_text(data)
        if "ALLEGATO A" not in visible_text.upper():
            raise ValueError(f"Printable official source has no Allegato A title (format={detected})")
        rows = sum(
            bool(OFFICIAL_ROW.fullmatch(re.sub(r"\s+", " ", line.strip())))
            for line in visible_text.splitlines()
        )
        if rows < 27:
            raise ValueError(
                f"Official print response has only {rows} TO table rows "
                f"(format={detected}). Expected at least 27; do not use "
                "a navigation shell, access-denied page, or unrelated PDF."
            )
    return {
        "source_id": source_id,
        "official_landing_page": SOURCE_PAGE_URLS[source_id],
        "expected_url": entry["url"],
        "actual_url": actual_url,
        "raw_sha256": sha256_bytes(data),
        "bytes": len(data),
        "detected_format": detected if entry["media_type"] == "html" else "xlsx",
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
        status = getattr(response, "status", None)
        mime = response.headers.get("Content-Type", "unknown") if hasattr(response, "headers") else "unknown"
        data = response.read(20 * 1024 * 1024 + 1)
        if len(data) > 20 * 1024 * 1024:
            raise ValueError("Source exceeds 20 MB safety limit")
    # The official print endpoint may serve PDF, HTML or plain text.
    # A response MIME type is not evidence that the legal table exists.
    try:
        manifest = source_snapshot(data, source_id, actual_url=final_url)
    except ValueError as exc:
        raise ValueError(
            f"Official source unusable (HTTP={status}, MIME={mime!r}, "
            f"bytes={len(data)}, first_bytes_hex={data[:16].hex()}): {exc}"
        ) from exc
    manifest["http_status"] = status
    manifest["http_content_type"] = mime
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
    # Generic textual download: the official print endpoint may emit text/plain.
    for codec in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(codec)
        except UnicodeDecodeError:
            continue
    raise ValueError("Cannot decode legal text source")


def _extract_legal_text(data: bytes) -> tuple[str, str, str]:
    """Return visible legal text, metadata source and detected original format.

    PDF extraction uses the real PDF text layer, never OCR. A scanned or
    password-protected PDF fails closed instead of inventing observations.
    """
    if data.startswith(b"%PDF-"):
        from pypdf import PdfReader
        try:
            reader = PdfReader(BytesIO(data), strict=False)
            if len(reader.pages) == 0 or len(reader.pages) > 600:
                raise ValueError(f"Unexpected official PDF page count: {len(reader.pages)}")
            if reader.is_encrypted:
                raise ValueError("Official PDF is encrypted and not text-extractable")
            extracted = []
            for page in reader.pages:
                text = page.extract_text(extraction_mode="layout")
                extracted.append(text or "")
            text = "\n".join(extracted)
        except Exception as exc:
            raise ValueError(f"Cannot extract original PDF text layer: {exc}") from exc
        if not text.strip():
            raise ValueError("PDF contains no selectable legal text; OCR not performed")
        return text, text, "pdf"
    if not data or b"\x00" in data[:4096]:
        raise ValueError(
            f"Official source body is empty or binary and not PDF "
            f"(bytes={len(data)}, prefix={data[:16].hex()})"
        )
    decoded = _decode_html(data)
    if decoded.lstrip().startswith(("<!DOCTYPE", "<!doctype", "<html", "<HTML")):
        parser = _TextFromHtml()
        parser.feed(decoded)
        return parser.text(), decoded, "html"
    if decoded.lstrip().startswith("<") and "html" in decoded[:4096].lower():
        parser = _TextFromHtml()
        parser.feed(decoded)
        return parser.text(), decoded, "html"
    if decoded.lstrip().startswith("<"):
        raise ValueError("Unsupported XML/HTML response without extractable legal text")
    if not decoded.strip():
        raise ValueError("Empty textual response")
    return decoded, decoded, "plain_text"


_OFFICIAL_EDITION_DATE = re.compile(
    r"(?<!\d)(?:0?9\s*[/.\-]\s*0?8\s*[/.\-]\s*2016"
    r"|2016\s*[/.\-]\s*0?8\s*[/.\-]\s*0?9"
    r"|0?9\s+agosto\s+2016)(?!\d)",
    re.IGNORECASE,
)
_VALID_EDITION_LABEL = re.compile(
    r"(?:in\s+vigore\s+dal|testo\s+vigente\s+dal|"
    r"decorrenza\s+dal|vigente\s+dal)",
    re.IGNORECASE,
)


def _find_official_edition_date(visible_text: str, html_source: str) -> str | None:
    """Find clearly labelled effective-date metadata in text or HTML.

    A standalone date is insufficient; this does not create human approval.
    """
    for location, source in (
        ("visible_text", visible_text),
        ("html_source", html.unescape(html_source)),
    ):
        collapsed = re.sub(r"\s+", " ", source)
        for match in _OFFICIAL_EDITION_DATE.finditer(collapsed):
            preceding = collapsed[max(0, match.start() - 240):match.start()]
            preceding = re.sub(r"<[^>]+>", " ", preceding)
            if _VALID_EDITION_LABEL.search(preceding):
                return location
    return None


def compare_current_annex(
    original_html: bytes,
    snapshot_path: Path,
    registry_path: Path,
) -> dict:
    """Check *all* 27 numeric GG, zone and ancillary seat-altitude readings.

    Requires saved official full-page HTML, not search-result snippets.
    The full page has to identify the edition in force since 9 Aug 2016.
    """
    text, source_text, source_format = _extract_legal_text(original_html)
    collapsed = re.sub(r"\s+", " ", text)
    edition_marker_location = _find_official_edition_date(collapsed, source_text)
    annex_title_present = "ALLEGATO A" in collapsed.upper()
    # Compare the data even if the downloaded HTML lacks legal edition
    # metadata. Do not approve the data without that metadata.

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
    values_match = complete and not differences
    publication_check = bool(values_match and edition_marker_location and annex_title_present)
    if not annex_title_present:
        reason = "official_annex_title_missing"
    elif not complete:
        reason = "incomplete_official_table"
    elif differences:
        reason = "source_values_disagree"
    elif not edition_marker_location:
        reason = "legal_edition_metadata_missing"
    else:
        reason = None
    return {
        "indicator_id": "heating_degree_days",
        "source_url": CURRENT_ANNEX_URL,
        "official_edition_expected": "in vigore dal 09/08/2016",
        "edition_marker_present": bool(edition_marker_location),
        "edition_marker_location": edition_marker_location,
        "annex_title_present": annex_title_present,
        "source_to_table_rows_parsed": len(readings),
        "values_match_on_27_municipalities": bool(values_match),
        "blocking_reason": reason,
        "official_file_sha256": sha256_bytes(original_html),
        "official_source_format": source_format,
        "snapshot_sha256": sha256_bytes(snapshot_path.read_bytes()),
        "municipality_registry_sha256": sha256_bytes(registry_path.read_bytes()),
        "rows_examined": len(verified_rows),
        "missing_municipalities": missing,
        "differences": differences,
        "official_readings": verified_rows,
        "technical_crosscheck_passed": publication_check,
        "qa_status": "technical_checks_only" if publication_check else "blocked",
        "human_source_reviewed": False,
        "validated_for_release": False,
        "notes": (
            "Original HTML and explicit legal-edition metadata required. "
            "If the returned page omits its effective date, numeric matches "
            "are recorded but the technical gate remains blocked until the "
            "edition is established from an authoritative source. "
            "Human confirmation of source and licensing is still mandatory."
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
