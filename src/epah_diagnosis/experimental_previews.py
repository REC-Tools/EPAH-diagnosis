"""Preview-only replacements for legacy survey and ERA5 finalizers.

Fresh, staged technical outputs only. Never writes to the canonical matrix,
never grants approval, and never copies the raw survey into the output pack.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import tempfile
from dataclasses import asdict
from datetime import date
from pathlib import Path

from epah_diagnosis.cli import read_municipality_codes
from epah_diagnosis.local_affordability import (
    MIN_RESPONDENTS, filter_municipalities, parse_affordability_csv,
)
from epah_diagnosis.provenance import sha256_file

ROOT = Path(__file__).resolve().parents[2]
STATUS = "technical_draft_do_not_publish"
QUESTIONS = ("unable_warm_yes", "utility_arrears_yes", "unable_cool_yes", "reduced_heating_cost_yes")


def _destination(out_dir: Path, inputs: list[Path]) -> Path:
    target = out_dir.resolve()
    if out_dir.exists():
        raise FileExistsError("Choose a NEW output directory; prior evidence cannot be overwritten")
    if target == ROOT or any(target.is_relative_to(ROOT / name) for name in (
            "data", "config", "src", "tests", "scripts", "docs", ".git", ".github")):
        raise ValueError("Preview destination must not be inside canonical or source directories")
    for source in inputs:
        if not source.is_file():
            raise FileNotFoundError(f"Missing input: {source}")
        if target.is_relative_to(source.resolve().parent):
            raise ValueError("Preview destination must be separate from input/evidence directories")
    return target


def _registry(path: Path) -> dict[str, str]:
    result = read_municipality_codes(path)
    if len(result) != 27:
        raise ValueError("Exactly 27 registered municipalities required")
    return result


def _csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _publish(target: Path, inputs: dict[str, Path], rows: list[dict], qa: dict,
             summary: dict | None = None) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".epah-preview-", dir=target.parent) as temp:
        stage = Path(temp) / "result"
        stage.mkdir()
        _csv(stage / "preview.csv", rows)
        if summary is not None:
            (stage / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
        qa.update(status=STATUS, scientific_approval=False, publication_allowed=False,
                  automatic_promotions=0, canonical_data_modified=False)
        (stage / "qa.json").write_text(json.dumps(qa, indent=2, allow_nan=False) + "\n")
        (stage / "README_REVIEW.txt").write_text(
            "TECHNICAL PREVIEW - DO NOT PUBLISH\n"
            "No canonical promotion or scientific approval. Keep raw sources separately.\n"
            "Survey suppression is a minimum small-sample control, not a privacy or representativeness certification.\n"
            "Review sampling, valid-response denominators and disclosure across other outputs before sharing.\n")
        manifest = {"schema_version": "1.0", "status": STATUS, "scientific_approval": False,
                    "publication_allowed": False, "automatic_promotions": 0,
                    "canonical_data_modified": False,
                    "input_sha256": {key: sha256_file(value) for key, value in inputs.items()},
                    "output_sha256": {p.name: sha256_file(p) for p in stage.iterdir()}}
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        # Atomically reserve the new destination before replacing our own empty
        # directory with the completed stage. Never replace a prior output pack.
        target.mkdir(exist_ok=False)
        try:
            os.replace(stage, target)
        except OSError:
            target.rmdir()
            raise
    return target


def build_affordability(input_file: Path, registry_file: Path, out_dir: Path, *,
                        period_start: str, period_end: str) -> Path:
    target = _destination(out_dir, [input_file, registry_file])
    start, end = date.fromisoformat(period_start), date.fromisoformat(period_end)
    if start.isoformat() != period_start or end.isoformat() != period_end or start > end:
        raise ValueError("Survey reference period must use ordered ISO dates")
    registry = _registry(registry_file)
    records = filter_municipalities(parse_affordability_csv(
        input_file.read_text(encoding="utf-8-sig")), set(registry))
    rows = []
    eligible = []
    for item in records:
        suppressed = item.respondents < MIN_RESPONDENTS
        if not suppressed:
            eligible.append(item)
        rows.append({"municipality": item.municipality, "municipality_code": registry[item.municipality],
                     "period_start": period_start, "period_end": period_end,
                     "status": STATUS, "missingness_reason": "small_sample_suppressed" if suppressed else "",
                     "respondents": "" if suppressed else item.respondents,
                     **{field: "" if suppressed else getattr(item, field) for field in QUESTIONS},
                     **{field.removesuffix("_yes") + "_pct": "" if suppressed else item.share(field)
                        for field in QUESTIONS}})
    denominator = sum(r.respondents for r in eligible)
    summary = {"status": STATUS, "period_start": period_start, "period_end": period_end,
               "scope": "eligible respondents only; not population prevalence",
               "eligible_municipalities": len(eligible), "suppressed_municipalities": 27 - len(eligible),
               "eligible_respondents": denominator,
               "weighted_pct": {field: round(sum(getattr(r, field) for r in eligible) / denominator * 100, 2)
                                if denominator else None for field in QUESTIONS},
               "excluded_suppressed_counts": True, "publication_allowed": False}
    return _publish(target, {"survey": input_file, "registry": registry_file}, rows,
                    {"kind": "local_affordability", "municipalities": 27,
                     "minimum_respondents": MIN_RESPONDENTS,
                     "suppressed_municipalities": 27 - len(eligible),
                     "common_valid_response_denominator_required": True}, summary)


def build_climate(kind: str, input_file: Path, geometry_file: Path, registry_file: Path,
                  out_dir: Path, *, year: int, max_fallback_km: float = 30.0) -> Path:
    from epah_diagnosis.cartography import check_source_crs
    from epah_diagnosis.release_artifacts import check_geojson
    from epah_diagnosis.cooling import compute_municipal_cdd_from_netcdf
    from epah_diagnosis.heat_stress import compute_municipal_heat_stress_from_netcdf

    if kind not in {"cdd", "utci"}:
        raise ValueError("Unknown climate preview kind")
    target = _destination(out_dir, [input_file, geometry_file, registry_file])
    registry = _registry(registry_file)
    geometry = json.loads(geometry_file.read_text(encoding="utf-8"))
    check_source_crs(geometry)
    check_geojson(geometry, registry)
    compute = compute_municipal_cdd_from_netcdf if kind == "cdd" else compute_municipal_heat_stress_from_netcdf
    results = compute(input_file, geometry_file, year, max_fallback_km=max_fallback_km)
    if len(results) != 27 or {r.municipality for r in results} != set(registry):
        raise ValueError("Climate output must match the 27 registered municipalities")
    rows = [{**asdict(r), "municipality_code": registry[r.municipality], "status": STATUS}
            for r in results]
    return _publish(target, {"netcdf": input_file, "geography": geometry_file, "registry": registry_file}, rows,
                    {"kind": kind, "municipalities": 27, "reference_year": year,
                     "max_fallback_km": max_fallback_km, "spatial_representativeness_approved": False})


def affordability_main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Local aggregate survey technical preview; never promotes data")
    parser.add_argument("--input", type=Path, default=ROOT / "data/raw/local_energy_affordability.csv")
    parser.add_argument("--registry", type=Path, default=ROOT / "data/municipalities.csv")
    parser.add_argument("--period-start", required=True)
    parser.add_argument("--period-end", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = build_affordability(args.input, args.registry, args.out_dir,
                                     period_start=args.period_start, period_end=args.period_end)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"BLOCKED: {exc}\n")
    print(f"Technical survey preview (NOT APPROVED): {result}")
    return 0


def climate_main(kind: str, argv=None) -> int:
    parser = argparse.ArgumentParser(description=f"ERA5 {kind} technical preview; never promotes data")
    filename = "era5_land_daily_mean_temperature_2025.nc" if kind == "cdd" else "era5_heat_utci_2025.nc"
    parser.add_argument("--input", type=Path, default=ROOT / "data/raw" / filename)
    parser.add_argument("--geography", type=Path, default=ROOT / "data/geography/municipalities_2026.geojson")
    parser.add_argument("--registry", type=Path, default=ROOT / "data/municipalities.csv")
    parser.add_argument("--reference-year", type=int, default=2025)
    parser.add_argument("--max-fallback-km", type=float, default=30.0)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = build_climate(kind, args.input, args.geography, args.registry, args.out_dir,
                               year=args.reference_year, max_fallback_km=args.max_fallback_km)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"BLOCKED: {exc}\n")
    print(f"Technical {kind} preview (NOT APPROVED): {result}")
    return 0
