"""Independent 2011 ISTAT CPA source validation and safe, replayable acquisition.

This module intentionally does *not* modify the verification matrix.
The existing prepare_building_stock.py computes aggregate values; this module
independently rereads raw Piemonte census sections to check 27 numerators and
denominators against those draft values. It cannot authenticate reviewers.
"""
from __future__ import annotations

import csv
import hashlib
import io
import os
import re
import tempfile
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

from epah_diagnosis.cli import read_municipality_codes
from epah_diagnosis.istat_building_stock import CPA_2011_URL

OFFICIAL_LANDING_PAGE = "https://www.istat.it/notizia/basi-territoriali-e-variabili-censuarie/"
PRE_1981_FIELDS = ("E8", "E9", "E10", "E11", "E12")
LATER_FIELDS = ("E13", "E14", "E15", "E16")
EPOCH_FIELDS = PRE_1981_FIELDS + LATER_FIELDS
MAX_SOURCE_BYTES = 900 * 1024 * 1024
MAX_UNCOMPRESSED_CSV_BYTES = 3 * 1024 * 1024 * 1024


def _hash_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _source_names(archive: zipfile.ZipFile) -> list[str]:
    names = [
        info.filename for info in archive.infolist()
        if info.filename.lower().endswith(".csv")
        and "indicatori_2011_sezioni" in info.filename.lower()
    ]
    if not names:
        raise ValueError("No 2011 section CSVs in the official ZIP")
    if len(names) != len(set(names)) or any(
        info.file_size > MAX_UNCOMPRESSED_CSV_BYTES
        for info in archive.infolist() if info.filename in names
    ):
        raise ValueError("Duplicate or implausibly large section CSV in ZIP")
    return names


def _piemonte_section(archive: zipfile.ZipFile) -> str:
    names = [
        name for name in _source_names(archive)
        if re.search(r"(?:^|/)R01_indicatori_2011_sezioni\.csv$", name, re.IGNORECASE)
    ]
    if len(names) != 1:
        raise ValueError(
            f"Expected exactly one Piemonte R01_indicatori_2011_sezioni.csv, got {len(names)}"
        )
    return names[0]


def _decode_italian_csv(data: bytes) -> str:
    for codec in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(codec)
        except UnicodeDecodeError:
            continue
    raise ValueError("Unable to decode official R01 section CSV")


def _clean_code(value: object) -> str | None:
    code = str(value or "").strip()
    if code.endswith(".0"):
        code = code[:-2]
    if not re.fullmatch(r"\d{1,6}", code):
        return None
    return code.zfill(6)


def _count(value: object, *, municipality: str, field: str) -> int:
    """Do not turn missing, suppressed, or malformed census counts into zero."""
    raw = str(value if value is not None else "").strip()
    if re.fullmatch(r"\d+", raw):
        return int(raw)
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", raw):
        return int(raw.replace(".", ""))
    raise ValueError(
        f"Missing/suppressed/noninteger official {field} count for {municipality}: {raw!r}"
    )


