"""Build 27 independent v0.2 factsheet PDFs from a verified v0.1 pilot."""
from __future__ import annotations

import argparse
import csv
import json
import os
import tempfile
from pathlib import Path

from pypdf import PdfReader

from epah_diagnosis.release_artifacts import sha256_file
from epah_diagnosis.report_v0_2 import computed_facts, verified_data
from epah_diagnosis.sheets_v0_2 import render_sheet

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE = ROOT / "outputs/v0.1.0-pilot"
DEFAULT_OUT = ROOT / "outputs/v0.2-municipal-sheets"
REGISTRY = ROOT / "data/municipalities.csv"
RELEASE_CONFIG = ROOT / "config/release_v0_1.json"


def build(bundle: Path, out_dir: Path, registry_file: Path = REGISTRY,
          release_config: Path = RELEASE_CONFIG) -> Path:
    bundle, destination = bundle.resolve(), out_dir.resolve()
    if destination.exists():
        raise FileExistsError("Previous sheet output exists; select a fresh --out-dir")
    if destination == bundle or destination.is_relative_to(bundle):
        raise ValueError("Output cannot be inside the original bundle")
    profiles, source_manifest = verified_data(bundle, registry_file, release_config)
    facts = computed_facts(profiles)
    with registry_file.open(encoding="utf-8-sig", newline="") as handle:
        source_registry = list(csv.DictReader(handle))
    codes = {r["municipality"]: r["istat_code"] for r in source_registry}
    if len(codes) != 27:
        raise ValueError("Need exactly 27 distinct registry rows")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".v02-sheets-", dir=destination.parent) as td:
        stage = Path(td) / "candidate"
        sheets = stage / "municipalities"
        sheets.mkdir(parents=True)
        entries = []
        for profile in sorted(profiles, key=lambda r: codes[r["municipality"]]):
            code = codes[profile["municipality"]]
            relative = f"municipalities/{code}.pdf"
            pdf = stage / relative
            render_sheet(pdf, profile, facts, code)
            reader = PdfReader(str(pdf))
            if len(reader.pages) != 1:
                raise ValueError(f"Fact sheet must fit one A4 page: {code}")
            page_text = reader.pages[0].extract_text() or ""
            if code not in page_text or "NON PUBBLICARE" not in page_text:
                raise ValueError(f"Missing municipal ID/status in PDF {code}")
            entries.append({
                "municipality": profile["municipality"], "istat_code": code,
                "path": relative, "sha256": sha256_file(pdf),
                "bytes": pdf.stat().st_size,
            })
        if len(entries) != 27 or len({r["istat_code"] for r in entries}) != 27:
            raise ValueError("Incomplete sheets coverage")
        index = {
            "schema_version": "1.0",
            "status": "technical_draft_do_not_publish",
            "municipalities": 27,
            "no_composite_score": True,
            "source_manifest_sha256": sha256_file(bundle / "release_manifest.json"),
            "source_release": source_manifest.get("release"),
            "sheets": entries,
        }
        (stage / "sheets_index_v0_2.json").write_text(
            json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
        if destination.exists():
            raise FileExistsError("Concurrent destination created; refusing overwrite")
        os.replace(stage, destination)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate 27 one-page internal technical factsheets (not approved)"
    )
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--release-config", type=Path, default=RELEASE_CONFIG)
    args = parser.parse_args()
    try:
        result = build(args.bundle, args.out_dir, args.registry, args.release_config)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"BLOCKED: {exc}")
        return 1
    print("V0.2 MUNICIPAL SHEETS (technical draft only):", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
