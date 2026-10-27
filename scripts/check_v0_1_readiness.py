from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

from epah_diagnosis.cli import read_municipalities


ROOT = Path(__file__).resolve().parents[1]
RELEASE_CONFIG = ROOT / "config" / "release_v0_1.json"
MATRIX_FILE = ROOT / "data" / "verification_matrix.csv"
MUNICIPALITIES_FILE = ROOT / "data" / "municipalities.csv"


def evaluate(
    matrix_file: Path = MATRIX_FILE,
    municipalities_file: Path = MUNICIPALITIES_FILE,
    release_config: Path = RELEASE_CONFIG,
) -> dict:
    release = json.loads(release_config.read_text(encoding="utf-8"))
    municipalities = read_municipalities(municipalities_file)
    expected = set(municipalities)
    core = tuple(release["core_indicators"])

    if len(municipalities) != release["release_criteria"]["municipalities"]:
        raise ValueError(
            f"Expected {release['release_criteria']['municipalities']} municipalities, "
            f"found {len(municipalities)}."
        )

    with matrix_file.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    indexed: dict[tuple[str, str], dict[str, str]] = {}
    duplicates: list[tuple[str, str]] = []

    for row in rows:
        municipality = row["municipality"].strip()
        indicator_id = row["indicator_id"].strip()
        key = (municipality, indicator_id)
        if key in indexed:
            duplicates.append(key)
        indexed[key] = row

    missing: dict[str, list[str]] = defaultdict(list)
    unvalidated: dict[str, list[str]] = defaultdict(list)
    empty_values: dict[str, list[str]] = defaultdict(list)

    for indicator_id in core:
        for municipality in municipalities:
            row = indexed.get((municipality, indicator_id))
            if row is None:
                missing[indicator_id].append(municipality)
                continue
            if row["status"].strip() != "Dato validato":
                unvalidated[indicator_id].append(municipality)
            if not row["value"].strip():
                empty_values[indicator_id].append(municipality)

    unexpected_municipalities = sorted(
        {
            row["municipality"].strip()
            for row in rows
            if row["municipality"].strip() not in expected
        }
    )

    extension_status = []
    for extension in release["extensions"]:
        indicator_id = extension["id"]
        if indicator_id == "local_energy_affordability":
            ids = (
                "inability_keep_home_warm",
                "utility_bill_arrears",
                "inability_keep_home_cool",
                "reduced_heating_for_cost",
            )
        else:
            ids = (indicator_id,)

        matching = [
            row
            for row in rows
            if row["indicator_id"].strip() in ids
            and row["municipality"].strip() in expected
        ]
        counts: dict[str, int] = defaultdict(int)
        for row in matching:
            counts[row["status"].strip()] += 1

        extension_status.append(
            {
                "id": indicator_id,
                "stage": extension["stage"],
                "blocking": bool(extension["blocking"]),
                "dependency": extension["dependency"],
                "rows_present": len(matching),
                "status_counts": dict(sorted(counts.items())),
            }
        )

    blockers = {
        "duplicates": [list(item) for item in sorted(set(duplicates))],
        "unexpected_municipalities": unexpected_municipalities,
        "missing_core": dict(missing),
        "unvalidated_core": dict(unvalidated),
        "empty_core_values": dict(empty_values),
    }
    ready = not any(
        (
            blockers["duplicates"],
            blockers["unexpected_municipalities"],
            blockers["missing_core"],
            blockers["unvalidated_core"],
            blockers["empty_core_values"],
        )
    )

    return {
        "release": release["release"],
        "ready": ready,
        "municipalities": len(municipalities),
        "core_indicators": len(core),
        "core_checks_expected": len(municipalities) * len(core),
        "blockers": blockers,
        "extensions": extension_status,
    }


def main() -> None:
    result = evaluate()

    print(f"EPAH Diagnosis v{result['release']} readiness")
    print("=" * 42)
    print(
        f"Core: {result['municipalities']} municipalities x "
        f"{result['core_indicators']} indicators = "
        f"{result['core_checks_expected']} checks"
    )

    if result["ready"]:
        print("READY: v0.1 core release criteria are satisfied.")
    else:
        print("NOT READY: blocking core issues remain.")
        for name, value in result["blockers"].items():
            if value:
                print(f"- {name}: {value}")

    print("\nNon-blocking extensions:")
    for extension in result["extensions"]:
        print(
            f"- {extension['id']}: {extension['stage']} "
            f"(rows={extension['rows_present']})"
        )

    if not result["ready"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
