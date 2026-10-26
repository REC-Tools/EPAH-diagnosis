from __future__ import annotations

import csv
import io
import re
import unicodedata
import urllib.request
import zipfile
from pathlib import Path
from epah_diagnosis.matrix_update import upsert_indicator_rows

from epah_diagnosis.istat_building_stock import (
    CPA_2011_URL,
    filter_by_codes,
    is_piemonte,
    parse_cpa_zip,
    weighted_share_pre_1981,
)

ROOT = Path(__file__).resolve().parents[1]
MUNICIPALITIES_FILE = ROOT / "data" / "municipalities.csv"
MATRIX_FILE = ROOT / "data" / "verification_matrix.csv"
OUTPUT_FILE = ROOT / "data" / "indicators" / "building_stock_2011.csv"
BENCHMARK_FILE = ROOT / "data" / "indicators" / "building_stock_benchmarks_2011.csv"
SOURCE_PAGE = "https://www.istat.it/notizia/basi-territoriali-e-variabili-censuarie/"
YEAR = "2011"
INDICATOR_ID = "old_building_stock"

def norm_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", value.casefold())

def norm_code(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    return digits.zfill(6)[-6:]

def read_target_municipalities() -> set[str]:
    with MUNICIPALITIES_FILE.open(encoding="utf-8", newline="") as handle:
        return {row["municipality"].strip() for row in csv.DictReader(handle) if row["municipality"].strip()}

def download_payload() -> bytes:
    request = urllib.request.Request(
        CPA_2011_URL,
        headers={"User-Agent": "Mozilla/5.0 EPAH-diagnosis/1.0"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()

def extract_name_code_map(payload: bytes) -> dict[str, tuple[str, str]]:
    mapping: dict[str, tuple[str, str]] = {}
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for name in archive.namelist():
            if not (name.lower().endswith(".csv") and "indicatori_2011_sezioni" in name.lower()):
                continue
            text = archive.read(name).decode("latin-1")
            reader = csv.DictReader(io.StringIO(text), delimiter=";")
            if not reader.fieldnames:
                continue
            fields = {field.upper(): field for field in reader.fieldnames}
            if "PROCOM" not in fields or "COMUNE" not in fields:
                continue
            for row in reader:
                municipality = (row.get(fields["COMUNE"]) or "").strip()
                code = norm_code(row.get(fields["PROCOM"]) or "")
                if municipality and code:
                    mapping[norm_name(municipality)] = (code, municipality)
    if not mapping:
        raise ValueError("No COMUNE/PROCOM mapping found in ISTAT CPA archive.")
    return mapping

def main() -> None:
    target_names = read_target_municipalities()
    print("Downloading official ISTAT 2011 census-section variables...")
    payload = download_payload()
    all_municipalities = parse_cpa_zip(payload)
    name_code_map = extract_name_code_map(payload)

    target_codes: set[str] = set()
    display_name_by_code: dict[str, str] = {}
    missing: list[str] = []
    for municipality in sorted(target_names):
        match = name_code_map.get(norm_name(municipality))
        if match is None:
            missing.append(municipality)
            continue
        code, _ = match
        target_codes.add(code)
        display_name_by_code[code] = municipality
    if missing:
        raise ValueError("Target municipalities not found in CPA 2011 archive: " + ", ".join(missing))
    if len(target_codes) != len(target_names):
        raise ValueError("Duplicate municipality code mappings in CPA 2011 archive")

    records = filter_by_codes(all_municipalities, target_codes)
    if len(records) != len(target_names):
        raise ValueError(f"Incomplete census stock coverage: {len(records)}/{len(target_names)}")
    piemonte = [item for item in all_municipalities if is_piemonte(item.municipality_code)]
    if not piemonte:
        raise ValueError("No Piemonte municipalities in ISTAT CPA dataset")
    gc_share = weighted_share_pre_1981(records)
    piemonte_share = weighted_share_pre_1981(piemonte)
    italy_share = weighted_share_pre_1981(all_municipalities)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as handle:
        fields = [
            "municipality_code","municipality","year","residential_buildings_total",
            "buildings_pre_1981","share_pre_1981_pct","buildings_pre_1919",
            "buildings_1919_1945","buildings_1946_1960","buildings_1961_1970",
            "buildings_1971_1980","buildings_1981_1990","buildings_1991_2000",
            "buildings_2001_2005","buildings_after_2005",
            "green_community_share_pre_1981_pct","piemonte_share_pre_1981_pct",
            "italy_share_pre_1981_pct","source","source_url","quality","limitations"
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in sorted(records, key=lambda x: display_name_by_code[x.municipality_code]):
            writer.writerow({
                "municipality_code": item.municipality_code,
                "municipality": display_name_by_code[item.municipality_code],
                "year": YEAR,
                "residential_buildings_total": item.residential_buildings_total,
                "buildings_pre_1981": item.buildings_pre_1981,
                "share_pre_1981_pct": f"{item.share_pre_1981:.2f}",
                "buildings_pre_1919": item.buildings_pre_1919,
                "buildings_1919_1945": item.buildings_1919_1945,
                "buildings_1946_1960": item.buildings_1946_1960,
                "buildings_1961_1970": item.buildings_1961_1970,
                "buildings_1971_1980": item.buildings_1971_1980,
                "buildings_1981_1990": item.buildings_1981_1990,
                "buildings_1991_2000": item.buildings_1991_2000,
                "buildings_2001_2005": item.buildings_2001_2005,
                "buildings_after_2005": item.buildings_after_2005,
                "green_community_share_pre_1981_pct": f"{gc_share:.2f}",
                "piemonte_share_pre_1981_pct": f"{piemonte_share:.2f}",
                "italy_share_pre_1981_pct": f"{italy_share:.2f}",
                "source": "ISTAT - Variabili censuarie CPA 2011",
                "source_url": CPA_2011_URL,
                "quality": "Fonte ufficiale ISTAT; sezioni censuarie aggregate a Comune.",
                "limitations": "Baseline 2011; epoca di costruzione come proxy.",
            })

    with BENCHMARK_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "territory","year","residential_buildings_total","buildings_pre_1981",
            "share_pre_1981_pct","method","source_url"
        ])
        writer.writeheader()
        for territory, items in (
            ("Green Community Sinergie in Canavese", records),
            ("Piemonte", piemonte),
            ("Italia", all_municipalities),
        ):
            writer.writerow({
                "territory": territory,
                "year": YEAR,
                "residential_buildings_total": sum(i.residential_buildings_total for i in items),
                "buildings_pre_1981": sum(i.buildings_pre_1981 for i in items),
                "share_pre_1981_pct": f"{weighted_share_pre_1981(items):.2f}",
                "method": "Somma E8:E12 / somma E3",
                "source_url": CPA_2011_URL,
            })

    by_name = {display_name_by_code[item.municipality_code].casefold(): item for item in records}
    with MATRIX_FILE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0].keys())

    updated = 0
    for row in rows:
        if row["indicator_id"] != INDICATOR_ID:
            continue
        item = by_name.get(row["municipality"].casefold())
        if item is None:
            raise ValueError(f"Missing building-stock result for {row['municipality']}")
        row["status"] = "Dato validato"
        row["year"] = YEAR
        row["territorial_level"] = "Comune"
        row["unit"] = "%"
        row["source_url"] = SOURCE_PAGE
        row["value"] = f"{item.share_pre_1981:.2f}"
        row["quality"] = "Fonte ufficiale ISTAT; sezioni 2011 aggregate a Comune"
        row["limitations"] = "Baseline 2011; quota edifici residenziali pre-1981 come proxy"
        row["notes"] = (
            f"Edifici pre-1981: {item.buildings_pre_1981}; "
            f"edifici residenziali totali: {item.residential_buildings_total}; "
            "formula=(E8+E9+E10+E11+E12)/E3"
        )
        updated += 1

    if updated != 27:
        raise ValueError(f"Expected 27 updates, got {updated}.")

    # Commit only the target indicator rows; preserve other dimensions unchanged.
    upsert_indicator_rows(
        MATRIX_FILE,
        INDICATOR_ID,
        [row for row in rows if row["indicator_id"] == INDICATOR_ID],
    )

    print("Validated 27 municipal building-stock checks.")
    print(f"Green Community residential buildings pre-1981: {gc_share:.2f}%")
    print(f"Piemonte residential buildings pre-1981: {piemonte_share:.2f}%")
    print(f"Italia residential buildings pre-1981: {italy_share:.2f}%")

if __name__ == "__main__":
    main()
