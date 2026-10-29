from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from epah_diagnosis.matrix_update import upsert_indicator_rows

from epah_diagnosis.climate import load_reference, summarize
from epah_diagnosis.climate_verification import approve_with_evidence, compare_reference
from epah_diagnosis.priority_source_audit import compare_current_annex


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_FILE = ROOT / "data" / "reference" / "climate_dpr412_green_community.csv"
HISTORICAL_FILE = ROOT / "data" / "reference" / "climate_dpr412_official_2008_transcription.csv"
MATRIX_FILE = ROOT / "data" / "verification_matrix.csv"
OUTPUT_FILE = ROOT / "data" / "indicators" / "heating_degree_days.csv"
BENCHMARK_FILE = ROOT / "data" / "indicators" / "heating_degree_days_summary.csv"

INDICATOR_ID = "heating_degree_days"
INDICATOR_NAME = "Gradi-giorno di riscaldamento"
SOURCE_URL = (
    "https://def.giustiziatributaria.gov.it/DocTribFrontend/"
    "getAttoNormativoDetail.do?ACTION=getArticolo&articolo=Allegato+A"
    "&codiceOrdinamento=60A+++++0000000"
    "&id=%7B0E4DC3BD-3B00-45E2-9CA6-B4DECB631C36%7D"
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Promote climate data only after documented review of current Annex A"
    )
    parser.add_argument(
        "--official-html", type=Path, required=True,
        help="Saved full official consolidated 2016 Annex A HTML, not search snippets"
    )
    parser.add_argument(
        "--approved-evidence", type=Path, required=True,
        help="Human review JSON for the consolidated 2016 Annex A"
    )
    args = parser.parse_args()

    # Fail before writing any dataset or matrix. A historical cross-check
    # alone does not certify the legally current Annex A.
    official = compare_current_annex(
        args.official_html.read_bytes(), REFERENCE_FILE,
        ROOT / "data/municipalities.csv",
    )
    if not official["technical_crosscheck_passed"]:
        raise ValueError(
            "Official consolidated Annex A 2016 is not identical for all 27 municipalities: "
            + str(official["missing_municipalities"] or official["differences"])
        )
    raw_review = json.loads(args.approved_evidence.read_text(encoding="utf-8"))
    if (raw_review.get("official_annex_sha256") != official["official_file_sha256"]
            or raw_review.get("official_annex_rows_verified") != 27):
        raise ValueError("Human review must reference the exact 27-row official Annex A HTML SHA-256")
    comparison = compare_reference(REFERENCE_FILE, HISTORICAL_FILE)
    approval = approve_with_evidence(comparison, args.approved_evidence)
    records = load_reference(REFERENCE_FILE)
    summary = summarize(records)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "municipality",
                "climate_zone",
                "heating_degree_days",
                "municipal_seat_altitude_m",
                "source",
                "source_url",
                "quality",
                "limitations",
            ],
        )
        writer.writeheader()
        for record in sorted(records, key=lambda item: item.municipality):
            writer.writerow(
                {
                    "municipality": record.municipality,
                    "climate_zone": record.climate_zone,
                    "heating_degree_days": record.heating_degree_days,
                    "municipal_seat_altitude_m": record.municipal_seat_altitude_m,
                    "source": "DPR 412/1993 - Allegato A",
                    "source_url": SOURCE_URL,
                    "quality": (
                        "Classificazione normativa nazionale per Comune; "
                        "valore statico di riferimento."
                    ),
                    "limitations": (
                        "I gradi-giorno normativi sono un indicatore climatico "
                        "convenzionale e non rappresentano il consumo energetico "
                        "reale né la temperatura osservata nell'anno corrente."
                    ),
                }
            )

    with BENCHMARK_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "territory",
                "municipality_count",
                "zone_f_count",
                "zone_e_count",
                "mean_heating_degree_days",
                "median_heating_degree_days",
                "min_heating_degree_days",
                "max_heating_degree_days",
                "method",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "territory": "Green Community Sinergie in Canavese",
                **summary,
                "method": (
                    "Unweighted descriptive summary of municipal DPR 412/1993 "
                    "heating degree days; no population weighting."
                ),
            }
        )

    with MATRIX_FILE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    original_count = len(rows)


    for record in records:
        key = record.municipality.casefold()
        rows.append(
            {
                "municipality": record.municipality,
                "indicator_id": INDICATOR_ID,
                "indicator_name": INDICATOR_NAME,
                "macro_area": "Climate",
                "status": "Dato validato",
                "source_priority": "DPR 412/1993 - Allegato A",
                "year": "normativo",
                "territorial_level": "Comune",
                "unit": "GG",
                "source_url": SOURCE_URL,
                "value": str(record.heating_degree_days),
                "quality": (
                    "Confronto storico 27/27 e revisione umana Allegato A 2016; "
                    f"zona climatica {record.climate_zone}"
                ),
                "limitations": (
                    "Indicatore climatico convenzionale; non misura consumi "
                    "energetici reali o condizioni meteorologiche annuali"
                ),
                "notes": (
                    f"Zona climatica {record.climate_zone}; "
                    f"quota snapshot casa comunale {record.municipal_seat_altitude_m} m; "
                    f"evidence: {approval['review_evidence_url']}"
                ),
            }
        )

    upsert_indicator_rows(MATRIX_FILE, INDICATOR_ID, rows[original_count:])

    print("Validated 27 municipal heating-degree-day records.")
    print(
        f"Zone F: {summary['zone_f_count']} / 27; "
        f"Zone E: {summary['zone_e_count']} / 27"
    )
    print(
        "Green Community heating degree days: "
        f"mean {summary['mean_heating_degree_days']:.2f}; "
        f"median {summary['median_heating_degree_days']:.2f}; "
        f"range {summary['min_heating_degree_days']}-"
        f"{summary['max_heating_degree_days']}"
    )


if __name__ == "__main__":
    main()
