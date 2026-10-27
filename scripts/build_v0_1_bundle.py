from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path

from epah_diagnosis.comparison import NUMERIC_DIMENSIONS, build_comparison_rows
from epah_diagnosis.mapping import write_enriched_geojson
from epah_diagnosis.municipality_profile import build_profiles

from check_v0_1_readiness import evaluate


ROOT = Path(__file__).resolve().parents[1]
MATRIX_FILE = ROOT / "data" / "verification_matrix.csv"
BOUNDARIES = ROOT / "data" / "geography" / "municipalities_2026.geojson"
OUTPUT_DIR = ROOT / "outputs" / "v0.1"


PROFILE_FIELDS = [
    "municipality",
    "population_65_plus_pct",
    "population_65_plus_year",
    "income_vulnerability_pct",
    "income_vulnerability_year",
    "old_building_stock_pct",
    "old_building_stock_year",
    "heating_degree_days",
    "heating_degree_days_year",
    "mean_altitude_m",
    "mean_altitude_year",
    "snai_class",
    "snai_year",
    "dea_access_minutes",
    "dea_access_year",
    "upper_secondary_access_minutes",
    "upper_secondary_access_year",
    "rail_access_minutes",
    "rail_access_year",
]


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_release_notes(readiness: dict) -> str:
    extension_lines = []
    for item in readiness["extensions"]:
        extension_lines.append(
            "- **" + item["id"] + "** — " + item["stage"]
            + "; dependency: " + item["dependency"]
        )
    extensions = "\n".join(extension_lines)

    return (
        "# EPAH Diagnosis v" + readiness["release"] + "\n\n"
        "This bundle is the first reproducible release candidate for the 27 "
        "municipalities of Green Community Sinergie in Canavese.\n\n"
        "## Core\n\n"
        "The v0.1 core contains " + str(readiness["core_indicators"])
        + " validated dimensions for all " + str(readiness["municipalities"])
        + " municipalities (" + str(readiness["core_checks_expected"])
        + " municipality-indicator checks).\n\n"
        "The release deliberately keeps dimensions separate. It does not "
        "calculate a single energy-poverty score and does not identify "
        "individual households.\n\n"
        "## Non-blocking extensions\n\n" + extensions + "\n\n"
        "## Files\n\n"
        "- municipality_profile.csv: integrated core profile.\n"
        "- municipality_comparison.csv: transparent per-dimension rankings.\n"
        "- municipality_profile.geojson: profile joined to ISTAT boundaries.\n"
        "- readiness.json: machine-readable release readiness.\n"
        "- release_manifest.json: generation metadata and caveats.\n"
    )


def main() -> None:
    readiness = evaluate()
    if not readiness["ready"]:
        raise RuntimeError(
            "v0.1 bundle cannot be built because core readiness is not satisfied. "
            "Run python scripts/check_v0_1_readiness.py for details."
        )

    if not BOUNDARIES.exists():
        raise FileNotFoundError(
            f"Missing official municipality boundaries: {BOUNDARIES}"
        )

    with MATRIX_FILE.open(encoding="utf-8", newline="") as handle:
        matrix_rows = list(csv.DictReader(handle))

    profiles = build_profiles(matrix_rows)
    comparison = build_comparison_rows(profiles)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    profile_path = OUTPUT_DIR / "municipality_profile.csv"
    comparison_path = OUTPUT_DIR / "municipality_comparison.csv"
    geojson_path = OUTPUT_DIR / "municipality_profile.geojson"

    write_csv(profile_path, PROFILE_FIELDS, profiles)

    comparison_fields = ["municipality", "snai_class"]
    for field, rank_field in NUMERIC_DIMENSIONS:
        comparison_fields.extend([field, rank_field])
    write_csv(comparison_path, comparison_fields, comparison)

    write_enriched_geojson(BOUNDARIES, profile_path, geojson_path)

    (OUTPUT_DIR / "readiness.json").write_text(
        json.dumps(readiness, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "release": readiness["release"],
        "generated_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "scope": "Green Community Sinergie in Canavese - 27 municipalities",
        "core": {
            "municipalities": readiness["municipalities"],
            "indicators": readiness["core_indicators"],
            "checks": readiness["core_checks_expected"],
        },
        "artifacts": [
            "municipality_profile.csv",
            "municipality_comparison.csv",
            "municipality_profile.geojson",
            "readiness.json",
            "release_manifest.json",
            "RELEASE_NOTES.md",
        ],
        "principles": [
            "No composite energy-poverty score.",
            "Municipality-level aggregates cannot identify energy-poor households.",
            "Each dimension retains source, year and methodological caveats.",
            "External-data extensions do not block the v0.1 core release.",
        ],
    }
    (OUTPUT_DIR / "release_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (OUTPUT_DIR / "RELEASE_NOTES.md").write_text(
        build_release_notes(readiness),
        encoding="utf-8",
    )

    print(f"Built EPAH Diagnosis v{readiness['release']} bundle.")
    print(f"Output directory: {OUTPUT_DIR}")
    for artifact in manifest["artifacts"]:
        print(f"- {OUTPUT_DIR / artifact}")


if __name__ == "__main__":
    main()
