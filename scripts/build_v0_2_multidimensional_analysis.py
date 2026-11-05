"""Create non-publishable independent comparison tables from verified pilot data."""
from __future__ import annotations

import argparse
import csv
import json
import os
import tempfile
from pathlib import Path

from epah_diagnosis.analysis_v0_2 import compare
from epah_diagnosis.release_artifacts import sha256_file
from epah_diagnosis.report_v0_2 import verified_data

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "outputs/v0.1.0-pilot"
OUTPUT = ROOT / "outputs/v0.2-multidimensional-analysis"
REGISTRY = ROOT / "data/municipalities.csv"
RELEASE_CONFIG = ROOT / "config/release_v0_1.json"


def build(bundle: Path, destination: Path, registry: Path = REGISTRY,
          release_config: Path = RELEASE_CONFIG) -> Path:
    bundle, destination = bundle.resolve(), destination.resolve()
    if destination.exists():
        raise FileExistsError("Existing analysis evidence: choose new --out-dir")
    if destination == bundle or destination.is_relative_to(bundle):
        raise ValueError("Analysis cannot be stored inside input bundle")
    profiles, manifest = verified_data(bundle, registry, release_config)
    with registry.open(encoding="utf-8-sig", newline="") as f:
        registry_rows = list(csv.DictReader(f))
    codes = {r["municipality"]: r["istat_code"] for r in registry_rows}
    compared, summary = compare(profiles, codes)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".epah-v02-analysis-", dir=destination.parent) as td:
        stage = Path(td) / "analysis"
        stage.mkdir()
        comparison_path = stage / "municipality_comparison_v0_2.csv"
        with comparison_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(compared[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(compared)
        pair_file = stage / "pairwise_overlap_v0_2.csv"
        with pair_file.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=list(summary["pairwise_cooccurrences"][0]),
                lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(summary["pairwise_cooccurrences"])
        summary_file = stage / "analysis_summary_v0_2.json"
        summary_file.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        artifacts = ["municipality_comparison_v0_2.csv", "pairwise_overlap_v0_2.csv",
                     "analysis_summary_v0_2.json"]
        lineage = {
            "status": "technical_draft_do_not_publish",
            "municipalities": 27,
            "no_composite_score": True,
            "source_bundle": bundle.name,
            "source_release": manifest.get("release"),
            "source_manifest_sha256": sha256_file(bundle / "release_manifest.json"),
            "source_profiles_sha256": sha256_file(bundle / "municipality_profile.csv"),
            "artifacts": {
                name: {"sha256": sha256_file(stage / name),
                       "bytes": (stage / name).stat().st_size}
                for name in artifacts
            },
        }
        (stage / "analysis_manifest_v0_2.json").write_text(
            json.dumps(lineage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        if destination.exists():
            raise FileExistsError("Concurrent output appeared; refusing overwrite")
        os.replace(stage, destination)
    return destination


def main() -> int:
    p = argparse.ArgumentParser(description="Non-causal 27-town v0.2 descriptive analysis")
    p.add_argument("--bundle", type=Path, default=BUNDLE)
    p.add_argument("--out-dir", type=Path, default=OUTPUT)
    p.add_argument("--registry", type=Path, default=REGISTRY)
    p.add_argument("--release-config", type=Path, default=RELEASE_CONFIG)
    args = p.parse_args()
    try:
        path = build(args.bundle, args.out_dir, args.registry, args.release_config)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"BLOCKED: {exc}")
        return 1
    print("V0.2 descriptive, not for publication:", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
