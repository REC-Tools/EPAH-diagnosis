from __future__ import annotations

import io
import re
import unicodedata
import urllib.request
from dataclasses import dataclass

from openpyxl import load_workbook


ALTITUDE_XLSX_URL = (
    "https://www.istat.it/wp-content/uploads/2026/02/"
    "Altimetria_Comuni-al-31_12_2021.xlsx"
)


@dataclass(frozen=True)
class AltitudeRecord:
    municipality: str
    mean_altitude_m: float
    min_altitude_m: float | None = None
    max_altitude_m: float | None = None


def normalize_text(value: object) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", text.casefold())


def _find_header_row(rows: list[tuple]) -> tuple[int, dict[str, int]]:
    for idx, row in enumerate(rows[:30]):
        normalized = [normalize_text(value) for value in row]

        name_idx = next(
            (
                i for i, value in enumerate(normalized)
                if value in {"comune", "denominazionecomune", "nomecomune"}
                or ("comune" in value and "cod" not in value)
            ),
            None,
        )
        mean_idx = next(
            (
                i for i, value in enumerate(normalized)
                if value in {
                    "altitudinemedia",
                    "quotamedia",
                    "altmedia",
                    "mediaaltitudine",
                }
                or ("alt" in value and "media" in value)
            ),
            None,
        )

        if name_idx is None or mean_idx is None:
            continue

        min_idx = next(
            (
                i for i, value in enumerate(normalized)
                if value in {"altitudineminima", "quotaminima", "altmin"}
                or ("alt" in value and "min" in value)
            ),
            None,
        )
        max_idx = next(
            (
                i for i, value in enumerate(normalized)
                if value in {"altitudinemassima", "quotamassima", "altmax"}
                or ("alt" in value and ("max" in value or "massima" in value))
            ),
            None,
        )
        return idx, {
            "municipality": name_idx,
            "mean": mean_idx,
            "min": min_idx if min_idx is not None else -1,
            "max": max_idx if max_idx is not None else -1,
        }

    raise ValueError("Unable to identify municipality and mean-altitude columns.")


def _as_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(".", "").replace(",", ".")
    return float(text)


def parse_altitude_workbook(payload: bytes) -> list[AltitudeRecord]:
    workbook = load_workbook(io.BytesIO(payload), read_only=True, data_only=True)

    errors: list[str] = []
    for sheet in workbook.worksheets:
        rows = list(sheet.iter_rows(values_only=True))
        try:
            header_idx, columns = _find_header_row(rows)
        except ValueError as exc:
            errors.append(f"{sheet.title}: {exc}")
            continue

        output: list[AltitudeRecord] = []
        for row in rows[header_idx + 1:]:
            if not row:
                continue
            name = row[columns["municipality"]]
            mean = row[columns["mean"]]
            if name in (None, "") or mean in (None, ""):
                continue

            min_value = (
                _as_float(row[columns["min"]])
                if columns["min"] >= 0 and columns["min"] < len(row)
                else None
            )
            max_value = (
                _as_float(row[columns["max"]])
                if columns["max"] >= 0 and columns["max"] < len(row)
                else None
            )

            output.append(
                AltitudeRecord(
                    municipality=str(name).strip(),
                    mean_altitude_m=float(_as_float(mean)),
                    min_altitude_m=min_value,
                    max_altitude_m=max_value,
                )
            )

        if output:
            return output

    raise ValueError(
        "No usable altitude table found in ISTAT workbook. "
        + " | ".join(errors[:5])
    )


def download_altitude(url: str = ALTITUDE_XLSX_URL) -> list[AltitudeRecord]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 EPAH-diagnosis/1.0"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = response.read()
    return parse_altitude_workbook(payload)


def filter_municipalities(
    records: list[AltitudeRecord],
    municipality_names: set[str],
) -> list[AltitudeRecord]:
    wanted = {normalize_text(name): name for name in municipality_names}
    selected = [
        record
        for record in records
        if normalize_text(record.municipality) in wanted
    ]

    found = {normalize_text(record.municipality) for record in selected}
    missing = sorted(
        original for key, original in wanted.items() if key not in found
    )
    if missing:
        raise ValueError(
            "Municipalities not found in ISTAT altitude dataset: "
            + ", ".join(missing)
        )

    if len(selected) != len(wanted):
        raise ValueError(
            f"Expected {len(wanted)} municipalities, found {len(selected)} rows."
        )
    return selected