def independent_r01_counts(original: bytes, registry: Path) -> tuple[list[dict], dict]:
    """Independently aggregate raw 2011 ISTAT R01 section rows for 27 codes.

    Does not invoke istat_building_stock.parse_cpa_zip or building_stock_qa.prepare:
    this provides a second arithmetic path to catch extraction/schema mistakes.
    """
    wanted = read_municipality_codes(registry)
    if len(wanted) != 27 or len(set(wanted.values())) != 27:
        raise ValueError("27 unique canonical municipality codes required")
    reverse = {code: name for name, code in wanted.items()}
    with zipfile.ZipFile(io.BytesIO(original)) as archive:
        name = _piemonte_section(archive)
        raw = archive.read(name)
    source = io.StringIO(_decode_italian_csv(raw), newline="")
    sample = source.read(12000)
    source.seek(0)
    dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
    reader = csv.DictReader(source, dialect=dialect)
    columns = {
        re.sub(r"\s+", "", str(name or "")).upper(): name
        for name in (reader.fieldnames or [])
    }
    code_field = next((columns[v] for v in
                       ("PROCOM", "PRO_COM", "PRO_COM_T", "COD_COM", "CODCOM", "CODICE_COMUNE")
                       if v in columns), None)
    missing = [field for field in ("E3", *EPOCH_FIELDS) if field not in columns]
    if code_field is None or missing:
        raise ValueError(
            "Piemonte 2011 CSV missing canonical municipality code or E3/E8-E16: "
            + ", ".join(missing)
        )
    totals = {code: {f: 0 for f in ("E3", *EPOCH_FIELDS)} for code in reverse}
    section_counts = {code: 0 for code in reverse}
    seen = 0
    for raw_row in reader:
        code = _clean_code(raw_row.get(code_field))
        if code not in reverse:
            continue
        seen += 1
        municipality = reverse[code]
        section_counts[code] += 1
        for key in totals[code]:
            totals[code][key] += _count(
                raw_row.get(columns[key]), municipality=municipality, field=key,
            )
    results = []
    for municipality, code in wanted.items():
        values = totals[code]
        if section_counts[code] == 0:
            raise ValueError(f"No raw Piemonte section rows found for {municipality} ({code})")
        total = values["E3"]
        before = sum(values[key] for key in PRE_1981_FIELDS)
        epoch_total = sum(values[key] for key in EPOCH_FIELDS)
        if total <= 0 or before > total or epoch_total > total:
            raise ValueError(
                f"Inconsistent E3 / E8-E16 counts for {municipality}: "
                f"total={total}, before={before}, sum_epochs={epoch_total}"
            )
        results.append({
            "municipality": municipality,
            "municipality_code": code,
            "section_count": section_counts[code],
            "residential_buildings_total": total,
            "buildings_pre_1981": before,
            "share_pre_1981_pct": f"{before / total * 100:.2f}",
            "year": "2011",
            **{key: values[key] for key in ("E3", *EPOCH_FIELDS)},
        })
    summary = {
        "raw_member": name,
        "selected_sections": seen,
        "target_count": len(results),
        "municipality_codes": sorted(reverse),
        "unweighted_mean_pct": round(
            sum(float(row["share_pre_1981_pct"]) for row in results) / len(results), 2
        ),
        "green_community_weighted_pct": round(
            sum(r["buildings_pre_1981"] for r in results)
            / sum(r["residential_buildings_total"] for r in results) * 100, 2
        ),
    }
    return results, summary


def verify_draft_independently(
    original: bytes, registry: Path, draft_rows: list[dict], benchmarks: list[dict],
) -> dict:
    independently, raw = independent_r01_counts(original, registry)
    indexed = {row["municipality_code"]: row for row in draft_rows}
    if len(indexed) != 27 or len(draft_rows) != 27:
        raise ValueError("Expected exactly 27 unique drafted building observations")
    differences = []
    for rec in independently:
        candidate = indexed.get(rec["municipality_code"])
        if not candidate:
            differences.append({
                "municipality": rec["municipality"], "issue": "missing draft row",
            })
            continue
        for field in ("municipality", "year", "residential_buildings_total",
                      "buildings_pre_1981", "share_pre_1981_pct"):
            value = str(rec[field])
            if candidate.get(field) != value:
                differences.append({
                    "municipality": rec["municipality"], "field": field,
                    "raw": value, "draft": candidate.get(field),
                })
        mapped = {
            "E8": "buildings_pre_1919", "E9": "buildings_1919_1945",
            "E10": "buildings_1946_1960", "E11": "buildings_1961_1970",
            "E12": "buildings_1971_1980", "E13": "buildings_1981_1990",
            "E14": "buildings_1991_2000", "E15": "buildings_2001_2005",
            "E16": "buildings_after_2005",
        }
        for source, field in mapped.items():
            if str(rec[source]) != candidate.get(field):
                differences.append({
                    "municipality": rec["municipality"], "field": field,
                    "raw": rec[source], "draft": candidate.get(field),
                })
    region = next((item for item in benchmarks
                   if item.get("territory") == "Green Community Sinergie in Canavese"), None)
    if region is None:
        raise ValueError("Missing Green Community weighted benchmark")
    if region.get("share_pre_1981_pct") != f"{raw['green_community_weighted_pct']:.2f}":
        differences.append({
            "indicator": "green_community_weighted_pct",
            "raw": f"{raw['green_community_weighted_pct']:.2f}",
            "draft": region.get("share_pre_1981_pct"),
        })
    return {
        "schema_version": "1.0",
        "indicator_id": "old_building_stock",
        "source_page": OFFICIAL_LANDING_PAGE,
        "official_file_url": CPA_2011_URL,
        "raw_archive_sha256": _hash_bytes(original),
        "registry_sha256": _hash_bytes(registry.read_bytes()),
        "period": "2011",
        "raw_italian_section_member": raw["raw_member"],
        "raw_section_rows_for_27_codes": raw["selected_sections"],
        "municipalities_compared": len(independently),
        "differences": differences,
        "technical_pass": len(independently) == 27 and not differences,
        "municipality_rows": independently,
        "weighted_share_pct": raw["green_community_weighted_pct"],
        "technical_only": True,
        "source_authenticity_reviewed": False,
        "historical_geography_reviewed": False,
        "license_reviewed": False,
        "independent_human_sample_reviewed": False,
        "validated_for_release": False,
        "notes": (
            "Independent raw R01 section recount. This does not certify "
            "source authenticity, the 2011-2026 municipality crosswalk, "
            "or infer present-day thermal performance."
        ),
    }


