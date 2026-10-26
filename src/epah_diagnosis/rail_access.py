from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RailGateway:
    station_name: str
    municipality: str
    province: str
    status: str
    source: str
    source_url: str
    notes: str


def load_rail_gateways(path: Path) -> list[RailGateway]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    gateways: list[RailGateway] = []
    for row in rows:
        municipality = (row.get("municipality") or "").strip()
        station_name = (row.get("station_name") or "").strip()
        status = (row.get("status") or "").strip()

        if not municipality or not station_name:
            continue
        if "active passenger rail" not in status.casefold():
            continue

        gateways.append(
            RailGateway(
                station_name=station_name,
                municipality=municipality,
                province=(row.get("province") or "").strip(),
                status=status,
                source=(row.get("source") or "").strip(),
                source_url=(row.get("source_url") or "").strip(),
                notes=(row.get("notes") or "").strip(),
            )
        )

    if not gateways:
        raise ValueError("No active rail gateways found in reference snapshot.")

    return gateways


def station_municipalities(gateways: list[RailGateway]) -> set[str]:
    return {gateway.municipality for gateway in gateways}
