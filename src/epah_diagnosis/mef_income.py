from __future__ import annotations

import csv
import io
import urllib.request
import zipfile
from dataclasses import dataclass


MEF_IRPEF_2024_URL = (
    "https://www1.finanze.gov.it/finanze/analisi_stat/public/v_4_0_0/contenuti/"
    "Redditi_e_principali_variabili_IRPEF_su_base_comunale_CSV_2024.zip"
)


@dataclass(frozen=True)
class IncomeVulnerability:
    municipality_code: str
    municipality: str
    taxpayers_total: int
    taxpayers_income_le_15000: int

    @property
    def share_income_le_15000(self) -> float:
        if self.taxpayers_total == 0:
            raise ZeroDivisionError("Taxpayers total is zero.")
        return round(self.taxpayers_income_le_15000 / self.taxpayers_total * 100, 2)


def _norm(value: str) -> str:
    return (
        value.strip()
        .lower()
        .replace("€", "euro")
        .replace(".", "")
        .replace(" ", "")
        .replace("_", "")
    )


def _find_column(fieldnames: list[str], tokens: tuple[str, ...]) -> str:
    normalized = {_norm(name): name for name in fieldnames}
    for key, original in normalized.items():
        if all(token in key for token in tokens):
            return original
    raise ValueError(f"Required MEF column not found for tokens={tokens}; fields={fieldnames}")


def _to_int(value: str) -> int:
    cleaned = value.strip().replace(".", "").replace(",", "")
    if not cleaned:
        return 0
    return int(float(cleaned))


def parse_mef_rows(rows: list[dict[str, str]]) -> list[IncomeVulnerability]:
    if not rows:
        return []

    fields = list(rows[0].keys())
    code_col = _find_column(fields, ("codice", "comune"))
    name_col = _find_column(fields, ("denominazione",))
    taxpayers_col = _find_column(fields, ("numero", "contribuenti"))
    le_zero_col = _find_column(fields, ("redditocomplessivo", "minoreouguale", "zero"))
    zero_10_col = _find_column(fields, ("redditocomplessivo", "0", "10000"))
    ten_15_col = _find_column(fields, ("redditocomplessivo", "10000", "15000"))

    output: list[IncomeVulnerability] = []
    for row in rows:
        municipality = row[name_col].strip()
        code = row[code_col].strip()
        if not municipality or not code:
            continue

        total = _to_int(row[taxpayers_col])
        low_income = (
            _to_int(row[le_zero_col])
            + _to_int(row[zero_10_col])
            + _to_int(row[ten_15_col])
        )

        output.append(
            IncomeVulnerability(
                municipality_code=code,
                municipality=municipality,
                taxpayers_total=total,
                taxpayers_income_le_15000=low_income,
            )
        )
    return output


def read_mef_csv(text: str) -> list[IncomeVulnerability]:
    sample = text[:8192]
    dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
    rows = list(csv.DictReader(io.StringIO(text), dialect=dialect))
    return parse_mef_rows(rows)


def download_mef(url: str = MEF_IRPEF_2024_URL) -> list[IncomeVulnerability]:
    request = urllib.request.Request(
        url, headers={"User-Agent": "EPAH-diagnosis/1.0"}
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        payload = response.read()

    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if not csv_names:
            raise ValueError("No CSV found in MEF archive.")
        raw = archive.read(csv_names[0])

    for encoding in ("utf-8-sig", "latin-1"):
        try:
            return read_mef_csv(raw.decode(encoding))
        except UnicodeDecodeError:
            continue
    raise ValueError("Unable to decode MEF CSV.")