def download_official_cpa(destination: Path, *, timeout: int = 120) -> dict:
    """Download original ZIP only from ISTAT HTTPS, preserving exact source bytes.

    Reject redirects to non-ISTAT hosts, nonzip responses and oversized data.
    No overwrite: archive and hash are a reproducibility boundary.
    """
    if destination.exists():
        raise FileExistsError(f"Original CPA archive already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        CPA_2011_URL, headers={
            "User-Agent": "EPAH-diagnosis/0.1 (building-stock original-source QA)",
            "Accept": "application/zip,application/octet-stream,*/*",
        }
    )
    tmp: Path | None = None
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            final_url = response.geturl()
            parsed = urlsplit(final_url)
            if parsed.scheme != "https" or not (
                parsed.hostname == "istat.it" or
                (parsed.hostname or "").endswith(".istat.it")
            ):
                raise ValueError(f"CPA redirected outside official ISTAT HTTPS: {final_url}")
            content_type = (
                response.headers.get("Content-Type", "unknown")
                if hasattr(response, "headers") else "unknown"
            )
            fd, name = tempfile.mkstemp(
                prefix=".cpa-2011-", suffix=".part", dir=destination.parent
            )
            tmp = Path(name)
            digest = hashlib.sha256()
            total = 0
            with os.fdopen(fd, "wb") as handle:
                while True:
                    block = response.read(1048576)
                    if not block:
                        break
                    total += len(block)
                    if total > MAX_SOURCE_BYTES:
                        raise ValueError("Official CPA archive exceeds 900 MiB limit")
                    digest.update(block)
                    handle.write(block)
        if not zipfile.is_zipfile(tmp):
            prefix = tmp.open("rb").read(16)
            raise ValueError(
                f"Official CPA response is not ZIP "
                f"(bytes={total}, MIME={content_type!r}, first_bytes_hex={prefix.hex()})"
            )
        with zipfile.ZipFile(tmp) as archive:
            _piemonte_section(archive)
        if destination.exists():
            raise FileExistsError(f"Destination appeared during download: {destination}")
        os.replace(tmp, destination)
        tmp = None
        return {
            "downloaded_at_utc": datetime.now(UTC).isoformat(),
            "source_url": CPA_2011_URL,
            "source_page": OFFICIAL_LANDING_PAGE,
            "response_url": final_url,
            "http_content_type": content_type,
            "bytes": total,
            "sha256": digest.hexdigest(),
            "source_authenticity_reviewed": False,
            "license_reviewed": False,
        }
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
