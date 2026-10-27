from __future__ import annotations

import csv
import io
import re
import unicodedata
from dataclasses import dataclass


MIN_RESPONDENTS = 10


@dataclass(frozen=True)
class AffordabilityRecord:
    municipality: str
    respondents: int
    unable_warm_yes: int
    utility_arrears_yes: int
    unable_cool_yes: int
    reduced_heating_cost_yes: int

    def share(self, field: str) -> float | None:
        if self.respondents < MIN_RESPONDENTS:
            return None
        value = getattr(self, field)
        return round(value / self.respondents * 100, 2)


def normalize_text(value: object) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", text.casefold())


def _as_int(value: object) -> int:
    if value in (None, ""):
        return 0
    text = str(value).strip().replace(" ", "")
    if not text:
        return 0
    return int(float(text.replace(",", ".")))


ALIASES = {
    "municipality": (
        "municipality",
        "comune",
        "denominazione comune",
    ),
    "respondents": (
        "respondents",
        "rispondenti",
        "numero rispondenti",
        "n rispondenti",
    ),
    "unable_warm_yes": (
        "unable_warm_yes",
        "incapacita caldo yes",
        "non riesce a mantenere casa calda",
        "unable to keep home warm",
    ),
    "utility_arrears_yes": (
        "utility_arrears_yes",
        "arretrati bollette yes",
        "arretrati bollette",
        "utility arrears",
    ),
    "unable_cool_yes": (
        "unable_cool_yes",
        "incapacita fresco yes",
        "non riesce a mantenere casa fresca",
        "unable to keep home cool",
    ),
    "reduced_heating_cost_yes": (
        "reduced_heating_cost_yes",
        "riduzione riscaldamento per costo yes",
        "riduce riscaldamento per costo",
        "reduced heating for cost",
    ),
}


def _pick_column(fieldnames: list[str], aliases: tuple[str, ...]) -> str:
    normalized = {normalize_text(field): field for field in fieldnames}
    for alias in aliases:
        key = normalize_text(alias)
        if key in normalized:
            return normalized[key]
    raise ValueError(
        "Missing expected local-affordability column. Expected one of "
        + ", ".join(aliases)
        + ". Available: "
        + ", ".join(fieldnames)
    )


def parse_affordability_csv(text: str) -> list[AffordabilityRecord]:
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
        raise ValueError("Local affordability file has no header row.")

    columns = {
        key: _pick_column(reader.fieldnames, aliases)
        for key, aliases in ALIASES.items()
    }

    records: list[AffordabilityRecord] = []
    for row in reader:
        municipality = (row.get(columns["municipality"]) or "").strip()
        if not municipality:
            continue

        record = AffordabilityRecord(
            municipality=municipality,
            respondents=_as_int(row.get(columns["respondents"])),
            unable_warm_yes=_as_int(row.get(columns["unable_warm_yes"])),
            utility_arrears_yes=_as_int(row.get(columns["utility_arrears_yes"])),
            unable_cool_yes=_as_int(row.get(columns["unable_cool_yes"])),
            reduced_heating_cost_yes=_as_int(
                row.get(columns["reduced_heating_cost_yes"])
            ),
        )

        if record.respondents < 0:
            raise ValueError(f"Negative respondents for {municipality}.")

        for field in (
            "unable_warm_yes",
            "utility_arrears_yes",
            "unable_cool_yes",
            "reduced_heating_cost_yes",
        ):
            value = getattr(record, field)
            if value < 0 or value > record.respondents:
                raise ValueError(
                    f"Invalid {field}={value} for {municipality}: "
                    f"respondents={record.respondents}."
                )

        records.append(record)

    if not records:
        raise ValueError("No usable local-affordability records found.")

    return records


def filter_municipalities(
    records: list[AffordabilityRecord],
    target_municipalities: set[str],
) -> list[AffordabilityRecord]:
    wanted = {normalize_text(name): name for name in target_municipalities}
    by_key = {normalize_text(record.municipality): record for record in records}

    missing = sorted(
        wanted[key]
        for key in wanted
        if key not in by_key
    )
    if missing:
        raise ValueError(
            "Municipalities missing from local-affordability file: "
            + ", ".join(missing)
        )

    selected = []
    for key, official_name in wanted.items():
        record = by_key[key]
        selected.append(
            AffordabilityRecord(
                municipality=official_name,
                respondents=record.respondents,
                unable_warm_yes=record.unable_warm_yes,
                utility_arrears_yes=record.utility_arrears_yes,
                unable_cool_yes=record.unable_cool_yes,
                reduced_heating_cost_yes=record.reduced_heating_cost_yes,
            )
        )

    return sorted(selected, key=lambda item: item.municipality)
