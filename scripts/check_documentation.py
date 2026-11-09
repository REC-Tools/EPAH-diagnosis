"""Offline checks for links and script references in current operational docs.

Only local Markdown destinations are checked; network URLs and heading anchors
are intentionally outside scope. No project files are changed by this check.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = (
    ROOT / "README.md",
    ROOT / "docs/index.md",
    ROOT / "docs/operational_guide.md",
    ROOT / "docs/script_reference.md",
    ROOT / "docs/v0_1_owner_accepted_release.md",
    ROOT / "docs/release_v0_1_scope_27.md",
    ROOT / "docs/archive/README.md",
    ROOT / "docs/indicator_catalog.md",
    ROOT / "docs/diagnostic_maps.md",
    ROOT / "docs/release_v0_1.md",
    ROOT / "docs/framework.md",
    ROOT / "docs/pipeline.md",
    ROOT / "docs/indicator_completion_criteria.md",
    ROOT / "docs/data_contract.md",
    ROOT / "docs/provenance.md",
    ROOT / "docs/automated_technical_pipeline.md",
    ROOT / "docs/releases/v0.2.0.md",
    ROOT / "docs/releases/v0.3.0.md",
    ROOT / "docs/v0_3_visual_atlas.md",
    ROOT / "docs/v0_3_h03_annual_hdd_candidate.md",
    ROOT / "docs/v0_3_h03_nwioi_netcdf_extraction.md",
)
# Detect specific superseded release assertions in CURRENT documentation only.
# Dated archive/review material is intentionally excluded from this check.
CURRENT_STATUS_DOCUMENTS = frozenset({
    ROOT / "README.md",
    ROOT / "docs/index.md",
    ROOT / "docs/operational_guide.md",
    ROOT / "docs/framework.md",
    ROOT / "docs/pipeline.md",
    ROOT / "docs/indicator_completion_criteria.md",
    ROOT / "docs/data_contract.md",
    ROOT / "docs/provenance.md",
    ROOT / "docs/diagnostic_maps.md",
    ROOT / "docs/script_reference.md",
})
STALE_RELEASE_CLAIMS = (
    re.compile(r"\bcatalogo\s+(?:metodologico\s+)?di\s+otto\s+voci\b", re.I),
    re.compile(r"\bmatrice\s+(?:applicativa\s+)?(?:attuale\s+)?(?:contiene|di)\s+81\s+righe\b", re.I),
    re.compile(r"\bmaturit[aà]\s+.*?\b(?:PR\s+B|non\s+ancora\s+implementata)\b", re.I),
    re.compile(r"(?<![\w/])scripts/(?:build_municipality_comparison|build_multidimensional_overlap|generate_overlap_map)\.py\b"),
)


def stale_release_claims(contents: str) -> list[str]:
    return [f"outdated current-release assertion: {pattern.pattern}"
            for pattern in STALE_RELEASE_CLAIMS if pattern.search(contents)]


MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
SCRIPT_REFERENCE = re.compile(r"(?<![\w/])scripts/(?:[a-z0-9_]+/)*[a-z0-9_]+\.py\b")


def problems_for_document(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return [f"{path.relative_to(ROOT)}: missing documentation file"]
    contents = path.read_text(encoding="utf-8")
    if path in CURRENT_STATUS_DOCUMENTS:
        errors.extend(f"{path.relative_to(ROOT)}: {message}"
                      for message in stale_release_claims(contents))
    for match in MARKDOWN_LINK.finditer(contents):
        dest = match.group(1).split()[0].split("#", 1)[0]
        if not dest or dest.startswith(("https://", "http://", "mailto:", "#")):
            continue
        target = (path.parent / dest).resolve()
        if not target.is_relative_to(ROOT) or not target.exists():
            errors.append(f"{path.relative_to(ROOT)}: invalid local link {dest!r}")
    for match in SCRIPT_REFERENCE.finditer(contents):
        dest = match.group(0)
        if not (ROOT / dest).is_file():
            errors.append(f"{path.relative_to(ROOT)}: missing script {dest}")
    return errors


def main() -> int:
    errors = [error for file in DOCUMENTS for error in problems_for_document(file)]
    if errors:
        for error in errors:
            print("ERROR:", error)
        return 1
    print(f"Documentation references valid ({len(DOCUMENTS)} pages, offline).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
