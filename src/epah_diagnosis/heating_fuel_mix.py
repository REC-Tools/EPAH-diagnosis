from __future__ import annotations

import csv
import io
import re
import unicodedata
from dataclasses import dataclass


FUEL_FIELDS = (
    "natural_gas",
    "diesel",
    "lpg",
    "solid_fuel",
    "fuel_oil",
    "electricity",
    "other",
)


@dataclass(frozen=True)
class HeatingFuelMix:
    municipality: str
    natural_gas: int
    diesel: int
    lpg: int
    solid_fuel: int
    fuel_oil: int
    electricity: int
    other: int

    @property
    def heated_dwellings_total(self) -> int:
        return sum(getattr(self, field) for field in FUEL_FIELDS)

    @property
    def non_natural_gas_share_pct(self) -> float:
        total = self.heated_dwellings_total
        if total <= 0:
            raise ZeroDivisionError("Heated dwellings total is zero.")
        return round((total - self.natural_gas) / total * 100, 2)


def normalize_text(value: object) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", text.casefold())


def _as_int(value: object) -> int:
    if value in (None, ""):
        return 0
    if isinstance(value, (int, float)):
        return int(round(float(value)))
    text = str(value).strip().replace(".", "").replace(" ", "")
    if not text or text in {"-", "..", "..."}:
        return 0
    text = text.replace(",", ".")
    return int(round(float(text)))


ALIASES = {
    "municipality": (
        "Comune",
        "Denominazione comune",
        "Nome comune",
        "Municipality",
    ),
    "natural_gas": (
        "Metano",
        "Gas naturale",
        "Natural gas",
    ),
    "diesel": (
        "Gasolio",
        "Diesel",
    ),
    "lpg": (
        "GPL",
        "Gas liquido GPL",
        "Gas liquefatto",
    ),
    "solid_fuel": (
        "Combustibile solido",
        "Combustibili solidi",
        "Legna carbone",
        "Legna/Carbone",
        "Solid fuel",
    ),
    "fuel_oil": (
        "Olio combustibile",
        "Fuel oil",
    ),
    "electricity": (
        "Energia elettrica",
        "Elettricita",
        "Electricity",
    ),
    "other": (
        "Altro",
        "Altro combustibile o energia",
        "Altra fonte",
        "Other",
    ),
}


def _pick_column(fieldnames: list[str], aliases: tuple[str, ...]) -> str:
    normalized = {normalize_text(field): field for field in fieldnames}
    for alias in aliases:
        key = normalize_text(alias)
        if key in normalized:
            return normalized[key]
    raise ValueError(
        "Missing expected heating-fuel column. Expected one of "
        + ", ".join(aliases)
        + ". Available: "
        + ", ".join(fieldnames)
    )


def parse_heating_fuel_mix_csv(text: str) -> list[HeatingFuelMix]:
    sample = text[:10000]
    first_line = sample.splitlines()[0] if sample.splitlines() else ""

    if ";" in first_line:
        delimiter = ";"
    elif "\t" in first_line:
        delimiter = "\t"
    else:
        delimiter = ","

    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames:
        raise ValueError("Heating fuel-mix export has no header row.")

    columns = {
        key: _pick_column(reader.fieldnames, aliases)
        for key, aliases in ALIASES.items()
    }

    records: list[HeatingFuelMix] = []
    for row in reader:
        municipality = (row.get(columns["municipality"]) or "").strip()
        if not municipality:
            continue

        values = {
            field: _as_int(row.get(columns[field]))
            for field in FUEL_FIELDS
        }

        if sum(values.values()) <= 0:
            continue

        records.append(
            HeatingFuelMix(
                municipality=municipality,
                **values,
            )
        )

    if not records:
        raise ValueError("No usable municipal heating fuel-mix records found.")

    return records


def filter_municipalities(
    records: list[HeatingFuelMix],
    target_municipalities: set[str],
) -> list[HeatingFuelMix]:
    wanted = {normalize_text(name): name for name in target_municipalities}
    by_key = {normalize_text(record.municipality): record for record in records}

    missing = sorted(
        wanted[key]
        for key in wanted
        if key not in by_key
    )
    if missing:
        raise ValueError(
            "Municipalities missing from official heating fuel-mix export: "
            + ", ".join(missing)
        )

    selected = [
        HeatingFuelMix(
            municipality=official_name,
            natural_gas=by_key[key].natural_gas,
            diesel=by_key[key].diesel,
            lpg=by_key[key].lpg,
            solid_fuel=by_key[key].solid_fuel,
            fuel_oil=by_key[key].fuel_oil,
            electricity=by_key[key].electricity,
            other=by_key[key].other,
        )
        for key, official_name in wanted.items()
    ]

    return sorted(selected, key=lambda item: item.municipality)
