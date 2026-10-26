from __future__ import annotations

import csv
import io
import re
import shutil
import subprocess
import tempfile
import unicodedata
import urllib.request
from dataclasses import dataclass
from pathlib import Path


PIEMONTE_CSV_URL = (
    "https://ottomilacensus.istat.it/fileadmin/download/01/confini/confini_01.csv"
)

HISTORIC_CODE = "A10"
POOR_CONDITION_CODE = "A9"


@dataclass(frozen=True)
class BuildingStock:
    municipality_code: str
    municipality: str
    historic_occupied_dwellings_pct: float
    poor_condition_buildings_pct: float


def _norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _to_float(value: str | None) -> float | None:
    if value is None:
        return None
    cleaned = value.strip().replace(",", ".")
    if cleaned in {"", "-", "..", "...", "...."}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _detect_dialect(text: str):
    sample = text[:10000]
    return csv.Sniffer().sniff(sample, delimiters=";,\t")


def _find_col(fields: list[str | None], candidates: tuple[str, ...]) -> str:
    normalized = {
        _norm(name): name for name in fields if name is not None and name.strip()
    }
    for candidate in candidates:
        key = _norm(candidate)
        if key in normalized:
            return normalized[key]
    raise ValueError(f"Missing expected column {candidates}. Got: {fields}")


def _find_indicator_col(fields: list[str | None], code: str) -> str:
    wanted = _norm(code)
    exact = [
        name for name in fields
        if name is not None and _norm(name) == wanted
    ]
    if exact:
        return exact[0]

    starts = [
        name for name in fields
        if name is not None and _norm(name).startswith(wanted)
    ]
    if len(starts) == 1:
        return starts[0]

    raise ValueError(f"Cannot identify indicator column {code}. Got: {fields}")


def parse_regional_csv(text: str) -> list[BuildingStock]:
    dialect = _detect_dialect(text)
    rows = list(csv.DictReader(io.StringIO(text), dialect=dialect))
    if not rows:
        raise ValueError("ISTAT 8milaCensus regional CSV is empty.")

    fields = list(rows[0].keys())

    code_col = _find_col(
        fields,
        ("PRO_COM_T", "Codice Comune", "Codice Istat Comune", "COD_COM", "COMUNE"),
    )
    name_col = _find_col(
        fields,
        ("Comune", "Denominazione Comune", "DEN_COM", "COMUNE_DES"),
    )
    year_col = _find_col(
        fields,
        ("Anno", "ANNO", "Censimento", "ANNO_CENSIMENTO"),
    )
    a9_col = _find_indicator_col(fields, POOR_CONDITION_CODE)
    a10_col = _find_indicator_col(fields, HISTORIC_CODE)

    output: list[BuildingStock] = []
    for row in rows:
        year = (row.get(year_col) or "").strip()
        if year != "2011":
            continue

        code = (row.get(code_col) or "").strip()
        municipality = (row.get(name_col) or "").strip()
        if not code or not municipality:
            continue

        historic = _to_float(row.get(a10_col))
        poor = _to_float(row.get(a9_col))
        if historic is None or poor is None:
            continue

        if not 0 <= historic <= 100:
            raise ValueError(f"Invalid A10 value for {municipality}: {historic}")
        if not 0 <= poor <= 100:
            raise ValueError(f"Invalid A9 value for {municipality}: {poor}")

        # Normalize numeric municipality identifiers to six digits where possible.
        digits = re.sub(r"\D", "", code)
        if digits:
            code = digits.zfill(6)[-6:]

        output.append(
            BuildingStock(
                municipality_code=code,
                municipality=municipality,
                historic_occupied_dwellings_pct=historic,
                poor_condition_buildings_pct=poor,
            )
        )

    if not output:
        raise ValueError(
            "No 2011 municipal building-stock rows parsed. "
            f"Detected fields: {fields}"
        )
    return output


def _download_with_urllib(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 EPAH-diagnosis/1.0",
            "Accept": "text/csv,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def _download_with_curl(url: str) -> bytes:
    curl = shutil.which("curl") or shutil.which("curl.exe")
    if not curl:
        raise RuntimeError("curl is not available.")

    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "confini_01.csv"
        completed = subprocess.run(
            [
                curl,
                "-L",
                "--fail",
                "--silent",
                "--show-error",
                "--tlsv1.2",
                "-A",
                "Mozilla/5.0 EPAH-diagnosis/1.0",
                "-o",
                str(output),
                url,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "curl download failed.")
        return output.read_bytes()


def download_regional_csv(url: str = PIEMONTE_CSV_URL) -> list[BuildingStock]:
    errors: list[str] = []
    raw: bytes | None = None

    try:
        raw = _download_with_urllib(url)
    except Exception as exc:
        errors.append(f"urllib: {exc}")

    if raw is None:
        try:
            raw = _download_with_curl(url)
        except Exception as exc:
            errors.append(f"curl: {exc}")

    if raw is None:
        raise RuntimeError(
            "Unable to download ISTAT 8milaCensus Piemonte CSV. "
            "Download it manually from the official 8milaCensus Download page "
            "and rerun with --input <path>. Details: " + " | ".join(errors)
        )

    for encoding in ("utf-8-sig", "latin-1"):
        try:
            return parse_regional_csv(raw.decode(encoding))
        except UnicodeDecodeError:
            continue

    raise ValueError("Unable to decode ISTAT 8milaCensus regional CSV.")


def read_regional_file(path: Path) -> list[BuildingStock]:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            return parse_regional_csv(raw.decode(encoding))
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Unable to decode {path}.")


def filter_municipalities(
    data: list[BuildingStock],
    municipality_names: set[str],
) -> list[BuildingStock]:
    wanted = {_norm(name): name for name in municipality_names}
    selected = [item for item in data if _norm(item.municipality) in wanted]

    found = {_norm(item.municipality) for item in selected}
    missing = sorted(name for key, name in wanted.items() if key not in found)
    if missing:
        raise ValueError(
            "Municipalities not found in 8milaCensus regional CSV: "
            + ", ".join(missing)
        )

    if len(selected) != len(municipality_names):
        raise ValueError(
            f"Expected {len(municipality_names)} municipalities, found {len(selected)} rows."
        )
    return selected
