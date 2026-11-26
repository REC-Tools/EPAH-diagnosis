"""Fail-closed v0.5.0 SOFTWARE-only release contract, never territorial approval."""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.5.0"
TAG = "v0.5.0"
ATTESTATION = "source_only_v0.5.0_attestation.json"
WORKFLOW = ".github/workflows/v05-stable-software.yml"
EXPECTED = {
    "version": VERSION, "tag": TAG, "release_track": "software_source_only_stable",
    "publication_status": "stable_software_unapproved_territorial_results",
    "source_code_public": True, "scientific_validation": "not_asserted_by_software_release",
    "institutional_approval": "pending", "publish_territorial_outputs": False,
    "publish_pdf_or_data_assets": False, "allowed_release_assets": [ATTESTATION],
    "municipalities": 27, "independent_core_indicators": 9, "visual_atlas_slots": 16,
    "canonical_catalog_changed": False, "candidates_promoted_to_canonical": 0,
    "territorial_snapshot_complete": False, "no_composite_energy_poverty_score": True,
    "household_inference": False, "quarantined_cit_excluded": True, "previous_stable_tag": "v0.4.0",
}
STATUSES = {
    "H47": "real_technical_preview_independently_reproduced",
    "H50": "real_technical_preview_independently_audited",
    "H46": "real_technical_preview_independently_audited",
    "H03": "originals_available_method_decision_pending",
    "H04": "originals_available_method_decision_pending",
    "H05": "residential_municipal_source_missing",
    "ADD-HOUSING-01": "real_technical_preview_human_mapping_review_pending",
}


SELECTED_DELIVERY = {
    'profile': 'selected-20261126', 'active_candidates': ['V05-03', 'V05-19'],
    'rental_reference_year': 2021, 'heat_reference_year': 2025,
    'heat_scope': 'source_grid_cell', 'heat_thresholds_celsius': [26, 32, 38, 46],
    'heat_threshold_operator': '>', 'municipal_heat_aggregation': False,
    'included_in_release': False, 'publication_allowed': False,
}


