"""Fail-closed 0.2.0 stable SOFTWARE-only release readiness; never a data approval."""
from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.2.0"
TAG = "v0.2.0"
MODULES = (
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
    versions = [p["version"] for p in lock["package"]
                if p.get("name") == "epah-diagnosis" and
                p.get("source", {}).get("editable") == "."]
    pkg = (root / "src/epah_diagnosis/__init__.py").read_text(encoding="utf-8")
    if (project["project"]["version"] != VERSION or versions != [VERSION]
            or f'__version__ = "{VERSION}"' not in pkg):
        raise ValueError("Stable code, editable lock and package versions disagree")
    metadata = json.loads((root / "docs/releases/v0.2.0.json").read_text(encoding="utf-8"))
    config = json.loads((root / "config/report_v0_2.json").read_text(encoding="utf-8"))
    expected = {
        "version": VERSION,
        "tag": TAG,
        "release_track": "software_source_only_stable",
        "publication_status": "stable_software_unapproved_territorial_results",
        "source_code_public": True,
        "scientific_validation": "not_asserted_by_software_release",
        "institutional_approval": "pending",
        "publish_local_pilot_or_v02_outputs": False,
        "publish_pdf_or_data_assets": False,
        "municipalities": 27,
        "independent_core_indicators": 9,
        "no_composite_energy_poverty_score": True,
        "household_inference": False,
        "quarantined_cit_excluded": True,
        "historical_rc_tag": "v0.2.0-rc1",
    }
    if (any(metadata.get(k) != v for k, v in expected.items())
            or config.get("publication_status") != "technical_draft_do_not_publish"
            or config.get("approved_for_publication") is not False):
        raise ValueError("Stable software cannot assert scientific/institutional publication")
    if any(not (root / "scripts" / name).is_file() for name in MODULES):
        raise ValueError("Missing one or more stable v0.2 software components")
    notes = (root / "docs/releases/v0.2.0.md").read_text(encoding="utf-8")
    for phrase in (
        "v0.2.0", "NON", "pending", "CIT", "27 Comuni", "uv run --locked",
        "source_only_v0.2.0_attestation.json",
    ):
        if phrase not in notes:
            raise ValueError(f"Stable software notes must disclose scope: {phrase}")
    workflow = (root / ".github/workflows/v02-stable-software.yml").read_text(encoding="utf-8")
    if ("workflow_dispatch:" not in workflow
            or "  push:" in workflow or "  pull_request:" in workflow
            or "--prerelease" in workflow or
            "source_only_v0.2.0_attestation.json" not in workflow):
        raise ValueError("Stable software release must require an explicit manual dispatch")
    return {
        "schema_version": "1.0", "version": VERSION, "tag": TAG,
        "source_only": True, "stable_software": True, "prerelease": False,
        "publication_authorized": False, "review_status": "pending",
        "core_municipalities": 27, "core_indicators": 9,
        "quarantined_cit_included": False, "attached_private_data": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only stable SOFTWARE-only release readiness (not approval of data)"
    )
    parser.add_argument("--commit-sha", help="40-character Git commit SHA on main")
    parser.add_argument("--json-out", type=Path, help="Write attestation to a NEW file")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        result = check(args.root)
        if args.commit_sha is not None:
            if not re.fullmatch("[0-9a-f]{40}", args.commit_sha):
                raise ValueError("Commit SHA must contain 40 lowercase hex characters")
            result["git_commit_sha"] = args.commit_sha
        if args.json_out is not None:
            args.json_out.parent.mkdir(parents=True, exist_ok=True)
            with args.json_out.open("x", encoding="utf-8") as stream:
                json.dump(result, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print("BLOCKED:", exc, file=sys.stderr)
        return 1
    print("Stable v0.2.0 SOFTWARE-only contract passed; territorial publication unapproved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
