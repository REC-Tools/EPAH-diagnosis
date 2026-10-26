from __future__ import annotations

import csv
import io
import re
import unicodedata
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
    region: str
    taxpayers_total: int
    taxpayers_income_le_15000: int
    total_income_frequency: int | None = None
    total_income_amount_eur: float | None = None

    @property
    def share_income_le_15000(self) -> float:
        if self.taxpayers_total == 0:
            raise ZeroDivisionError("Taxpayers total is zero.")
        return round(self.taxpayers_income_le_15000 / self.taxpayers_total * 100, 2)

    @property
    def mean_total_income_eur(self) -> float | None:
        if (
            self.total_income_frequency is None
            or self.total_income_amount_eur is None
            or self.total_income_frequency == 0
        ):
            return None
        return round(self.total_income_amount_eur / self.total_income_frequency, 2)


def normalize_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return (
        value.strip()
        .casefold()
        .replace("€", "euro")
        .replace(".", "")
        .replace("_", "")
        .replace(" ", "")
    )


def _find_exact_column(fieldnames: list[str | None], candidates: tuple[str, ...]) -> str:
    normalized = {
        _norm(name): name
        for name in fieldnames
        if name is not None and name.strip()
    }
    for candidate in candidates:
        key = _norm(candidate)
        if key in normalized:
            return normalized[key]
    raise ValueError(
        f"Required MEF column not found. Expected one of {candidates}; "
        f"fields={fieldnames}"
    )


def _find_optional_column(fieldnames: list[str | None], candidates: tuple[str, ...]) -> str | None:
    try:
        return _find_exact_column(fieldnames, candidates)
    except ValueError:
        return None


def _to_int(value: str | None) -> int:
    if value is None:
        return 0
    cleaned = value.strip().replace(" ", "")
    if not cleaned:
        return 0
    # Frequencies are integers; tolerate thousands separators and decimal artifacts.
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").split(",")[0]
    else:
        cleaned = cleaned.replace(".", "").replace(",", "")
    return int(float(cleaned))


def _to_float_it(value: str | None) -> float | None:
    if value is None:
        return None
    cleaned = value.strip().replace(" ", "")
    if not cleaned:
        return None

    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    return float(cleaned)


def _detect_header(text: str) -> tuple[str, str]:
    lines = [line for line in text.splitlines() if line.strip()]
    for index, line in enumerate(lines[:50]):
        for delimiter in (";", ",", "\t"):
            cells = [cell.strip().strip('"').casefold() for cell in line.split(delimiter)]
            joined = " ".join(cells)
            if (
                "denominazione comune" in joined
                and "numero contribuenti" in joined
                and "reddito complessivo da 0 a 10000 euro" in joined
            ):
                return "\n".join(lines[index:]) + "\n", delimiter

    preview = "\n".join(lines[:10])
    raise ValueError(
        "Unable to locate MEF municipal CSV header. "
        f"First non-empty rows were:\n{preview}"
    )


def parse_mef_rows(rows: list[dict[str, str]]) -> list[IncomeVulnerability]:
    if not rows:
        return []

    fields = list(rows[0].keys())

    code_col = _find_exact_column(
        fields,
        ("Codice Istat Comune", "Codice comune", "Codice Istat"),
    )
    name_col = _find_exact_column(fields, ("Denominazione Comune", "Comune"))
    region_col = _find_exact_column(fields, ("Regione",))
    taxpayers_col = _find_exact_column(fields, ("Numero contribuenti",))

    le_zero_col = _find_exact_column(
        fields,
        ("Reddito complessivo minore o uguale a zero euro - Frequenza",),
    )
    zero_10_col = _find_exact_column(
        fields,
        ("Reddito complessivo da 0 a 10000 euro - Frequenza",),
    )
    ten_15_col = _find_exact_column(
        fields,
        ("Reddito complessivo da 10000 a 15000 euro - Frequenza",),
    )

    total_income_freq_col = _find_optional_column(
        fields,
        ("Reddito complessivo - Frequenza",),
    )
    total_income_amount_col = _find_optional_column(
        fields,
        ("Reddito complessivo - Ammontare in euro",),
    )

    output: list[IncomeVulnerability] = []
    for row in rows:
        if None in row:
            row.pop(None, None)

        municipality = (row.get(name_col) or "").strip()
        code = (row.get(code_col) or "").strip()
        region = (row.get(region_col) or "").strip()

        if not municipality or not code:
            continue

        total = _to_int(row.get(taxpayers_col))
        if total <= 0:
            continue

        low_income = (
            _to_int(row.get(le_zero_col))
            + _to_int(row.get(zero_10_col))
            + _to_int(row.get(ten_15_col))
        )

        if low_income < 0 or low_income > total:
            raise ValueError(
                f"Invalid low-income frequency for {municipality}: "
                f"{low_income} out of {total}"
            )

        output.append(
            IncomeVulnerability(
                municipality_code=code,
                municipality=municipality,
                region=region,
                taxpayers_total=total,
                taxpayers_income_le_15000=low_income,
                total_income_frequency=(
                    _to_int(row.get(total_income_freq_col))
                    if total_income_freq_col
                    else None
                ),
                total_income_amount_eur=(
                    _to_float_it(row.get(total_income_amount_col))
                    if total_income_amount_col
                    else None
                ),
            )
        )

    if not output:
        raise ValueError("MEF parser produced no valid municipal rows.")

    return output


def read_mef_csv(text: str) -> list[IncomeVulnerability]:
    table_text, delimiter = _detect_header(text)
    rows = list(csv.DictReader(io.StringIO(table_text), delimiter=delimiter))
    return parse_mef_rows(rows)


def download_mef(url: str = MEF_IRPEF_2024_URL) -> list[IncomeVulnerability]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 EPAH-diagnosis/1.0",
            "Accept": "application/zip,application/octet-stream,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        payload = response.read()

    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if not csv_names:
            raise ValueError("No CSV found in MEF archive.")

        # Prefer the largest CSV if the archive contains documentation or extra tables.
        csv_names.sort(key=lambda name: archive.getinfo(name).file_size, reverse=True)
        raw = archive.read(csv_names[0])

    for encoding in ("utf-8-sig", "latin-1"):
        try:
            text = raw.decode(encoding)
            return read_mef_csv(text)
        except UnicodeDecodeError:
            continue

    raise ValueError("Unable to decode MEF CSV.")


def filter_municipalities(
    data: list[IncomeVulnerability],
    municipality_names: set[str],
) -> list[IncomeVulnerability]:
    wanted = {normalize_name(name): name for name in municipality_names}
    selected = [
        item
        for item in data
        if normalize_name(item.municipality) in wanted
    ]

    found = {normalize_name(item.municipality) for item in selected}
    missing = sorted(
        original
        for key, original in wanted.items()
        if key not in found
    )
    if missing:
        raise ValueError(f"Municipalities not found in MEF dataset: {', '.join(missing)}")

    if len(selected) != len(municipality_names):
        raise ValueError(
            f"Expected {len(municipality_names)} unique municipalities, "
            f"found {len(selected)} rows."
        )

    return selected
