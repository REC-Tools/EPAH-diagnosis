"""Fail-closed 0.3.0 stable SOFTWARE-only release readiness; never a data approval.

Checks that code, lock and package versions agree, that the release metadata
cannot claim scientific/institutional approval or publication, that every v0.3
candidate has its pipeline scripts and a non-approved status, that no candidate
was promoted into the nine-indicator canonical catalog, that the release notes
disclose scope, and that publishing needs an explicit manual dispatch.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.3.0"
TAG = "v0.3.0"
ATTESTATION = "source_only_v0.3.0_attestation.json"
WORKFLOW = ".github/workflows/v03-stable-software.yml"
# Pipeline scripts each candidate needs; a missing one blocks the release.
CANDIDATE_SCRIPTS = {
    "H47": ("prepare_population_0_11_v0_3.py", "check_posas_2026_source_v0_3.py",
            "audit_posas_h47_reproduction_v0_3.py"),
    "H50": ("normalize_h50_istat_sdmx_v0_3.py", "prepare_low_education_25_64_v0_3.py",
            "audit_h50_istat_independent_v0_3.py"),
    "H46": ("acquire_h46_istat_sdmx_v0_3.py", "normalize_h46_istat_sdmx_v0_3.py",
            "prepare_unemployment_15_plus_v0_3.py", "audit_h46_istat_independent_v0_3.py"),
    "H03": ("extract_nwioi_hdd_2025_v0_3.py", "prepare_hdd_eurostat_2025_v0_3.py"),
    "H04": ("prepare_cdd_eurostat_2025_v0_3.py",),
    "H05": ("prepare_v0_3_housing_candidates.py",),
    "ADD-HOUSING-01": ("prepare_v0_3_housing_candidates.py",),
}
SHARED_SCRIPTS = ("build_v0_3_visual_atlas.py", "check_v0_3_evidence.py",
                  "import_v0_3_evidence.py", "check_v0_2_stable_release.py")
# Statuses a software release may report. Anything implying approval is refused.
ALLOWED_CANDIDATE_STATUS = {
    "pipeline_only_no_real_data",
    "real_technical_preview_independently_audited",
    "real_technical_preview_independently_reproduced",
}
CANONICAL_INDICATORS = 9
EXPECTED = {
    "version": VERSION,
    "tag": TAG,
    "release_track": "software_source_only_stable",
    "publication_status": "stable_software_unapproved_territorial_results",
    "source_code_public": True,
    "scientific_validation": "not_asserted_by_software_release",
    "institutional_approval": "pending",
    "publish_local_pilot_or_v02_outputs": False,
    "publish_v03_previews_or_atlas": False,
    "publish_pdf_or_data_assets": False,
    "municipalities": 27,
    "independent_core_indicators": CANONICAL_INDICATORS,
    "canonical_catalog_changed": False,
    "candidates_promoted_to_canonical": 0,
    "no_composite_energy_poverty_score": True,
    "household_inference": False,
    "quarantined_cit_excluded": True,
    "previous_stable_tag": "v0.2.0",
}
NOTE_PHRASES = ("v0.3.0", "NON", "pending", "CIT", "27 Comuni", "uv run --locked",
                ATTESTATION, "technical_draft_do_not_publish", "config/indicators.json")


def check_versions(root: Path) -> None:
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    lock = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
    locked = [p["version"] for p in lock["package"]
              if p.get("name") == "epah-diagnosis" and p.get("source", {}).get("editable") == "."]
    package = (root / "src/epah_diagnosis/__init__.py").read_text(encoding="utf-8")
    if (project["project"]["version"] != VERSION or locked != [VERSION]
            or f'__version__ = "{VERSION}"' not in package):
        raise ValueError("Stable code, editable lock and package versions disagree")


def check_metadata(root: Path) -> dict:
    metadata = json.loads((root / "docs/releases/v0.3.0.json").read_text(encoding="utf-8"))
    if any(metadata.get(k) != v for k, v in EXPECTED.items()):
        raise ValueError("Stable software cannot assert scientific/institutional publication")
    candidates = metadata.get("candidates")
    if not isinstance(candidates, dict) or set(candidates) != set(CANDIDATE_SCRIPTS):
        raise ValueError(f"Release metadata must list exactly the candidates {sorted(CANDIDATE_SCRIPTS)}")
    for candidate, status in candidates.items():
        if status not in ALLOWED_CANDIDATE_STATUS:
            raise ValueError(f"Candidate {candidate} has a non-releasable status {status!r}")
    return candidates


def check_canonical(root: Path) -> None:
    catalog = json.loads((root / "config/indicators.json").read_text(encoding="utf-8"))
    ids = {item.get("id") for item in catalog.get("indicators", [])}
    if len(catalog.get("indicators", [])) != CANONICAL_INDICATORS:
        raise ValueError("Canonical catalog no longer has nine indicators")
    if ids & set(CANDIDATE_SCRIPTS):
        raise ValueError("A v0.3 candidate was promoted into the canonical catalog")
    config = json.loads((root / "config/report_v0_2.json").read_text(encoding="utf-8"))
    if (config.get("publication_status") != "technical_draft_do_not_publish"
            or config.get("approved_for_publication") is not False):
        raise ValueError("v0.2 report configuration must stay unpublishable")


def check_scripts(root: Path) -> None:
    needed = {s for scripts in CANDIDATE_SCRIPTS.values() for s in scripts} | set(SHARED_SCRIPTS)
    missing = sorted(s for s in needed if not (root / "scripts" / s).is_file())
    if missing:
        raise ValueError(f"Missing v0.3 software components: {missing}")


def check_notes_and_workflow(root: Path) -> None:
    notes = (root / "docs/releases/v0.3.0.md").read_text(encoding="utf-8")
    for phrase in NOTE_PHRASES:
        if phrase not in notes:
            raise ValueError(f"Stable software notes must disclose scope: {phrase}")
    workflow = (root / WORKFLOW).read_text(encoding="utf-8")
    if ("workflow_dispatch:" not in workflow
            or "\n  push:" in workflow or "\n  pull_request:" in workflow
            or "--prerelease" in workflow or ATTESTATION not in workflow
            or "github.ref == 'refs/heads/main'" not in workflow):
        raise ValueError("Stable software release must require an explicit manual dispatch on main")


def check(root: Path = ROOT) -> dict:
    check_versions(root)
    candidates = check_metadata(root)
    check_canonical(root)
    check_scripts(root)
    check_notes_and_workflow(root)
    return {
        "schema_version": "1.0", "version": VERSION, "tag": TAG,
        "source_only": True, "stable_software": True, "prerelease": False,
        "publication_authorized": False, "review_status": "pending",
        "core_municipalities": 27, "core_indicators": CANONICAL_INDICATORS,
        "candidates": candidates, "candidates_promoted_to_canonical": 0,
        "quarantined_cit_included": False, "attached_private_data": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only stable SOFTWARE-only v0.3.0 release readiness (not approval of data)")
    parser.add_argument("--commit-sha", help="40-character Git commit SHA on main")
    parser.add_argument("--json-out", type=Path, help="Write attestation to a NEW file")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
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
    print("Stable v0.3.0 SOFTWARE-only contract passed; candidates and territorial publication unapproved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
