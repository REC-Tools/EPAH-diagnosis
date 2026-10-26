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


@dataclass(frozen=True)
class HeatingFacilitiesRecord:
    municipality_code: str
    occupied_dwellings: int
    occupied_dwellings_with_heating: int

    @property
    def heating_gap_pct(self) -> float:
        if self.occupied_dwellings <= 0:
            raise ZeroDivisionError("Occupied dwellings total is zero.")
        without_heating = max(
            0,
            self.occupied_dwellings - self.occupied_dwellings_with_heating,
        )
        return round(without_heating / self.occupied_dwellings * 100, 2)


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


def _decode(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Unable to decode ISTAT census-section table.")


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


def _detect_dialect(text: str):
    return csv.Sniffer().sniff(text[:20000], delimiters=";,\t")


def parse_section_csv(text: str) -> list[HeatingFacilitiesRecord]:
    dialect = _detect_dialect(text)
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    rows = list(reader)
    if not rows:
        raise ValueError("ISTAT census-section file is empty.")

    fields = list(rows[0].keys())
    code_col = _find_column(
        fields,
        ("PRO_COM", "PRO_COM_T", "PROCOM", "COD_COM", "CODCOM", "CODICE_COMUNE"),
    )
    occupied_col = _find_column(fields, ("A2",))
    heating_col = _find_column(fields, ("A24",))

    grouped: dict[str, dict[str, int]] = {}

    for row in rows:
        code = _normalize_code(row.get(code_col))
        if not code:
            continue

        bucket = grouped.setdefault(code, {"A2": 0, "A24": 0})
        bucket["A2"] += _clean_int(row.get(occupied_col))
        bucket["A24"] += _clean_int(row.get(heating_col))

    output: list[HeatingFacilitiesRecord] = []
    for code, values in sorted(grouped.items()):
        occupied = values["A2"]
        heated = values["A24"]
        if occupied <= 0:
            continue
        if heated > occupied:
            raise ValueError(
                f"Occupied dwellings with heating exceed occupied dwellings for "
                f"{code}: {heated} > {occupied}"
            )

        output.append(
            HeatingFacilitiesRecord(
                municipality_code=code,
                occupied_dwellings=occupied,
                occupied_dwellings_with_heating=heated,
            )
        )

    if not output:
        raise ValueError("No municipal heating-facilities records were produced.")

    return output


def parse_cpa_zip(payload: bytes) -> list[HeatingFacilitiesRecord]:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        candidates = [
            name
            for name in archive.namelist()
            if name.lower().endswith(".csv")
            and "indicatori_2011_sezioni" in name.lower()
        ]
        if not candidates:
            raise ValueError("No ISTAT census-section CSV files found.")

        by_code: dict[str, HeatingFacilitiesRecord] = {}
        errors: list[str] = []

        for name in sorted(candidates):
            try:
                records = parse_section_csv(_decode(archive.read(name)))
            except (ValueError, csv.Error) as exc:
                errors.append(f"{name}: {exc}")
                continue

            for record in records:
                if record.municipality_code in by_code:
                    raise ValueError(
                        "Duplicate municipality across ISTAT regional files: "
                        f"{record.municipality_code}"
                    )
                by_code[record.municipality_code] = record

    if not by_code:
        raise ValueError(
            "No table with PROCOM/PRO_COM, A2 and A24 found in ISTAT archive. "
            + " | ".join(errors[:5])
        )

    return [by_code[code] for code in sorted(by_code)]


def download_heating_facilities(
    url: str = CPA_2011_URL,
) -> list[HeatingFacilitiesRecord]:
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
    data: list[HeatingFacilitiesRecord],
    municipality_codes: set[str],
) -> list[HeatingFacilitiesRecord]:
    wanted = {_normalize_code(code) for code in municipality_codes}
    selected = [item for item in data if item.municipality_code in wanted]

    found = {item.municipality_code for item in selected}
    missing = sorted(wanted - found)
    if missing:
        raise ValueError(
            "Municipalities not found in ISTAT heating dataset: "
            + ", ".join(missing)
        )

    if len(selected) != len(wanted):
        raise ValueError(
            f"Expected {len(wanted)} municipalities, found {len(selected)} rows."
        )

    return selected
