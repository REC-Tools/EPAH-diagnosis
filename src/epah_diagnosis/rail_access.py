from __future__ import annotations

import re
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser


RFI_STATIONS_URL = "https://www.rfi.it/it/stazioni.html"

PIEMONTE_PROVINCES = {
    "alessandria",
    "asti",
    "biella",
    "cuneo",
    "novara",
    "torino",
    "verbano-cusio-ossola",
    "vercelli",
}

VALID_CLASSES = {
    "MAIN HUB",
    "HUB",
    "MAJOR",
    "PLUS",
    "LOCAL PLUS",
    "LOCAL",
}


@dataclass(frozen=True)
class RfiStation:
    station_name: str
    municipality: str
    province: str
    classification: str


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_cell = False
        self.in_row = False
        self.cell_parts: list[str] = []
        self.row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "tr":
            self.in_row = True
            self.row = []
        elif tag in {"td", "th"} and self.in_row:
            self.in_cell = True
            self.cell_parts = []

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self.in_cell:
            value = " ".join("".join(self.cell_parts).split())
            self.row.append(value)
            self.in_cell = False
            self.cell_parts = []
        elif tag == "tr" and self.in_row:
            if self.row:
                self.rows.append(self.row)
            self.in_row = False
            self.row = []


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


def parse_rfi_stations_html(html: str) -> list[RfiStation]:
    parser = _TableParser()
    parser.feed(html)

    stations: list[RfiStation] = []
    header: list[str] | None = None

    for row in parser.rows:
        normalized = [_norm(value) for value in row]

        if (
            "stazione" in normalized
            and "comune" in normalized
            and "provincia" in normalized
            and "classificazione" in normalized
        ):
            header = normalized
            continue

        if header is None or len(row) < len(header):
            continue

        values = {
            header[index]: row[index]
            for index in range(min(len(header), len(row)))
        }

        province = values.get("provincia", "").strip()
        classification = values.get("classificazione", "").strip().upper()
        municipality = values.get("comune", "").strip()
        station_name = values.get("stazione", "").strip()

        if not station_name or not municipality or not province:
            continue
        if classification not in VALID_CLASSES:
            continue
        if _norm(province) not in PIEMONTE_PROVINCES:
            continue

        stations.append(
            RfiStation(
                station_name=station_name,
                municipality=municipality,
                province=province,
                classification=classification,
            )
        )

    if not stations:
        raise ValueError(
            "No Piemonte RFI stations parsed from station catalogue HTML."
        )

    return stations


def download_rfi_stations(url: str = RFI_STATIONS_URL) -> list[RfiStation]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 EPAH-diagnosis/1.0",
            "Accept": "text/html,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        html = response.read().decode("utf-8", errors="replace")
    return parse_rfi_stations_html(html)


def station_municipalities(stations: list[RfiStation]) -> set[str]:
    return {station.municipality for station in stations}
