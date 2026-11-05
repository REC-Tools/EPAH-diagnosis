"""Build an offline v0.2 HTML dashboard from audited comparisons and v0.1."""
from __future__ import annotations

import argparse
import csv
import json
import os
import tempfile
from pathlib import Path

from epah_diagnosis.analysis_v0_2 import compare
from epah_diagnosis.dashboard_v0_2 import document
from epah_diagnosis.release_artifacts import sha256_file
from epah_diagnosis.report_v0_2 import FIELDS, verified_data

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "outputs/v0.2-multidimensional-analysis"
BUNDLE = ROOT / "outputs/v0.1.0-pilot"
OUTPUT = ROOT / "outputs/v0.2-offline-dashboard"
REGISTRY = ROOT / "data/municipalities.csv"
RELEASE_CONFIG = ROOT / "config/release_v0_1.json"


def read_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Expected JSON object")
    return data


def build(analysis_dir: Path, bundle: Path, destination: Path,
          registry: Path = REGISTRY, release_config: Path = RELEASE_CONFIG) -> Path:
    analysis_dir, bundle, destination = (p.resolve() for p in (analysis_dir, bundle, destination))
    if destination.exists():
        raise FileExistsError("Dashboard output exists; specify a new --out-dir")
    if destination.is_relative_to(analysis_dir) or destination.is_relative_to(bundle):
        raise ValueError("Cannot write dashboard inside source directories")
    profiles, _ = verified_data(bundle, registry, release_config)
    with registry.open(encoding="utf-8-sig", newline="") as handle:
        codes = {r["municipality"]: r["istat_code"] for r in csv.DictReader(handle)}
    expected_rows, expected_summary = compare(profiles, codes)
    manifest = read_json(analysis_dir / "analysis_manifest_v0_2.json")
    if (manifest.get("status") != "technical_draft_do_not_publish"
            or manifest.get("municipalities") != 27
            or manifest.get("no_composite_score") is not True
            or manifest.get("source_manifest_sha256") != sha256_file(bundle / "release_manifest.json")
            or manifest.get("source_profiles_sha256") != sha256_file(bundle / "municipality_profile.csv")):
        raise ValueError("Comparison input is not backed by this verified pilot")
    for name, entry in manifest.get("artifacts", {}).items():
        f = analysis_dir / name
        if not f.is_file() or f.stat().st_size != entry.get("bytes") or sha256_file(f) != entry.get("sha256"):
            raise ValueError("Analysis checksum mismatch: " + name)
    required = ("municipality_comparison_v0_2.csv",
                "pairwise_overlap_v0_2.csv", "analysis_summary_v0_2.json")
    if set(manifest.get("artifacts", {})) != set(required):
        raise ValueError("Unexpected analysis fileset")
    with (analysis_dir / required[0]).open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    with (analysis_dir / required[1]).open(encoding="utf-8", newline="") as f:
        pairs = list(csv.DictReader(f))
    summary = read_json(analysis_dir / required[2])
    if (rows != expected_rows or summary != expected_summary
            or len(pairs) != 28
            or pairs != [{k: str(v) for k, v in p.items()}
                         for p in expected_summary["pairwise_cooccurrences"]]):
        raise ValueError("Analysis tables differ from independently recomputed 27-town evidence")
    p_by_name = {p["municipality"]: p for p in profiles}
    payload = {
        "schema_version": "1.0",
        "status": "technical_draft_do_not_publish",
        "no_composite_score": True,
        "indicators": [{"key": key, "label": label, "unit": unit} for key, label, unit, _ in FIELDS],
        "municipalities": [],
        "pairs": [
            {"a": p["indicator_a"], "b": p["indicator_b"],
             "count": p["municipalities_above_both"]}
            for p in expected_summary["pairwise_cooccurrences"]
        ],
    }
    for row in expected_rows:
        p = p_by_name[row["municipality"]]
        payload["municipalities"].append({
            "name": row["municipality"], "code": row["istat_code"],
            "snai": p["snai_class"], "snai_year": p["snai_year"],
            "values": {
                key: {"value": float(row[key]),
                      "median": float(row[key + "_median_27"]),
                      "year": p[year_key]}
                for key, _, _, year_key in FIELDS
            },
        })
    if len(payload["municipalities"]) != 27:
        raise ValueError("Incomplete dashboard input")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".epah-v02-dashboard-", dir=destination.parent) as td:
        stage = Path(td) / "dashboard"
        stage.mkdir()
        (stage / "index.html").write_text(document(payload), encoding="utf-8")
        (stage / "dashboard_data_v0_2.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        names = ("index.html", "dashboard_data_v0_2.json")
        out_manifest = {
            "status": "technical_draft_do_not_publish",
            "offline_only": True, "municipalities": 27,
            "no_composite_score": True,
            "source_manifest_sha256": sha256_file(bundle / "release_manifest.json"),
            "analysis_manifest_sha256": sha256_file(analysis_dir / "analysis_manifest_v0_2.json"),
            "artifacts": {
                name: {"sha256": sha256_file(stage / name),
                       "bytes": (stage / name).stat().st_size}
                for name in names
            },
        }
        (stage / "dashboard_manifest_v0_2.json").write_text(
            json.dumps(out_manifest, indent=2) + "\n", encoding="utf-8"
        )
        if destination.exists():
            raise FileExistsError("Concurrent dashboard output; refusing overwrite")
        os.replace(stage, destination)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description="Build local-only v0.2 HTML viewer, not a publication")
    parser.add_argument("--analysis-dir", type=Path, default=ANALYSIS)
    parser.add_argument("--bundle", type=Path, default=BUNDLE)
    parser.add_argument("--out-dir", type=Path, default=OUTPUT)
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--release-config", type=Path, default=RELEASE_CONFIG)
    args = parser.parse_args()
    try:
        result = build(args.analysis_dir, args.bundle, args.out_dir,
                       args.registry, args.release_config)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"BLOCKED: {exc}")
        return 1
    print("Open locally:", result / "index.html")
    print("TECHNICAL DRAFT - NOT FOR PUBLICATION.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
