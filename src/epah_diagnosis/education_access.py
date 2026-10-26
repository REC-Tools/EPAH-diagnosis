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
    "SCUANAGRAFESTAT20242520250831.csv"
)

SECONDARY_PATHWAYS_URL = (
    "https://dati.istruzione.it/opendata/opendata/catalog/"
    "ALUSECGRADOINDSTA20242520250831.csv"
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


def _download(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 EPAH-diagnosis/1.0",
            "Accept": "text/csv,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.read()


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
        region = normalize_text(row.get("Regione"))
        if region != normalize_text(region_name):
            continue

        school_code = str(row.get("CodiceScuola") or "").strip()
        municipality = str(row.get("DescrizioneComune") or "").strip()

        if school_code and municipality:
            school_to_municipality[school_code] = municipality

    if not school_to_municipality:
        raise ValueError("No Piemonte schools found in MIM school registry.")

    municipal_flags: dict[str, dict[str, bool]] = defaultdict(
        lambda: {
            "liceo": False,
            "technical_professional": False,
        }
    )

    for row in pathway_rows:
        school_code = str(row.get("CodiceScuola") or "").strip()
        municipality = school_to_municipality.get(school_code)
        if not municipality:
            continue

        tipo = normalize_text(row.get("TipoPercorso"))
        percorso = normalize_text(row.get("Percorso"))

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
        raise ValueError("No complete upper-secondary poles identified.")

    return sorted(complete, key=lambda item: item.municipality)
