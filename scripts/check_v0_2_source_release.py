"""Fail-closed source-code-only v0.2 RC contract, no release mutation or data promotion."""
from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "docs/releases/v0.2.0-rc1.json"
NOTES = ROOT / "docs/releases/v0.2.0-rc1.md"
VERSION = "0.2.0rc1"
TAG = "v0.2.0-rc1"
REQUIRED_SCRIPTS = (
    "build_v0_2_territorial_report.py",
    "build_v0_2_municipality_sheets.py",
    "build_v0_2_multidimensional_analysis.py",
    "build_v0_2_dashboard.py",
    "build_v0_2_review_package.py",
    "check_v0_2_review_package.py",
)


def check(root: Path = ROOT) -> dict:
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    lock = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
    versions = [
        p.get("version") for p in lock["package"]
        if p.get("name") == "epah-diagnosis" and p.get("source", {}).get("editable") == "."
    ]
    package_init = (root / "src/epah_diagnosis/__init__.py").read_text(encoding="utf-8")
    if (project["project"]["version"] != VERSION or versions != [VERSION]
            or f'__version__ = "{VERSION}"' not in package_init):
        raise ValueError("Project, installed package and locked local version must all agree")
    metadata = json.loads((root / "docs/releases/v0.2.0-rc1.json").read_text(encoding="utf-8"))
    report = json.loads((root / "config/report_v0_2.json").read_text(encoding="utf-8"))
    if (metadata.get("tag") != TAG or metadata.get("version") != VERSION
            or metadata.get("release_track") != "software_source_only_prerelease"
            or metadata.get("publication_status") != "technical_candidate_not_institutionally_approved"
            or metadata.get("source_code_public") is not True
            or metadata.get("institutional_approval") != "pending"
            or metadata.get("scientific_validation") != "not_assessed_by_release"
            or metadata.get("publish_local_pilot_or_v02_outputs") is not False
            or metadata.get("publish_pdf_or_data_assets") is not False
            or metadata.get("municipalities") != 27
            or metadata.get("independent_core_indicators") != 9
            or metadata.get("no_composite_energy_poverty_score") is not True
            or metadata.get("household_inference") is not False
            or metadata.get("quarantined_cit_excluded") is not True
            or report.get("publication_status") != "technical_draft_do_not_publish"
            or report.get("approved_for_publication") is not False):
        raise ValueError("V0.2 source-only pre-release cannot claim institutional publication approval")
    names = metadata.get("expected_components")
    if not isinstance(names, list) or len(names) != 5 or len(set(names)) != 5:
        raise ValueError("Incomplete v0.2 software components")
    if any(not (root / "scripts" / name).is_file() for name in REQUIRED_SCRIPTS):
        raise ValueError("Missing v0.2 executable component")
    notes = (root / "docs/releases/v0.2.0-rc1.md").read_text(encoding="utf-8")
    for phrase in (TAG, "NOT", "non include", "non", "pending human",
                   "dati sintetici", "CIT", "27 Comuni", "uv run --locked"):
        if phrase not in notes:
            raise ValueError(f"Missing limitation or installation guidance in RC notes: {phrase}")
    if (root / ".github/workflows/v02-ci-diagnostics.yml").exists():
        raise ValueError("Debugging workflow with repository write permissions must be removed")
    if (root / "docs/_temporary_v02_ci_failure.txt").exists():
        raise ValueError("Temporary CI diagnostic logs cannot be shipped with a release")
    return {
        "schema_version": "1.0", "version": VERSION, "tag": TAG,
        "source_only": True, "prerelease": True,
        "publication_authorized": False, "review_status": "pending",
        "ci_checks_dont_validate_official_sources": True,
        "core_municipalities": 27, "core_indicators": 9,
        "quarantined_cit_included": False,
        "attached_private_data": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only checks for software-only v0.2 source prerelease")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--json-out", type=Path,
                        help="Write an attestation JSON to a NEW file without overwriting")
    args = parser.parse_args()
    try:
        result = check(args.root)
        if args.json_out:
            dest = args.json_out
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("x", encoding="utf-8") as stream:
                json.dump(result, stream, indent=2, ensure_ascii=False)
                stream.write("\n")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 1
    print("Verified v0.2.0-rc1 software-only prerelease contract; institutional release remains blocked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
