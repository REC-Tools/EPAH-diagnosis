from __future__ import annotations

import csv
from pathlib import Path

from epah_diagnosis.local_affordability import (
    MIN_RESPONDENTS,
    filter_municipalities,
    parse_affordability_csv,
)


ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = ROOT / "data" / "raw" / "local_energy_affordability.csv"
MUNICIPALITIES_FILE = ROOT / "data" / "municipalities.csv"
MATRIX_FILE = ROOT / "data" / "verification_matrix.csv"
OUTPUT_FILE = ROOT / "data" / "indicators" / "local_energy_affordability.csv"
SUMMARY_FILE = ROOT / "data" / "indicators" / "local_energy_affordability_summary.csv"

SOURCE = "FERVORES / Green Community local anonymous aggregate survey"

INDICATORS = (
    (
        "inability_keep_home_warm",
        "Famiglie incapaci di mantenere l'abitazione adeguatamente calda",
        "unable_warm_yes",
    ),
    (
        "utility_bill_arrears",
        "Famiglie con arretrati sulle bollette energetiche",
        "utility_arrears_yes",
    ),
    (
        "inability_keep_home_cool",
        "Famiglie incapaci di mantenere l'abitazione adeguatamente fresca",
        "unable_cool_yes",
    ),
    (
        "reduced_heating_for_cost",
        "Famiglie che riducono il riscaldamento per motivi economici",
        "reduced_heating_cost_yes",
    ),
)


def read_target_municipalities() -> set[str]:
    with MUNICIPALITIES_FILE.open(encoding="utf-8", newline="") as handle:
        return {
            row["municipality"].strip()
            for row in csv.DictReader(handle)
            if row["municipality"].strip()
        }


def _read_input(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Unable to decode local affordability file.")


def main() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Missing local aggregate affordability file: {INPUT_FILE}. "
            "Fill the provided template using anonymous municipality-level "
            "counts before running this finalizer."
        )

    records = parse_affordability_csv(_read_input(INPUT_FILE))
    selected = filter_municipalities(records, read_target_municipalities())

    if len(selected) != 27:
        raise ValueError(
            f"Expected 27 municipality affordability records, found {len(selected)}."
        )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "municipality",
            "respondents",
            "unable_warm_yes",
            "inability_keep_home_warm_pct",
            "utility_arrears_yes",
            "utility_bill_arrears_pct",
            "unable_cool_yes",
            "inability_keep_home_cool_pct",
            "reduced_heating_cost_yes",
            "reduced_heating_for_cost_pct",
            "minimum_reporting_threshold",
            "suppressed",
            "source",
            "limitations",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        for item in selected:
            suppressed = item.respondents < MIN_RESPONDENTS
            writer.writerow(
                {
                    "municipality": item.municipality,
                    "respondents": item.respondents,
                    "unable_warm_yes": item.unable_warm_yes,
                    "inability_keep_home_warm_pct": (
                        "" if suppressed else f"{item.share('unable_warm_yes'):.2f}"
                    ),
                    "utility_arrears_yes": item.utility_arrears_yes,
                    "utility_bill_arrears_pct": (
                        "" if suppressed else f"{item.share('utility_arrears_yes'):.2f}"
                    ),
                    "unable_cool_yes": item.unable_cool_yes,
                    "inability_keep_home_cool_pct": (
                        "" if suppressed else f"{item.share('unable_cool_yes'):.2f}"
                    ),
                    "reduced_heating_cost_yes": item.reduced_heating_cost_yes,
                    "reduced_heating_for_cost_pct": (
                        ""
                        if suppressed
                        else f"{item.share('reduced_heating_cost_yes'):.2f}"
                    ),
                    "minimum_reporting_threshold": MIN_RESPONDENTS,
                    "suppressed": str(suppressed).lower(),
                    "source": SOURCE,
                    "limitations": (
                        "Local self-reported aggregate data. Results depend on "
                        "sampling and respondent composition; municipalities with "
                        f"fewer than {MIN_RESPONDENTS} respondents are suppressed."
                    ),
                }
            )

    eligible = [item for item in selected if item.respondents >= MIN_RESPONDENTS]
    total_respondents = sum(item.respondents for item in eligible)

    with SUMMARY_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "territory",
                "eligible_municipalities",
                "suppressed_municipalities",
                "respondents",
                "inability_keep_home_warm_pct",
                "utility_bill_arrears_pct",
                "inability_keep_home_cool_pct",
                "reduced_heating_for_cost_pct",
                "method",
            ],
        )
        writer.writeheader()

        def aggregate(field: str) -> str:
            if total_respondents <= 0:
                return ""
            numerator = sum(getattr(item, field) for item in eligible)
            return f"{numerator / total_respondents * 100:.2f}"

        writer.writerow(
            {
                "territory": "Green Community Sinergie in Canavese",
                "eligible_municipalities": len(eligible),
                "suppressed_municipalities": len(selected) - len(eligible),
                "respondents": total_respondents,
                "inability_keep_home_warm_pct": aggregate("unable_warm_yes"),
                "utility_bill_arrears_pct": aggregate("utility_arrears_yes"),
                "inability_keep_home_cool_pct": aggregate("unable_cool_yes"),
                "reduced_heating_for_cost_pct": aggregate(
                    "reduced_heating_cost_yes"
                ),
                "method": (
                    "Weighted aggregate across municipalities meeting the minimum "
                    f"reporting threshold of {MIN_RESPONDENTS} respondents."
                ),
            }
        )

    with MATRIX_FILE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0].keys())

    existing = {
        (row["municipality"].casefold(), row["indicator_id"])
        for row in rows
    }

    for item in selected:
        suppressed = item.respondents < MIN_RESPONDENTS

        for indicator_id, indicator_name, count_field in INDICATORS:
            key = (item.municipality.casefold(), indicator_id)
            if key in existing:
                continue

            value = item.share(count_field)

            rows.append(
                {
                    "municipality": item.municipality,
                    "indicator_id": indicator_id,
                    "indicator_name": indicator_name,
                    "macro_area": "Socio-economic",
                    "status": "Dato acquisito" if suppressed else "Dato validato",
                    "source_priority": "Local primary data",
                    "year": "",
                    "territorial_level": "Comune",
                    "unit": "%",
                    "source_url": "",
                    "value": "" if value is None else f"{value:.2f}",
                    "quality": (
                        f"Anonymous municipality aggregate; n={item.respondents}. "
                        + (
                            "Suppressed because minimum reporting threshold was "
                            f"not met ({MIN_RESPONDENTS})."
                            if suppressed
                            else "Minimum reporting threshold met."
                        )
                    ),
                    "limitations": (
                        "Self-reported local data; not population-representative "
                        "unless sampling is designed accordingly. Small-n results "
                        "are suppressed."
                    ),
                    "notes": (
                        "Direct affordability/thermal-comfort signal. Cross-read "
                        "with income, building efficiency, HDD/CDD and fuel mix."
                    ),
                }
            )

    with MATRIX_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(
        f"Processed 27 municipalities: {len(eligible)} reportable, "
        f"{len(selected) - len(eligible)} suppressed (n<{MIN_RESPONDENTS})."
    )
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
