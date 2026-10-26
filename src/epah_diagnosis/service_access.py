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


def normalize_istat_code(value: object) -> str:
    digits = re.sub(r"\D", "", "" if value is None else str(value))
    if not digits:
        return ""
    return digits.zfill(6)[-6:]


def _detect_delimiter(sample: str) -> str:
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,\t|").delimiter
    except csv.Error:
        return ";" if sample.count(";") >= sample.count(",") else ","


def _as_float(value: object) -> float:
    text = str(value).strip().replace(" ", "")
    if not text:
        raise ValueError("empty numeric value")
    if "," in text and "." not in text:
        text = text.replace(",", ".")
    return float(text)


def _matrix_columns(fieldnames: list[str]) -> dict[str, str]:
    normalized = {field.upper(): field for field in fieldnames}

    required = {
        "origin_code": "OR_PROCOM",
        "destination_code": "DEST_PROCOM",
        "time": "TEP_TOT",
    }

    missing = [source for source in required.values() if source not in normalized]
    if missing:
        raise ValueError(
            "Missing ISTAT matrix columns "
            + ", ".join(missing)
            + ". Fields: "
            + ", ".join(fieldnames)
        )

    columns = {
        key: normalized[source]
        for key, source in required.items()
    }
    if "KM_TOT" in normalized:
        columns["distance"] = normalized["KM_TOT"]

    return columns


def nearest_services_from_zip(
    payload: bytes,
    origin_codes: dict[str, str],
    service_codes: dict[str, str],
) -> list[AccessibilityResult]:
    """Return the fastest DEA destination for every origin.

    origin_codes and service_codes map six-digit ISTAT PROCOM codes to the
    municipality names that should appear in the output.
    """
    wanted_origins = {
        normalize_istat_code(code): name
        for code, name in origin_codes.items()
    }
    wanted_services = {
        normalize_istat_code(code): name
        for code, name in service_codes.items()
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

                for row in reader:
                    origin_code = normalize_istat_code(row.get(columns["origin_code"]))
                    if origin_code not in wanted_origins:
                        continue

                    destination_code = normalize_istat_code(
                        row.get(columns["destination_code"])
                    )
                    if destination_code not in wanted_services:
                        continue

                    try:
                        minutes = _as_float(row.get(columns["time"], ""))
                    except (TypeError, ValueError):
                        continue

                    distance = None
                    if "distance" in columns:
                        try:
                            distance = _as_float(row.get(columns["distance"], ""))
                        except (TypeError, ValueError):
                            distance = None

                    candidate = AccessibilityResult(
                        municipality=wanted_origins[origin_code],
                        service_municipality=wanted_services[destination_code],
                        travel_time_minutes=minutes,
                        distance_km=distance,
                    )

                    previous = best.get(origin_code)
                    if previous is None or minutes < previous.travel_time_minutes:
                        best[origin_code] = candidate

    if not parsed_any_csv:
        raise ValueError(
            "No ISTAT matrix CSV had the expected PROCOM/TEP_TOT schema. "
            + " | ".join(schema_errors[:5])
        )

    missing = sorted(
        name
        for code, name in wanted_origins.items()
        if code not in best
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
