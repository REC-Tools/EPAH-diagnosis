from __future__ import annotations

import csv
import io
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path


POSAS_2026_URL = "https://demo.istat.it/data/posas/POSAS_2026_it_Comuni.zip"


@dataclass(frozen=True)
class Population65Plus:
    municipality_code: str
    municipality: str
    population_total: int
    population_65_plus: int

    @property
    def share_65_plus(self) -> float:
        if self.population_total == 0:
            raise ZeroDivisionError("Population total is zero.")
        return round(self.population_65_plus / self.population_total * 100, 2)


def _pick_column(fieldnames: list[str | None], candidates: tuple[str, ...]) -> str:
    normalized = {
        name.strip().lower(): name
        for name in fieldnames
        if name is not None and name.strip()
    }
    for candidate in candidates:
        if candidate.lower() in normalized:
            return normalized[candidate.lower()]
    raise ValueError(f"None of the expected columns found: {candidates}. Got {fieldnames}")


def _detect_header(text: str) -> tuple[str, str]:
    """Return CSV text starting at the real header row and its delimiter.

    ISTAT POSAS files may begin with one or more descriptive rows before the
    tabular header, e.g. "Popolazione residente per età e sesso...".
    """
    lines = [line for line in text.splitlines() if line.strip()]
    delimiters = (";", ",", "\t")

    for index, line in enumerate(lines[:50]):
        for delimiter in delimiters:
            cells = [cell.strip().strip('"').lower() for cell in line.split(delimiter)]
            has_comune = any(cell in {"comune", "denominazione", "nome comune"} or "comune" in cell for cell in cells)
            has_age = any(cell in {"eta", "età"} or cell.startswith("età") or cell.startswith("eta") for cell in cells)
            has_total = any(cell in {"totale", "tot_p", "tot"} or "totale" in cell for cell in cells)
            if has_comune and has_age and has_total and len(cells) >= 4:
                return "\n".join(lines[index:]) + "\n", delimiter

    preview = "\n".join(lines[:10])
    raise ValueError(
        "Unable to locate the POSAS table header. "
        "Expected a row containing Comune, Età/Eta and Totale. "
        f"First rows were:\n{preview}"
    )


def calculate_65_plus_from_rows(rows: list[dict[str, str]]) -> list[Population65Plus]:
    if not rows:
        return []

    fields = list(rows[0].keys())
    code_col = _pick_column(fields, ("codice comune", "codice_comune", "codice", "pro_com_t"))
    name_col = _pick_column(fields, ("comune", "denominazione", "nome comune"))
    age_col = _pick_column(fields, ("eta", "età"))
    total_col = _pick_column(fields, ("totale", "tot_p", "tot"))

    grouped: dict[tuple[str, str], dict[str, int]] = {}

    for row in rows:
        if None in row:
            row.pop(None, None)

        code = row[code_col].strip()
        name = row[name_col].strip()
        raw_age = row[age_col].strip()
        raw_total = row[total_col].strip().replace(".", "")

        if not code or not name or not raw_total:
            continue

        try:
            age = int(raw_age)
            value = int(raw_total)
        except ValueError:
            continue

        # ISTAT uses age 999 as an explicit total row; do not include it in sums.
        if age == 999:
            continue

        bucket = grouped.setdefault((code, name), {"total": 0, "over65": 0})
        bucket["total"] += value
        if age >= 65:
            bucket["over65"] += value

    return [
        Population65Plus(
            municipality_code=code,
            municipality=name,
            population_total=values["total"],
            population_65_plus=values["over65"],
        )
        for (code, name), values in sorted(grouped.items())
    ]


def read_posas_csv(text: str) -> list[Population65Plus]:
    table_text, delimiter = _detect_header(text)
    rows = list(csv.DictReader(io.StringIO(table_text), delimiter=delimiter))
    return calculate_65_plus_from_rows(rows)


def download_posas(url: str = POSAS_2026_URL) -> list[Population65Plus]:
    with urllib.request.urlopen(url, timeout=90) as response:
        payload = response.read()

    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if not csv_names:
            raise ValueError("No CSV file found inside ISTAT POSAS archive.")

        if len(csv_names) > 1:
            csv_names.sort(key=len)

        raw = archive.read(csv_names[0])
        for encoding in ("utf-8-sig", "latin-1"):
            try:
                text = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise UnicodeDecodeError("unknown", raw, 0, 1, "Unable to decode POSAS CSV")

    return read_posas_csv(text)


def filter_municipalities(
    data: list[Population65Plus], municipality_names: set[str]
) -> list[Population65Plus]:
    wanted = {name.casefold(): name for name in municipality_names}
    selected = [item for item in data if item.municipality.casefold() in wanted]

    found = {item.municipality.casefold() for item in selected}
    missing = sorted(name for key, name in wanted.items() if key not in found)
    if missing:
        raise ValueError(f"Municipalities not found in POSAS: {', '.join(missing)}")

    return selected


def write_indicator_csv(data: list[Population65Plus], output: Path, year: int = 2026) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "municipality_code",
                "municipality",
                "year",
                "population_total",
                "population_65_plus",
                "share_65_plus_pct",
                "source",
                "quality",
                "limitations",
            ],
        )
        writer.writeheader()
        for item in data:
            writer.writerow(
                {
                    "municipality_code": item.municipality_code,
                    "municipality": item.municipality,
                    "year": year,
                    "population_total": item.population_total,
                    "population_65_plus": item.population_65_plus,
                    "share_65_plus_pct": f"{item.share_65_plus:.2f}",
                    "source": "ISTAT POSAS",
                    "quality": "Official source; latest year is provisional estimate",
                    "limitations": "2026 population by age and sex is an ISTAT estimate.",
                }
            )
