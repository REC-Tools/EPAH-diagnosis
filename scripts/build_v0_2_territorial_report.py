"""Build a separate v0.2 territorial technical PDF from a checked v0.1 bundle.

No direct import of CIT quarantine and no changes to official or pilot datasets.
Never overwrite an existing report folder. All reported values are computed
from the 27 municipality profiles inside the already-hashed v0.1 package.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from pypdf import PdfReader

from epah_diagnosis.release_artifacts import sha256_file
from epah_diagnosis.report_v0_2 import computed_facts, verified_data, write_report

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE = ROOT / "outputs/v0.1.0-pilot"
DEFAULT_OUTPUT = ROOT / "outputs/v0.2-territorial-technical"
CONFIG = ROOT / "config/report_v0_2.json"
RELEASE_CONFIG = ROOT / "config/release_v0_1.json"
REGISTRY = ROOT / "data/municipalities.csv"
REPORT_FILE = "diagnostic_report_v0_2_technical.pdf"


def validate_config(path: Path) -> dict:
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if (cfg.get("publication_status") != "technical_draft_do_not_publish"
            or cfg.get("ta_code") != "26-IT-Unione-TA26"
            or cfg.get("language") != "it"
            or not isinstance(cfg.get("audience"), str)
            or not cfg["audience"].strip()
            or not isinstance(cfg.get("author_label"), str)
            or not cfg["author_label"].strip()):
        raise ValueError("Report configuration must explicitly deny institutional publication")
    return cfg


def build_report(
    bundle: Path,
    output: Path,
    registry: Path = REGISTRY,
    release_config: Path = RELEASE_CONFIG,
    report_config: Path = CONFIG,
) -> Path:
    """Read and verify inputs *before* allocating a new report destination."""
    bundle, output = bundle.resolve(), output.resolve()
    if output.exists():
        raise FileExistsError(f"Preserve existing v0.2 report: {output}")
    if output == bundle or output.is_relative_to(bundle):
        raise ValueError("Report output must not modify the existing v0.1 input bundle")
    cfg = validate_config(report_config)
    profiles, manifest = verified_data(bundle, registry, release_config)
    facts = computed_facts(profiles)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".epah-v0.2-report-", dir=output.parent) as temp:
        stage = Path(temp) / "report"
        stage.mkdir()
        pdf_file = stage / REPORT_FILE
        write_report(pdf_file, bundle, profiles, facts, cfg)
        pdf = PdfReader(str(pdf_file))
        if not 9 <= len(pdf.pages) <= 12:
            raise ValueError(f"Unexpected PDF pagination: {len(pdf.pages)} pages")
        first = pdf.pages[0].extract_text() or ""
        full = "\n".join(page.extract_text() or "" for page in pdf.pages)
        if ("26-IT-Unione-TA26" not in first
                or "27 Comuni" not in full
                or "NON PUBBLICARE" not in full
                or "Pont Canavese" in full
                or "CIT Piemonte" in full):
            raise ValueError("PDF missing essential technical status / scope or contains excluded CIT")
        (stage / "diagnostic_facts_v0_2.json").write_text(
            json.dumps(facts, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        notes = {
            "version": "0.2-technical",
            "status": "technical_draft_do_not_publish",
            "project_code": cfg["ta_code"],
            "generated_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
            "source_bundle": bundle.name,
            "source_release": manifest.get("release"),
            "source_manifest_sha256": sha256_file(bundle / "release_manifest.json"),
            "source_profile_sha256": sha256_file(bundle / "municipality_profile.csv"),
            "source_map_sha256": {
                name: sha256_file(bundle / "maps" / name)
                for name in ("map_old_building_stock.png", "map_income_vulnerability.png")
            },
            "source_approval": "v0.1 technical pilot; institutional approval not asserted",
            "source_scope": "27 municipalities and nine independently described indicators",
            "not_a_new_source_validation": True,
            "no_composite_score": True,
            "no_household_attribution": True,
            "cit_included": False,
            "output_pdf_pages": len(pdf.pages),
            "artifacts": {
                filename: {"sha256": sha256_file(stage / filename),
                           "bytes": (stage / filename).stat().st_size}
                for filename in (REPORT_FILE, "diagnostic_facts_v0_2.json")
            },
        }
        (stage / "report_manifest_v0_2.json").write_text(
            json.dumps(notes, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        if output.exists():
            raise FileExistsError("Report output created concurrently; refusing overwrite")
        os.replace(stage, output)
    return output


def main() -> int:
    p = argparse.ArgumentParser(
        description="Generate a distinct nonpublishable v0.2 territorial PDF from a v0.1 technical bundle"
    )
    p.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--registry", type=Path, default=REGISTRY)
    p.add_argument("--release-config", type=Path, default=RELEASE_CONFIG)
    p.add_argument("--report-config", type=Path, default=CONFIG)
    args = p.parse_args()
    try:
        result = build_report(
            args.bundle, args.out_dir, args.registry, args.release_config, args.report_config
        )
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"BLOCKED: {exc}")
        return 1
    print(f"V0.2 technical report: {result / REPORT_FILE}")
    print("This is a separate working draft, not an approved institutional EPAH release.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
