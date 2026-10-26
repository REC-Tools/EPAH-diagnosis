from __future__ import annotations

import csv
import io
import re
import urllib.request
import zipfile
from dataclasses import dataclass


CPA_2011_URL = (
    "https://www.istat.it/storage/cartografia/variabili-censuarie/"
    "dati-cpa_2011.zip"
)

PRE_1981_FIELDS = ("E8", "E9", "E10", "E11", "E12")
POST_1980_FIELDS = ("E13", "E14", "E15", "E16")
ALL_EPOCH_FIELDS = PRE_1981_FIELDS + POST_1980_FIELDS

PIEMONTE_PROVINCE_PREFIXES = {
    "001",  # Torino
    "002",  # Vercelli
    "003",  # Novara
    "004",  # Cuneo
    "005",  # Asti
    "006",  # Alessandria
    "096",  # Biella
    "103",  # Verbano-Cusio-Ossola
}


@dataclass(frozen=True)
class BuildingStock:
    municipality_code: str
    residential_buildings_total: int
    buildings_pre_1981: int
    buildings_1981_1990: int
    buildings_1991_2000: int
    buildings_2001_2005: int
    buildings_after_2005: int
    buildings_pre_1919: int
    buildings_1919_1945: int
    buildings_1946_1960: int
    buildings_1961_1970: int
    buildings_1971_1980: int

    @property
    def share_pre_1981(self) -> float:
        if self.residential_buildings_total == 0:
            raise ZeroDivisionError("Residential building total is zero.")
        return round(
            self.buildings_pre_1981 / self.residential_buildings_total * 100,
            2,
        )


def _clean_int(value: str | None) -> int:
    if value is None:
        return 0
    cleaned = value.strip().replace(".", "").replace(",", "")
    if cleaned in {"", "-", "..", "...", "...."}:
        return 0
    return int(float(cleaned))


def _normalize_code(value: str | None) -> str:
    if value is None:
        return ""
    digits = re.sub(r"\D", "", value)
    if not digits:
        return ""
    return digits.zfill(6)[-6:]


def _detect_dialect(text: str):
    return csv.Sniffer().sniff(text[:20000], delimiters=";,\t")


def _find_column(fields: list[str | None], candidates: tuple[str, ...]) -> str:
    normalized = {
        (field or "").strip().upper(): field
        for field in fields
        if field is not None and field.strip()
    }
    for candidate in candidates:
        if candidate.upper() in normalized:
            return normalized[candidate.upper()]
    raise ValueError(f"Missing expected column {candidates}. Got {fields}")


def _validate_schema(fields: list[str | None]) -> tuple[str, str]:
    code_col = _find_column(
        fields,
        ("PRO_COM", "PRO_COM_T", "PROCOM", "COD_COM", "CODCOM", "CODICE_COMUNE"),
    )
    total_col = _find_column(fields, ("E3",))
    required = (total_col,) + tuple(
        _find_column(fields, (field,)) for field in ALL_EPOCH_FIELDS
    )
    if len(required) != 10:
        raise ValueError("Unexpected building-stock schema.")
    return code_col, total_col


