from __future__ import annotations

import csv
import io
import re
import statistics
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


ENERGY_CLASSES = ("A4", "A3", "A2", "A1", "B", "C", "D", "E", "F", "G")
POOR_CLASSES = {"E", "F", "G"}


@dataclass(frozen=True)
class ApeRecord:
    municipality: str
    energy_class: str
    epgl_nren: float | None = None


@dataclass(frozen=True)
class MunicipalityApeSummary:
    municipality: str
    total_apes: int
    poor_class_apes: int
    class_counts: dict[str, int]
    epgl_nren_median: float | None

    @property
    def poor_class_share_pct(self) -> float:
        if self.total_apes <= 0:
            raise ZeroDivisionError("APE total is zero.")
        return round(self.poor_class_apes / self.total_apes * 100, 2)


def normalize_text(value: object) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", text.casefold())


def normalize_energy_class(value: object) -> str:
    text = "" if value is None else str(value).strip().upper()
    text = text.replace(" ", "")
    if text in ENERGY_CLASSES:
        return text
    raise ValueError(f"Unsupported energy class: {value!r}")


def _as_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(" ", "")
    if not text:
        return None
    if "," in text and "." not in text:
        text = text.replace(",", ".")
    return float(text)


def _pick_column(fieldnames: list[str], aliases: tuple[str, ...], required: bool = True) -> str | None:
    normalized = {normalize_text(field): field for field in fieldnames}
    for alias in aliases:
        key = normalize_text(alias)
        if key in normalized:
            return normalized[key]
    if required:
        raise ValueError(
            "Missing required SIPEE column. Expected one of "
            + ", ".join(aliases)
            + ". Available: "
            + ", ".join(fieldnames)
        )
    return None


def parse_sipee_csv(text: str) -> list[ApeRecord]:
    sample = text[:10000]
    try:
        delimiter = csv.Sniffer().sniff(sample, delimiters=";,\t|").delimiter
    except csv.Error:
        delimiter = ";" if sample.count(";") >= sample.count(",") else ","

    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames:
        raise ValueError("SIPEE export has no header row.")

    municipality_col = _pick_column(
        reader.fieldnames,
        ("Comune", "Comune immobile", "Denominazione Comune", "Comune edificio"),
    )
    class_col = _pick_column(
        reader.fieldnames,
        (
            "Classe energetica",
            "ClasseEnergetica",
            "Classe energetica globale",
            "Classe",
        ),
    )
    epgl_col = _pick_column(
        reader.fieldnames,
        (
            "EPgl,nren",
            "EPgl nren",
            "EPGLNREN",
            "Indice prestazione energetica globale non rinnovabile",
        ),
        required=False,
    )

    records: list[ApeRecord] = []
    errors: list[str] = []

    for line_no, row in enumerate(reader, start=2):
        municipality = (row.get(municipality_col) or "").strip()
        raw_class = row.get(class_col)

        if not municipality or raw_class in (None, ""):
            continue

        try:
            energy_class = normalize_energy_class(raw_class)
            epgl_nren = _as_float(row.get(epgl_col)) if epgl_col else None
        except (TypeError, ValueError) as exc:
            errors.append(f"row {line_no}: {exc}")
            continue

        records.append(
            ApeRecord(
                municipality=municipality,
                energy_class=energy_class,
                epgl_nren=epgl_nren,
            )
        )

    if not records:
        raise ValueError(
            "No usable APE records found."
            + (f" Examples: {' | '.join(errors[:5])}" if errors else "")
        )

    return records


def aggregate_by_municipality(
    records: list[ApeRecord],
    target_municipalities: set[str],
) -> list[MunicipalityApeSummary]:
    wanted = {normalize_text(name): name for name in target_municipalities}
    grouped: dict[str, list[ApeRecord]] = {key: [] for key in wanted}

    for record in records:
        key = normalize_text(record.municipality)
        if key in grouped:
            grouped[key].append(record)

    missing = [wanted[key] for key, rows in grouped.items() if not rows]
    if missing:
        raise ValueError(
            "No SIPEE APE records for municipalities: " + ", ".join(sorted(missing))
        )

    output: list[MunicipalityApeSummary] = []
    for key, municipality in sorted(wanted.items(), key=lambda item: item[1]):
        rows = grouped[key]
        counts = Counter(record.energy_class for record in rows)
        epgl_values = [
            record.epgl_nren
            for record in rows
            if record.epgl_nren is not None
        ]

        output.append(
            MunicipalityApeSummary(
                municipality=municipality,
                total_apes=len(rows),
                poor_class_apes=sum(counts.get(cls, 0) for cls in POOR_CLASSES),
                class_counts={cls: counts.get(cls, 0) for cls in ENERGY_CLASSES},
                epgl_nren_median=(
                    statistics.median(epgl_values) if epgl_values else None
                ),
            )
        )

    return output


def read_csv_file(path: Path) -> list[ApeRecord]:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return parse_sipee_csv(raw.decode(encoding))
        except UnicodeDecodeError:
            continue
    raise ValueError("Unable to decode SIPEE export.")
