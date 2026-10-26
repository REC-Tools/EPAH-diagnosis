from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from epah_diagnosis.municipality_profile import REQUIRED_INDICATORS
from epah_diagnosis.cli import read_municipalities


ROOT = Path(__file__).resolve().parents[1]
MATRIX_FILE = ROOT / "data" / "verification_matrix.csv"


def main() -> None:
    with MATRIX_FILE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    expected_names = read_municipalities(ROOT / "data" / "municipalities.csv")
    if len(expected_names) != 27:
        raise ValueError(f"Expected 27 municipalities; got {len(expected_names)}")
    expected = set(expected_names)
    by_municipality: dict[str, dict[str, str]] = defaultdict(dict)
    duplicate_keys: set[tuple[str, str]] = set()
    unexpected_names: set[str] = set()
    for row in rows:
        municipality = row["municipality"].strip()
        indicator_id = row["indicator_id"].strip()
        if municipality not in expected:
            unexpected_names.add(municipality)
        if indicator_id in REQUIRED_INDICATORS:
            if indicator_id in by_municipality[municipality]:
                duplicate_keys.add((municipality, indicator_id))
            by_municipality[municipality][indicator_id] = row["status"].strip()

    missing_by_indicator: dict[str, list[str]] = defaultdict(list)
    not_validated_by_indicator: dict[str, list[str]] = defaultdict(list)

    for municipality in sorted(expected):
        statuses = by_municipality[municipality]
        for indicator_id in REQUIRED_INDICATORS:
            if indicator_id not in statuses:
                missing_by_indicator[indicator_id].append(municipality)
            elif statuses[indicator_id] != "Dato validato":
                not_validated_by_indicator[indicator_id].append(municipality)

    print("Integrated profile readiness")
    print("============================")

    if not missing_by_indicator and not not_validated_by_indicator and not duplicate_keys and not unexpected_names:
        print("READY: all required indicators are validated for every municipality.")
        return

    if duplicate_keys:
        print("\\nDuplicate municipality-indicator rows:")
        for name, indicator in sorted(duplicate_keys):
            print(f"- {name}: {indicator}")

    if unexpected_names:
        print("\\nUnexpected municipalities: " + ", ".join(sorted(unexpected_names)))

    if missing_by_indicator:
        print("\nMissing indicators:")
        for indicator_id in REQUIRED_INDICATORS:
            municipalities = missing_by_indicator.get(indicator_id)
            if municipalities:
                print(
                    f"- {indicator_id}: {len(municipalities)} municipalities "
                    f"(e.g. {', '.join(municipalities[:5])})"
                )

    if not_validated_by_indicator:
        print("\nPresent but not validated:")
        for indicator_id in REQUIRED_INDICATORS:
            municipalities = not_validated_by_indicator.get(indicator_id)
            if municipalities:
                print(
                    f"- {indicator_id}: {len(municipalities)} municipalities "
                    f"(e.g. {', '.join(municipalities[:5])})"
                )

    print("\nSuggested finalizers:")
    suggestions = {
        "population_65_plus": "finalize_population_65_plus.py",
        "income_vulnerability": "finalize_mef_income.py",
        "old_building_stock": "finalize_building_stock_single_source.py",
        "heating_degree_days": "finalize_heating_degree_days.py",
        "mean_altitude": "finalize_mean_altitude.py",
        "snai_classification": "finalize_snai_classification.py",
        "dea_accessibility": "finalize_dea_accessibility.py",
        "upper_secondary_accessibility": "finalize_upper_secondary_accessibility.py",
        "rail_accessibility": "finalize_rail_accessibility.py",
    }

    affected = set(missing_by_indicator) | set(not_validated_by_indicator)
    for indicator_id in REQUIRED_INDICATORS:
        if indicator_id in affected:
            script = suggestions.get(indicator_id)
            if script:
                print(f"- python scripts/{script}")

    raise SystemExit(1)


if __name__ == "__main__":
    main()