def parse_section_csv(text: str) -> list[BuildingStock]:
    dialect = _detect_dialect(text)
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    rows = list(reader)
    if not rows:
        raise ValueError("ISTAT census-section file is empty.")

    fields = list(rows[0].keys())
    code_col, total_col = _validate_schema(fields)
    epoch_cols = {
        field: _find_column(fields, (field,))
        for field in ALL_EPOCH_FIELDS
    }

    grouped: dict[str, dict[str, int]] = {}

    for row in rows:
        code = _normalize_code(row.get(code_col))
        if not code:
            continue

        bucket = grouped.setdefault(
            code,
            {"E3": 0, **{field: 0 for field in ALL_EPOCH_FIELDS}},
        )
        bucket["E3"] += _clean_int(row.get(total_col))
        for field, column in epoch_cols.items():
            bucket[field] += _clean_int(row.get(column))

    output: list[BuildingStock] = []
    for code, values in sorted(grouped.items()):
        total = values["E3"]
        if total <= 0:
            continue

        pre_1981 = sum(values[field] for field in PRE_1981_FIELDS)
        if pre_1981 > total:
            raise ValueError(
                f"Pre-1981 residential buildings exceed total for {code}: "
                f"{pre_1981} > {total}"
            )

        output.append(
            BuildingStock(
                municipality_code=code,
                residential_buildings_total=total,
                buildings_pre_1981=pre_1981,
                buildings_1981_1990=values["E13"],
                buildings_1991_2000=values["E14"],
                buildings_2001_2005=values["E15"],
                buildings_after_2005=values["E16"],
                buildings_pre_1919=values["E8"],
                buildings_1919_1945=values["E9"],
                buildings_1946_1960=values["E10"],
                buildings_1961_1970=values["E11"],
                buildings_1971_1980=values["E12"],
            )
        )

    if not output:
        raise ValueError("No municipal building-stock records were produced.")

    return output


def _decode(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Unable to decode ISTAT census-section table.")


def _merge_municipal_records(
    chunks: list[list[BuildingStock]],
) -> list[BuildingStock]:
    by_code: dict[str, BuildingStock] = {}

    for chunk in chunks:
        for item in chunk:
            if item.municipality_code in by_code:
                raise ValueError(
                    "Duplicate municipality across ISTAT regional files: "
                    f"{item.municipality_code}"
                )
            by_code[item.municipality_code] = item

    return [by_code[code] for code in sorted(by_code)]


def parse_cpa_zip(payload: bytes) -> list[BuildingStock]:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        candidates = [
            name
            for name in archive.namelist()
            if name.lower().endswith((".csv", ".txt"))
        ]
        if not candidates:
            raise ValueError("No CSV/TXT found inside ISTAT CPA 2011 archive.")

        parsed_chunks: list[list[BuildingStock]] = []
        errors: list[str] = []

        for name in sorted(candidates):
            try:
                text = _decode(archive.read(name))
                parsed_chunks.append(parse_section_csv(text))
            except (ValueError, csv.Error) as exc:
                errors.append(f"{name}: {exc}")

    if not parsed_chunks:
        raise ValueError(
            "No table with PROCOM/PRO_COM, E3 and E8-E16 found in ISTAT archive. "
            + " | ".join(errors[:5])
        )

    return _merge_municipal_records(parsed_chunks)


def download_cpa_2011(url: str = CPA_2011_URL) -> list[BuildingStock]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 EPAH-diagnosis/1.0",
            "Accept": "application/zip,application/octet-stream,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = response.read()
    return parse_cpa_zip(payload)


def filter_by_codes(
    data: list[BuildingStock],
    municipality_codes: set[str],
) -> list[BuildingStock]:
    wanted = {_normalize_code(code) for code in municipality_codes}
    selected = [item for item in data if item.municipality_code in wanted]

    found = {item.municipality_code for item in selected}
    missing = sorted(wanted - found)
    if missing:
        raise ValueError(
            "Municipalities not found in ISTAT CPA 2011 dataset: "
            + ", ".join(missing)
        )

    if len(selected) != len(wanted):
        raise ValueError(
            f"Expected {len(wanted)} municipalities, found {len(selected)} rows."
        )
    return selected


def weighted_share_pre_1981(items: list[BuildingStock]) -> float:
    total = sum(item.residential_buildings_total for item in items)
    old = sum(item.buildings_pre_1981 for item in items)
    if total == 0:
        raise ZeroDivisionError("Residential building total is zero.")
    return round(old / total * 100, 2)


def is_piemonte(code: str) -> bool:
    normalized = _normalize_code(code)
    return normalized[:3] in PIEMONTE_PROVINCE_PREFIXES
