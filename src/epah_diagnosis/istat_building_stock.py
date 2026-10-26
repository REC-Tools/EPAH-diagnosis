from __future__ import annotations

import html
import re
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser


BASE_URL = "https://ottomilacensus.istat.it/sottotema/{province_code}/{municipality_code}/7/"
HISTORIC_LABEL = "Consistenza delle abitazioni storiche occupate"
POOR_CONDITION_LABEL = "Incidenza degli edifici in pessimo stato di conservazione"


@dataclass(frozen=True)
class BuildingStock:
    municipality_code: str
    municipality: str
    historic_occupied_dwellings_pct: float
    poor_condition_buildings_pct: float
    region_historic_pct: float | None = None
    italy_historic_pct: float | None = None
    region_poor_condition_pct: float | None = None
    italy_poor_condition_pct: float | None = None


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._in_cell = False
        self._current_cell: list[str] = []
        self._current_row: list[str] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "tr":
            self._current_row = []
        elif tag in {"td", "th"} and self._current_row is not None:
            self._in_cell = True
            self._current_cell = []

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._current_cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._in_cell and self._current_row is not None:
            value = html.unescape(" ".join(self._current_cell))
            value = re.sub(r"\s+", " ", value).strip()
            self._current_row.append(value)
            self._in_cell = False
            self._current_cell = []
        elif tag == "tr" and self._current_row is not None:
            if self._current_row:
                self.rows.append(self._current_row)
            self._current_row = None


def _to_float(value: str) -> float | None:
    cleaned = value.strip().replace(",", ".")
    if cleaned in {"", "-", "..", "...", "...."}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _find_indicator_rows(rows: list[list[str]], label: str) -> list[list[str]]:
    target = label.casefold()
    return [
        row
        for row in rows
        if row and row[0].strip().casefold() == target
    ]


def parse_building_stock_page(
    page_html: str,
    municipality_code: str,
    municipality: str,
) -> BuildingStock:
    parser = _TableParser()
    parser.feed(page_html)

    historic_rows = _find_indicator_rows(parser.rows, HISTORIC_LABEL)
    poor_rows = _find_indicator_rows(parser.rows, POOR_CONDITION_LABEL)

    if not historic_rows:
        raise ValueError(f"Historic dwellings row not found for {municipality}.")
    if not poor_rows:
        raise ValueError(f"Poor-condition buildings row not found for {municipality}.")

    # First matching row belongs to the 1991/2001/2011 time-series table.
    # The last cell is the 2011 value.
    historic_2011 = _to_float(historic_rows[0][-1])
    poor_2011 = _to_float(poor_rows[0][-1])

    if historic_2011 is None:
        raise ValueError(f"2011 historic dwellings value missing for {municipality}.")
    if poor_2011 is None:
        raise ValueError(f"2011 poor-condition value missing for {municipality}.")

    # The second matching row, when present, belongs to the territorial
    # comparison table: indicator | municipality | region | Italy.
    region_historic = italy_historic = None
    region_poor = italy_poor = None

    if len(historic_rows) >= 2 and len(historic_rows[1]) >= 4:
        region_historic = _to_float(historic_rows[1][-2])
        italy_historic = _to_float(historic_rows[1][-1])

    if len(poor_rows) >= 2 and len(poor_rows[1]) >= 4:
        region_poor = _to_float(poor_rows[1][-2])
        italy_poor = _to_float(poor_rows[1][-1])

    for value, field in (
        (historic_2011, "historic_occupied_dwellings_pct"),
        (poor_2011, "poor_condition_buildings_pct"),
    ):
        if not 0 <= value <= 100:
            raise ValueError(f"Invalid {field} for {municipality}: {value}")

    return BuildingStock(
        municipality_code=municipality_code,
        municipality=municipality,
        historic_occupied_dwellings_pct=historic_2011,
        poor_condition_buildings_pct=poor_2011,
        region_historic_pct=region_historic,
        italy_historic_pct=italy_historic,
        region_poor_condition_pct=region_poor,
        italy_poor_condition_pct=italy_poor,
    )


def municipality_url(municipality_code: str) -> str:
    code = municipality_code.strip()
    if len(code) != 6 or not code.isdigit():
        raise ValueError(f"Unexpected ISTAT municipality code: {municipality_code}")
    return BASE_URL.format(
        province_code=code[:3],
        municipality_code=code,
    )


def download_building_stock(
    municipality_code: str,
    municipality: str,
) -> BuildingStock:
    url = municipality_url(municipality_code)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 EPAH-diagnosis/1.0"},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        raw = response.read()

    for encoding in ("utf-8", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("utf-8", errors="replace")

    return parse_building_stock_page(text, municipality_code, municipality)
