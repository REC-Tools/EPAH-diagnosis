from __future__ import annotations

import csv
import io
import re
import unicodedata
import urllib.request
from collections import defaultdict
from dataclasses import dataclass


SCHOOL_REGISTRY_URL = (
    "https://dati.istruzione.it/opendata/opendata/catalog/"
    "SCUANAGRAFESTAT/SCUANAGRAFESTAT20242520250831.csv"
)

SECONDARY_PATHWAYS_URL = (
    "https://dati.istruzione.it/opendata/opendata/catalog/"
    "ALUSECGRADOINDSTA/ALUSECGRADOINDSTA20242520250831.csv"
)


@dataclass(frozen=True)
class SchoolPole:
    municipality: str
    has_classical_or_scientific_lyceum: bool
    has_technical_or_professional: bool

    @property
    def is_complete_upper_secondary_pole(self) -> bool:
        return (
            self.has_classical_or_scientific_lyceum
            and self.has_technical_or_professional
        )


def normalize_text(value: object) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", text.casefold())


def _row_value(row: dict[str, str], *aliases: str) -> str:
    normalized = {
        normalize_text(key): value
        for key, value in row.items()
        if key is not None
    }

    for alias in aliases:
        key = normalize_text(alias)
        if key in normalized:
            value = normalized[key]
            return "" if value is None else str(value).strip()

    return ""


def _available_columns(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "<no rows>"
    return ", ".join(str(key) for key in rows[0].keys())


def _download(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 EPAH-diagnosis/1.0",
            "Accept": "text/csv,application/octet-stream,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        payload = response.read()
        content_type = (response.headers.get("Content-Type") or "").casefold()

    prefix = payload[:512].lstrip().lower()
    if (
        "text/html" in content_type
        or prefix.startswith(b"<!doctype html")
        or prefix.startswith(b"<html")
    ):
        raise ValueError(
            "MIM download returned HTML instead of CSV. "
            f"Check direct dataset distribution URL: {url}"
        )

    return payload


def _decode_csv(payload: bytes) -> list[dict[str, str]]:
    text = payload.decode("utf-8-sig", errors="replace")
    sample = text[:8192]
    try:
        delimiter = csv.Sniffer().sniff(sample, delimiters=";,\t|").delimiter
    except csv.Error:
        delimiter = ";" if sample.count(";") >= sample.count(",") else ","
    return list(csv.DictReader(io.StringIO(text), delimiter=delimiter))


def download_school_registry(url: str = SCHOOL_REGISTRY_URL) -> list[dict[str, str]]:
    return _decode_csv(_download(url))


def download_secondary_pathways(
    url: str = SECONDARY_PATHWAYS_URL,
) -> list[dict[str, str]]:
    return _decode_csv(_download(url))


def build_upper_secondary_poles(
    registry_rows: list[dict[str, str]],
    pathway_rows: list[dict[str, str]],
    region_name: str = "PIEMONTE",
) -> list[SchoolPole]:
    school_to_municipality: dict[str, str] = {}

    for row in registry_rows:
        region = normalize_text(
            _row_value(
                row,
                "Regione",
                "DenominazioneRegione",
                "DescrizioneRegione",
            )
        )
        if region != normalize_text(region_name):
            continue

        school_code = _row_value(
            row,
            "CodiceScuola",
            "CodiceIstituto",
            "CodiceMeccanografico",
        )
        municipality = _row_value(
            row,
            "DescrizioneComune",
            "Comune",
            "DenominazioneComune",
            "ComuneScuola",
        )

        if school_code and municipality:
            school_to_municipality[school_code] = municipality

    if not school_to_municipality:
        raise ValueError(
            "No Piemonte schools found in MIM school registry. "
            "Available columns: " + _available_columns(registry_rows)
        )

    municipal_flags: dict[str, dict[str, bool]] = defaultdict(
        lambda: {
            "liceo": False,
            "technical_professional": False,
        }
    )

    for row in pathway_rows:
        school_code = _row_value(
            row,
            "CodiceScuola",
            "CodiceIstituto",
            "CodiceMeccanografico",
        )
        municipality = school_to_municipality.get(school_code)
        if not municipality:
            continue

        tipo = normalize_text(
            _row_value(
                row,
                "TipoPercorso",
                "TipologiaPercorso",
                "TipoIstituto",
            )
        )
        percorso = normalize_text(
            _row_value(
                row,
                "Percorso",
                "DescrizionePercorso",
                "Indirizzo",
            )
        )

        if tipo == "liceo" and (
            "classico" in percorso or "scientifico" in percorso
        ):
            municipal_flags[municipality]["liceo"] = True

        if tipo in {
            "tecnico",
            "professionale",
            "professionaleiefp",
        }:
            municipal_flags[municipality]["technical_professional"] = True

    poles = [
        SchoolPole(
            municipality=municipality,
            has_classical_or_scientific_lyceum=flags["liceo"],
            has_technical_or_professional=flags["technical_professional"],
        )
        for municipality, flags in municipal_flags.items()
    ]

    complete = [pole for pole in poles if pole.is_complete_upper_secondary_pole]
    if not complete:
        raise ValueError(
            "No complete upper-secondary poles identified. "
            "Pathway columns: " + _available_columns(pathway_rows)
        )

    return sorted(complete, key=lambda item: item.municipality)
