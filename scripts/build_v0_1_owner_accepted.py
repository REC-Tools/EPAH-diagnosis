"""Build an owner-accepted pilot v0.1.0 without changing canonical data.

The user approved technical pilot release on 2026-10-30. This is NOT a
claim that independent validation or Unione Montana endorsement occurred.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import tempfile
from pathlib import Path

from epah_diagnosis.cli import read_municipality_codes
from epah_diagnosis.geography import parse_boundaries_zip, write_geojson
# Import the regular release builder only at invocation time: tests can
# independently inspect pilot staging without loading another script.

ROOT = Path(__file__).resolve().parents[1]
OWNER = "Tommaso Ferrucci"
DATE = "2026-10-30"
EVIDENCE = "https://github.com/REC-Tools/EPAH-diagnosis/blob/main/docs/reviews/v0_1_owner_acceptance_20261030.md"
PILOT_FIELDS = {
    "dea_accessibility": (
        "dea_accessibility_minutes.csv", "dea_accessibility_qa.json",
        "nearest_dea_municipality", "nearest_dea_code",
        "https://www.istat.it/notizia/matrici-di-contiguita-distanza-e-pendolarismo/"
    ),
    "rail_accessibility": (
        "rail_accessibility_minutes.csv", "rail_accessibility_qa.json",
        "nearest_service_municipality", "nearest_service_code",
        "https://www.istat.it/notizia/matrici-di-contiguita-distanza-e-pendolarismo/"
    ),
    "upper_secondary_accessibility": (
        "upper_secondary_accessibility_minutes.csv", "upper_secondary_accessibility_qa.json",
        "nearest_service_municipality", "nearest_service_code",
        "https://www.istat.it/notizia/matrici-di-contiguita-distanza-e-pendolarismo/"
    ),
}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def check_sample_evidence(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("comparisons")
    if (data.get("technical_pass") is not True or
            data.get("routes_checked") != 9 or data.get("matches") != 9 or
            not isinstance(items, list) or len(items) != 9 or
            not all(x.get("matches_original") is True for x in items) or
            set(x.get("indicator_id") for x in items) != set(PILOT_FIELDS) or
            any(sum(x.get("indicator_id") == k for x in items) != 3 for k in PILOT_FIELDS) or
            data.get("validated_for_release") is not False):
        raise ValueError("Original ISTAT audit must pass 9/9 (three per indicator)")
    return data


def stage_inputs(matrix: Path, catalog_path: Path, registry_path: Path,
                 drafts: dict[str, Path], samples_file: Path, work: Path) -> dict:
    samples = check_sample_evidence(samples_file)
    register = read_municipality_codes(registry_path)
    if len(register) != 27 or len(set(register.values())) != 27:
        raise ValueError("Exactly 27 distinct municipalities required")
    with matrix.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        if not fields:
            raise ValueError("Canonical matrix has no header")
        rows = list(reader)
    if len(rows) != 243:
        raise ValueError("Canonical core matrix must contain 243 records")
    index = {(r["municipality"], r["indicator_id"]): r for r in rows}
    if len(index) != 243:
        raise ValueError("Duplicate canonical matrix key")
    seen = set()
    audit_hashes = {}
    for kind, directory in drafts.items():
        csv_name, qa_name, dest_name, dest_code, source_url = PILOT_FIELDS[kind]
        source_file = directory / csv_name
        qa = json.loads((directory / qa_name).read_text(encoding="utf-8"))
        observations = list(csv.DictReader(source_file.open(encoding="utf-8-sig", newline="")))
        observed_codes = {r["municipality_code"] for r in observations}
        report_routes = qa.get("route_pair_count", qa.get("complete_route_pairs"))
        destinations = (qa.get("eligible_dea_municipality_count") if kind == "dea_accessibility"
                        else qa.get("destination_municipality_count"))
        if (qa.get("indicator_id") != kind or qa.get("origin_count") != 27 or
                qa.get("validated_for_release") is not False or
                qa.get("qa_status") != "technical_checks_only" or
                qa.get("data_csv_sha256") != sha(source_file) or
                qa.get("road_zip_sha256") != samples.get("road_zip_sha256") or
                report_routes != 27 * destinations or
                qa.get("expected_route_pairs") != report_routes or
                len(observations) != 27 or len(observed_codes) != 27 or
                observed_codes != set(register.values())):
            raise ValueError(f"{kind}: draft QA, sample source, or 27-town coverage differs")
        for item in observations:
            municipality = item["municipality"]
            if register.get(municipality) != item["municipality_code"]:
                raise ValueError(f"{kind}: ISTAT municipality/name mismatch")
            key = municipality, kind
            if key not in index or key in seen:
                raise ValueError(f"{kind}: missing or duplicate matrix key")
            seen.add(key)
            target = index[key]
            minutes = float(item["travel_time_minutes"])
            km = float(item["distance_km"])
            if not (math.isfinite(minutes) and 0 <= minutes <= 1440 and
                    math.isfinite(km) and 0 <= km <= 3000):
                raise ValueError(f"{kind}: invalid route value for {municipality}")
            if target["value"].strip():
                raise ValueError(f"{kind}: canonical matrix already populated; refuse unexpected overwrite")
            target.update({
                "status": "Dato validato",
                "year": "2021",
                "territorial_level": "Comune",
                "unit": "minuti",
                "source_url": source_url,
                "value": item["travel_time_minutes"],
                "quality": "Technical pilot accepted by expert; original ISTAT matrix and selected service-list proxy",
                "limitations": item["limitations"] + " PILOT v0.1: no nationwide nearest-service or institutional certification.",
                "notes": (f"Selected destination: {item[dest_name]} "
                          f"(ISTAT {item[dest_code]}); pilot technical acceptance {EVIDENCE}"),
            })
        audit_hashes[kind] = {
            "draft_data_sha256": qa["data_csv_sha256"],
            "route_pairs": report_routes,
            "candidate_destinations": destinations,
            "data_vintage": qa.get("service_vintage", "2025 Ministry DEA; road geography 2021"),
        }
    if len(seen) != 81:
        raise ValueError("Exactly 81 staged accessibility rows required")
    staged_matrix = work / "verification_matrix_pilot.csv"
    with staged_matrix.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    ids = [x["id"] for x in catalog["indicators"]]
    if len(ids) != 9 or len(set(ids)) != 9:
        raise ValueError("Nine distinct core methodologies required")
    for entry in catalog["indicators"]:
        # Operational only in the staged *pilot*, not in canonical catalog.
        entry["methodological_maturity"] = "OPERATIONAL"
        entry["caveat"] += " Pilot v0.1: owner accepted selected proxy with documented limits; independent institutional review pending."
    staged_catalog = work / "indicators_pilot.json"
    staged_catalog.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    review = {
        "schema_version": "1.0",
        "description": "Owner's explicit blanket TECHNICAL acceptance of limited pilot methods; not independent verification or Unione Montana endorsement.",
        "methodology_approvals": [
            {"indicator_id": identifier, "decision": "approved", "reviewed_by": OWNER,
             "reviewed_on": DATE, "evidence_url": EVIDENCE}
            for identifier in ids
        ],
    }
    staged_reviews = work / "methodology_reviews_owner_accepted.json"
    staged_reviews.write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "matrix": staged_matrix, "catalog": staged_catalog,
        "reviews": staged_reviews, "audits": audit_hashes,
        "istatsample_sha256": sha(samples_file),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build owner-approved pilot v0.1.0 from 27-town QA drafts")
    parser.add_argument("--matrix", type=Path, default=ROOT / "data/verification_matrix.csv")
    parser.add_argument("--catalog", type=Path, default=ROOT / "config/indicators.json")
    parser.add_argument("--registry", type=Path, default=ROOT / "data/municipalities.csv")
    parser.add_argument("--dea-draft", type=Path, default=ROOT / "outputs/quality/dea_accessibility_2025_v03")
    parser.add_argument("--rail-draft", type=Path, default=ROOT / "outputs/quality/rail_accessibility_v01")
    parser.add_argument("--school-draft", type=Path, default=ROOT / "outputs/quality/upper_secondary_accessibility_v01")
    parser.add_argument("--samples", type=Path, default=ROOT / "outputs/quality/v0_1_pilot_route_samples_v01/samples.json")
    parser.add_argument("--boundaries-zip", type=Path, default=ROOT / "data/downloads/Limiti01012026_g.zip")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/v0.1.0-pilot")
    parser.add_argument("--archive", type=Path, default=ROOT / "outputs/epah_diagnosis_v0.1.0_pilot.zip")
    args = parser.parse_args()
    if args.output_dir.exists() or args.archive.exists():
        raise FileExistsError("Pilot bundle/archive exists; preserve it and choose fresh output paths")
    originals = {args.matrix: sha(args.matrix), args.catalog: sha(args.catalog)}
    quality = ROOT / "outputs/quality"
    quality.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="v0.1-owner-accepted-", dir=quality) as tmp:
        work = Path(tmp)
        staging = stage_inputs(
            args.matrix, args.catalog, args.registry,
            {"dea_accessibility": args.dea_draft,
             "rail_accessibility": args.rail_draft,
             "upper_secondary_accessibility": args.school_draft},
            args.samples, work,
        )
        geo = work / "municipalities.geojson"
        features = parse_boundaries_zip(args.boundaries_zip.read_bytes(), set(read_municipality_codes(args.registry)))
        write_geojson(features, geo)
        from build_v0_1_bundle import build_bundle
        completed = build_bundle(
            matrix_file=staging["matrix"], municipality_file=args.registry,
            catalog_file=staging["catalog"], reviews_file=staging["reviews"],
            release_config=ROOT / "config/release_v0_1.json",
            boundaries=geo, output_dir=args.output_dir,
        )
        manifest_path = completed / "release_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["release_track"] = "owner_accepted_technical_pilot"
        manifest["review_status"] = {
            "owner": OWNER, "owner_date": DATE, "owner_acceptance_url": EVIDENCE,
            "unione_montana_institutional_approval": "pending",
            "source_specific_independent_human_check": "not asserted",
            "composite_energy_poverty_score": "not produced",
        }
        manifest["audited_drafts"] = staging["audits"]
        manifest["nine_original_istat_route_samples_sha256"] = staging["istatsample_sha256"]
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for path, previous in originals.items():
            if sha(path) != previous:
                raise ValueError(f"Canonical file changed unexpectedly: {path}")
    args.archive.parent.mkdir(parents=True, exist_ok=True)
    if args.archive.suffix != ".zip":
        raise ValueError("--archive must end with .zip")
    with tempfile.TemporaryDirectory(prefix="v0.1-zip-", dir=args.archive.parent) as td:
        packaged = Path(td) / args.archive.name
        import zipfile
        with zipfile.ZipFile(packaged, "x", compression=zipfile.ZIP_DEFLATED) as out:
            for file in sorted(args.output_dir.rglob("*")):
                if file.is_file():
                    out.write(file, file.relative_to(args.output_dir))
        packaged.replace(args.archive)
    print("EPAH v0.1.0 owner-accepted technical pilot: COMPLETE")
    print("  27 municipalities x 9 indicators = 243 observations")
    print("  Original canonical matrix and catalog unchanged")
    print("  Institutional Unione Montana review: pending")
    print(f"  Bundle: {args.output_dir}")
    print(f"  ZIP: {args.archive}")


if __name__ == "__main__":
    main()
