"""Build a complete, fail-closed v0.1 diagnostic bundle from reviewed inputs.

No sample/demo mode. With the current unverified matrix this intentionally
refuses to build any public-looking release artifact.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from epah_diagnosis.cli import read_municipality_codes
from epah_diagnosis.comparison import NUMERIC_DIMENSIONS, build_comparison_rows
from epah_diagnosis.mapping import write_enriched_geojson
from epah_diagnosis.municipality_profile import build_profiles
from epah_diagnosis.release_artifacts import (
    MAP_SPECS, check_geojson, draw_maps, sha256_file,
    validate_bundle_contents, write_report, write_workbook,
)

from check_v0_1_readiness import evaluate


ROOT = Path(__file__).resolve().parents[1]
MATRIX_FILE = ROOT / "data/verification_matrix.csv"
REGISTRY_FILE = ROOT / "data/municipalities.csv"
CATALOG_FILE = ROOT / "config/indicators.json"
REVIEWS_FILE = ROOT / "config/release_reviews_v0_1.json"
RELEASE_CONFIG = ROOT / "config/release_v0_1.json"
BOUNDARIES = ROOT / "data/geography/municipalities_2026.geojson"
OUTPUT_DIR = ROOT / "outputs/v0.1"

PROFILE_FIELDS = [
    "municipality",
    "population_65_plus_pct", "population_65_plus_year",
    "income_vulnerability_pct", "income_vulnerability_year",
    "old_building_stock_pct", "old_building_stock_year",
    "heating_degree_days", "heating_degree_days_year",
    "mean_altitude_m", "mean_altitude_year",
    "snai_class", "snai_year",
    "dea_access_minutes", "dea_access_year",
    "upper_secondary_access_minutes", "upper_secondary_access_year",
    "rail_access_minutes", "rail_access_year",
]


def _write_csv(path: Path, names: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=names, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _release_notes(version: str) -> str:
    return f"""# EPAH Diagnosis v{version} - Sinergie in Canavese

## Scope
A reproducible, municipality-level *screening* for 27 municipalities.
Nine dimensions are kept separate; no composite energy-poverty score
or identification of vulnerable individuals is calculated.

## Scientific limitations
Indicator years differ. The 2011 building-stock share is a historic proxy,
not a current energy-performance certificate. TEP_TOT access times relate
to ISTAT 2021 municipal reference points and a 2020 road graph, not the
time from each home to a hospital, school or station. DEA, schools and
rail destinations may be based on curated regional snapshots.
SNAI A-F is categorical and must not be turned into a numeric risk score.

## Deliverables
- municipality_profile.csv: all 27 x 9 approved core observations.
- municipality_comparison.csv: eight separate numeric rankings plus SNAI class.
- municipality_profile.geojson: joined official ISTAT municipal shapes.
- maps/: eight continuous maps and one categorical SNAI map.
- completeness.xlsx: data, years, codes, matrix quality and provenance fields.
- diagnostic_report.pdf: narrative technical screening and source caveats.
- release_manifest.json: source-input and independent artifact SHA-256 hashes.
- readiness.json: final structural status of release inputs and artifacts.

