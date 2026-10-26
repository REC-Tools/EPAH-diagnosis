from __future__ import annotations

import csv
import statistics
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ClimateRecord:
    municipality: str
    province: str
    climate_zone: str
    heating_degree_days: int
    municipal_seat_altitude_m: int


def load_reference(path: Path) -> list[ClimateRecord]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    records: list[ClimateRecord] = []
    for row in rows:
        records.append(
            ClimateRecord(
                municipality=row["municipality"].strip(),
                province=row["province"].strip(),
                climate_zone=row["climate_zone"].strip().upper(),
                heating_degree_days=int(row["heating_degree_days"]),
                municipal_seat_altitude_m=int(row["municipal_seat_altitude_m"]),
            )
        )

    if len(records) != 27:
        raise ValueError(f"Expected 27 climate records, found {len(records)}.")

    names = [record.municipality for record in records]
    if len(set(names)) != len(names):
        raise ValueError("Duplicate municipality in climate reference.")

    for record in records:
        if record.climate_zone not in {"A", "B", "C", "D", "E", "F"}:
            raise ValueError(
                f"Invalid climate zone for {record.municipality}: "
                f"{record.climate_zone}"
            )
        if record.climate_zone == "F" and record.heating_degree_days <= 3000:
            raise ValueError(
                f"Zone F municipality with <=3000 GG: {record.municipality}"
            )
        if record.climate_zone == "E" and not (2100 < record.heating_degree_days <= 3000):
            raise ValueError(
                f"Zone E municipality outside 2101-3000 GG: {record.municipality}"
            )

    return records


def summarize(records: list[ClimateRecord]) -> dict[str, float | int]:
    values = [record.heating_degree_days for record in records]
    return {
        "municipality_count": len(records),
        "zone_f_count": sum(record.climate_zone == "F" for record in records),
        "zone_e_count": sum(record.climate_zone == "E" for record in records),
        "mean_heating_degree_days": round(statistics.mean(values), 2),
        "median_heating_degree_days": round(statistics.median(values), 2),
        "min_heating_degree_days": min(values),
        "max_heating_degree_days": max(values),
    }