def check(root: Path = ROOT) -> dict:
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    lock = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
    versions = [p["version"] for p in lock["package"]
                if p.get("name") == "epah-diagnosis" and p.get("source", {}).get("editable") == "."]
    package = (root / "src/epah_diagnosis/__init__.py").read_text(encoding="utf-8")
    if (project["project"]["version"] != VERSION or versions != [VERSION]
            or f'__version__ = "{VERSION}"' not in package):
        raise ValueError("Code, lock and package versions must all be 0.5.0")
    metadata = json.loads((root / "docs/releases/v0.5.0.json").read_text(encoding="utf-8"))
    if (metadata.get("selected_delivery") != SELECTED_DELIVERY
            or any(metadata.get(key) != value for key, value in EXPECTED.items())
            or metadata.get("candidates") != STATUSES
            or metadata.get("documented_local_snapshot") != {
                "available_series": 13, "pending": ["H03", "H04", "H05"],
                "scientific_approval": False, "included_in_release": False}
            or metadata.get("v05_proposals") != {
                "contracts": 23, "municipal_series_added": 0, "scientific_approval": False}):
        raise ValueError("Source-only release scope or approval states disagree")
    # Reuse the existing protections without relaxing the historical version gate.
    spec = importlib.util.spec_from_file_location("v03_release_integrity", root / "scripts/check_v0_3_release.py")
    integrity = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(integrity)
    integrity.check_canonical(root)
    integrity.check_scripts(root)
    required = ("review_workflow_v0_4.py", "visual_atlas_v0_4.py", "review_pack_v0_4.py",
                "output_hub_v0_4.py", "synthetic_example_v0_4.py", "methodology_v0_5.py",
                "indicator_dashboard_v0_5.py", "heat_grid_v0_5.py",
                "utci_heat_source_v0_5.py", "rent_decision_v0_5.py")
    if any(not (root / "src/epah_diagnosis" / name).is_file() for name in required):
        raise ValueError("Missing v0.5 software components")
    # The delivery profile changes presentation, never the original indicator contracts.
    catalogs = [json.loads((root / "docs" / name).read_text(encoding="utf-8"))
                for name in ("v0_5_indicator_contracts.json", "v0_5_housing_contracts.json")]
    ids = [item["id"] for doc in catalogs for item in doc["indicators"]]
    if len(ids) != 23 or set(ids) != {f"V05-{i:02}" for i in range(1, 24)}:
        raise ValueError("Release requires the unchanged complete proposal inventory")
    tree = ast.parse((root / "src/epah_diagnosis/indicator_dashboard_v0_5.py").read_text(encoding="utf-8"))
    constants = {target.id: ast.literal_eval(node.value) for node in tree.body
                 if isinstance(node, ast.Assign) for target in node.targets
                 if isinstance(target, ast.Name) and target.id in {"CLOSEOUT_IDS", "CLOSEOUT_PROFILE"}}
    if (constants.get("CLOSEOUT_IDS") != set(SELECTED_DELIVERY["active_candidates"])
            or constants.get("CLOSEOUT_PROFILE") != SELECTED_DELIVERY["profile"]):
        raise ValueError("Selected delivery metadata and software disagree")
    notes = (root / "docs/releases/v0.5.0.md").read_text(encoding="utf-8")
    for phrase in (TAG, ATTESTATION, "technical_draft_do_not_publish", "pending", "CIT", "27 Comuni"):
        if phrase not in notes:
            raise ValueError(f"Release notes must disclose scope: {phrase}")
    workflow = (root / WORKFLOW).read_text(encoding="utf-8")
    if ("workflow_dispatch:" not in workflow or re.search(r"^  (push|pull_request|schedule|workflow_run):", workflow, re.M)
            or "github.ref == 'refs/heads/main'" not in workflow or "--prerelease" in workflow
            or 'test "$EXPECTED_SHA" = "$GITHUB_SHA"' not in workflow
            or 'test "$tag_sha" = "$GITHUB_SHA"' not in workflow
            or f'gh release create "$TAG" {ATTESTATION}' not in workflow
            or "uv run --locked pytest -q" not in workflow or "gh release download" not in workflow):
        raise ValueError("Release must be manual, main-only, exact-commit and source-only")
    for action in re.findall(r"uses: (\S+)", workflow):
        if not re.fullmatch(r"[\w/-]+@[0-9a-f]{40}", action):
            raise ValueError("Release actions must be pinned by commit")
    return {"schema_version": "1.0", "version": VERSION, "tag": TAG,
            "source_only": True, "stable_software": True, "prerelease": False,
            "publication_authorized": False, "scientific_approval": False,
            "institutional_approval": "pending", "attached_private_data": False,
            "core_municipalities": 27, "core_indicators": 9, "visual_atlas_slots": 16,
            "candidates_promoted_to_canonical": 0, "quarantined_cit_included": False,
            "territorial_snapshot_complete": False, "candidates": STATUSES,
            "proposal_contracts": 23, "selected_delivery": SELECTED_DELIVERY,
            "uv_lock_sha256": hashlib.sha256((root / "uv.lock").read_bytes()).hexdigest(),
            "release_metadata_sha256": hashlib.sha256((root / "docs/releases/v0.5.0.json").read_bytes()).hexdigest()}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--commit-sha")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    try:
        result = check(args.root)
        if args.commit_sha is not None:
            if not re.fullmatch(r"[0-9a-f]{40}", args.commit_sha):
                raise ValueError("Commit SHA must contain 40 lowercase hex characters")
            result["git_commit_sha"] = args.commit_sha
        if args.json_out is not None:
            if args.commit_sha is None:
                raise ValueError("A release attestation must name its commit")
            args.json_out.parent.mkdir(parents=True, exist_ok=True)
            with args.json_out.open("x", encoding="utf-8") as stream:
                json.dump(result, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 1
    print("Stable v0.5.0 SOFTWARE-only release contract passed; territorial publication pending.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