## Review and reuse
The repository's source-specific QA and signed-off methodological reviews
must be verified separately. This bundle does not assert any EPAH certification.
"""


def build_bundle(
    *,
    matrix_file: Path = MATRIX_FILE,
    municipality_file: Path = REGISTRY_FILE,
    catalog_file: Path = CATALOG_FILE,
    reviews_file: Path = REVIEWS_FILE,
    release_config: Path = RELEASE_CONFIG,
    boundaries: Path = BOUNDARIES,
    output_dir: Path = OUTPUT_DIR,
    replace: bool = False,
) -> Path:
    """Generate, audit and atomically publish the entire release directory.

    A failed input or geometry check leaves an existing bundle untouched.
    No partial staging files are advertised as the finished bundle.
    """
    inputs = {
        "matrix": matrix_file,
        "municipality_registry": municipality_file,
        "indicator_catalog": catalog_file,
        "review_manifest": reviews_file,
        "release_config": release_config,
        "istat_boundaries": boundaries,
    }
    output_dir = output_dir.resolve()
    if output_dir.exists() and (not replace or not output_dir.is_dir()):
        raise FileExistsError(
            f"Release destination exists: {output_dir}. Use --replace only after reviewing the old bundle."
        )
    input_gate = evaluate(
        matrix_file=matrix_file, municipalities_file=municipality_file,
        catalog_file=catalog_file, reviews_file=reviews_file,
        release_config=release_config, output_dir=output_dir, phase="inputs",
    )
    if not input_gate["inputs_ready"]:
        blocked = [
            str(k) for k, values in input_gate["blockers"].items() if values
        ] + list(input_gate["review_blockers"])
        raise ValueError(
            "NOT READY: v0.1 source observations or methodological approvals "
            "are incomplete. Blocking groups: " + ", ".join(blocked)
        )
    for name, path in inputs.items():
        if not path.is_file():
            raise FileNotFoundError(f"Missing required {name}: {path}")
    registry = read_municipality_codes(municipality_file)
    if len(registry) != 27:
        raise ValueError("Exactly 27 six-digit ISTAT municipality codes required")
    boundary_geo = json.loads(boundaries.read_text(encoding="utf-8"))
    check_geojson(boundary_geo, registry)
    with matrix_file.open(encoding="utf-8", newline="") as f:
        matrix = list(csv.DictReader(f))
    if len(matrix) != 243:
        raise ValueError("Release requires exactly 243 distinct municipality-indicator rows")
    profiles = build_profiles(matrix)
    if set(item["municipality"] for item in profiles) != set(registry):
        raise ValueError("Integrated profile differs from canonical municipality registry")
    comparison = build_comparison_rows(profiles)
    catalog = json.loads(catalog_file.read_text(encoding="utf-8"))["indicators"]
    release = json.loads(release_config.read_text(encoding="utf-8"))
    required = release["required_artifacts"]
    expected = {
        "municipality_profile.csv", "municipality_comparison.csv",
        "municipality_profile.geojson", "readiness.json",
        "release_manifest.json", "RELEASE_NOTES.md",
        "completeness.xlsx", "diagnostic_report.pdf",
        *(f"maps/{spec[3]}" for spec in MAP_SPECS),
    }
    if set(required) != expected or len(required) != len(expected):
        raise ValueError("Release config artifact contract differs from the canonical v0.1 deliverables")

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".v0.1-stage-", dir=output_dir.parent) as td:
        work = Path(td)
        stage = work / "bundle"
        stage.mkdir()

        _write_csv(stage / "municipality_profile.csv", PROFILE_FIELDS, profiles)
        comparison_fields = ["municipality", "snai_class"]
        for numeric, rank in NUMERIC_DIMENSIONS:
            comparison_fields.extend([numeric, rank])
        _write_csv(stage / "municipality_comparison.csv", comparison_fields, comparison)
        enriched = write_enriched_geojson(
            boundaries, stage / "municipality_profile.csv",
            stage / "municipality_profile.geojson",
        )
        check_geojson(enriched, registry, enriched=True)
        draw_maps(enriched, stage / "maps")
        write_workbook(stage / "completeness.xlsx", profiles, comparison,
                       matrix, catalog, registry, input_gate)
        write_report(stage / "diagnostic_report.pdf", profiles, catalog, input_gate)
        (stage / "RELEASE_NOTES.md").write_text(
            _release_notes(release["release"]), encoding="utf-8",
        )

        # Do not hash the manifest itself or readiness.json; readiness is
        # finalized only after all artifacts, including the manifest, exist.
        hashes = {
            name: {"sha256": sha256_file(stage / name),
                   "bytes": (stage / name).stat().st_size}
            for name in required if name not in {"release_manifest.json", "readiness.json"}
        }
        manifest = {
            "release": release["release"],
            "generated_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
            "scope": "Green Community Sinergie in Canavese - 27 Comuni",
            "source_inputs": {
                name: {"file_name": path.name, "sha256": sha256_file(path)}
                for name, path in inputs.items()
            },
            "source_archive_provenance": (
                "Original archive retrieval is documented in source-specific "
                "indicator QA files, not authenticated by these input checksums."
            ),
            "artifacts": hashes,
            "not_self_hashed": ["release_manifest.json", "readiness.json"],
            "municipalities": 27,
            "core_indicators": 9,
            "observations": 243,
            "no_composite_score": True,
            "limitations": (
                "Municipal screening. Historical/mixed source years; no individual "
                "energy-poverty attribution. No current nationwide service proximity claim."
            ),
        }
        (stage / "release_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        # Readiness is initially present so the release artifact gate can
        # evaluate the full fileset. It is rewritten to the final release status.
        (stage / "readiness.json").write_text(
            json.dumps(input_gate, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        release_gate = evaluate(
            matrix_file=matrix_file, municipalities_file=municipality_file,
            catalog_file=catalog_file, reviews_file=reviews_file,
            release_config=release_config, output_dir=stage, phase="release",
        )
        if not release_gate["release_ready"]:
            raise ValueError("Release is NOT READY after artifact generation: "
                             + str(release_gate["artifact_blockers"]))
        (stage / "readiness.json").write_text(
            json.dumps(release_gate, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        validate_bundle_contents(stage, registry, required)

        backup = work / "previous-bundle"
        if output_dir.exists():
            os.replace(output_dir, backup)
        try:
            os.replace(stage, output_dir)
        except Exception:
            if backup.exists():
                os.replace(backup, output_dir)
            raise
    return output_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Build fully reviewed EPAH diagnosis v0.1 bundle")
    parser.add_argument("--matrix", type=Path, default=MATRIX_FILE)
    parser.add_argument("--municipalities", type=Path, default=REGISTRY_FILE)
    parser.add_argument("--catalog", type=Path, default=CATALOG_FILE)
    parser.add_argument("--reviews", type=Path, default=REVIEWS_FILE)
    parser.add_argument("--release-config", type=Path, default=RELEASE_CONFIG)
    parser.add_argument("--boundaries", type=Path, default=BOUNDARIES)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--replace", action="store_true",
                        help="Replace existing finished bundle after a successful staged build")
    args = parser.parse_args()
    result = build_bundle(
        matrix_file=args.matrix, municipality_file=args.municipalities,
        catalog_file=args.catalog, reviews_file=args.reviews,
        release_config=args.release_config, boundaries=args.boundaries,
        output_dir=args.output_dir, replace=args.replace,
    )
    print("EPAH Diagnosis v0.1 release bundle completed and verified:")
    print(f"  {result}")
    for item in sorted(result.rglob("*")):
        if item.is_file():
            print("  - " + str(item.relative_to(result)))


if __name__ == "__main__":
    main()
