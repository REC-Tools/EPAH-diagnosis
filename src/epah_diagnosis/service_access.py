from __future__ import annotations

import csv
import io
import re
import unicodedata
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path


PIEMONTE_DISTANCE_MATRIX_URL = (
    "https://www.istat.it/storage/cartografia/matrici_distanze/Piemonte.zip"
)


@dataclass(frozen=True)
class AccessibilityResult:
    municipality: str
    service_municipality: str
    travel_time_minutes: float
    distance_km: float | None = None


def normalize_text(value: object) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", text.casefold())


def _detect_delimiter(sample: str) -> str:
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,\t|").delimiter
    except csv.Error:
        return ";" if sample.count(";") >= sample.count(",") else ","


def _find_column(fieldnames: list[str], patterns: tuple[tuple[str, ...], ...]) -> str:
    normalized = {field: normalize_text(field) for field in fieldnames}
    for required_parts in patterns:
        for field, value in normalized.items():
            if all(part in value for part in required_parts):
                return field
    raise ValueError(
        "Unable to identify required ISTAT matrix column. Fields: "
        + ", ".join(fieldnames)
    )


def _matrix_columns(fieldnames: list[str]) -> dict[str, str]:
    return {
        "origin": _find_column(
            fieldnames,
            (
                ("comune", "origine"),
                ("comune", "partenza"),
                ("origine", "denominazione"),
                ("origine", "nome"),
            ),
        ),
        "destination": _find_column(
            fieldnames,
            (
                ("comune", "destinazione"),
                ("destinazione", "denominazione"),
                ("destinazione", "nome"),
                ("comune", "arrivo"),
            ),
        ),
        "time": _find_column(
            fieldnames,
            (
                ("tempo", "min"),
                ("tempo",),
                ("durata", "min"),
                ("durata",),
            ),
        ),
    }


def _optional_distance_column(fieldnames: list[str]) -> str | None:
    try:
        return _find_column(
            fieldnames,
            (
                ("distanza", "km"),
                ("distanza",),
                ("km",),
            ),
        )
    except ValueError:
        return None


def _as_float(value: object) -> float:
    text = str(value).strip().replace(" ", "")
    if not text:
        raise ValueError("empty numeric value")
    if "," in text and "." not in text:
        text = text.replace(",", ".")
    return float(text)


def nearest_services_from_zip(
    payload: bytes,
    origin_municipalities: set[str],
    service_municipalities: set[str],
) -> list[AccessibilityResult]:
    wanted_origins = {
        normalize_text(name): name for name in origin_municipalities
    }
    wanted_services = {
        normalize_text(name): name for name in service_municipalities
    }
    best: dict[str, AccessibilityResult] = {}
    parsed_any_csv = False
    schema_errors: list[str] = []

    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        members = [
            name for name in archive.namelist()
            if name.lower().endswith(".csv")
        ]
        if not members:
            raise ValueError("No CSV files found in ISTAT Piemonte matrix archive.")

        for member in members:
            with archive.open(member) as raw:
                text_stream = io.TextIOWrapper(
                    raw,
                    encoding="utf-8-sig",
                    errors="replace",
                    newline="",
                )
                sample = text_stream.read(8192)
                delimiter = _detect_delimiter(sample)
                text_stream.seek(0)
                reader = csv.DictReader(text_stream, delimiter=delimiter)

                if not reader.fieldnames:
                    continue

                try:
                    columns = _matrix_columns(reader.fieldnames)
                except ValueError as exc:
                    schema_errors.append(f"{member}: {exc}")
                    continue

                parsed_any_csv = True
                distance_column = _optional_distance_column(reader.fieldnames)

                for row in reader:
                    origin_raw = row.get(columns["origin"])
                    destination_raw = row.get(columns["destination"])
                    if not origin_raw or not destination_raw:
                        continue

                    origin_key = normalize_text(origin_raw)
                    if origin_key not in wanted_origins:
                        continue

                    destination_key = normalize_text(destination_raw)
                    if destination_key not in wanted_services:
                        continue

                    try:
                        minutes = _as_float(row.get(columns["time"], ""))
                    except (TypeError, ValueError):
                        continue

                    distance = None
                    if distance_column is not None:
                        try:
                            distance = _as_float(row.get(distance_column, ""))
                        except (TypeError, ValueError):
                            distance = None

                    candidate = AccessibilityResult(
                        municipality=wanted_origins[origin_key],
                        service_municipality=wanted_services[destination_key],
                        travel_time_minutes=minutes,
                        distance_km=distance,
                    )

                    previous = best.get(origin_key)
                    if previous is None or minutes < previous.travel_time_minutes:
                        best[origin_key] = candidate

    if not parsed_any_csv:
        raise ValueError(
            "No ISTAT matrix CSV had a recognized schema. "
            + " | ".join(schema_errors[:5])
        )

    missing = sorted(
        original
        for key, original in wanted_origins.items()
        if key not in best
    )
    if missing:
        raise ValueError(
            "No DEA travel-time result for municipalities: "
            + ", ".join(missing)
        )

    return sorted(best.values(), key=lambda item: item.municipality)


def download_piemonte_matrix(
    url: str = PIEMONTE_DISTANCE_MATRIX_URL,
) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 EPAH-diagnosis/1.0",
            "Accept": "application/zip,application/octet-stream,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.read()


def read_service_municipalities(path: Path) -> set[str]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {
            row["municipality"].strip()
            for row in csv.DictReader(handle)
            if row["municipality"].strip()
        }
