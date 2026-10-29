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
    ROOT / "docs/operational_guide.md",
    ROOT / "docs/script_reference.md",
    ROOT / "docs/quality_review_20261029.md",
    ROOT / "docs/indicator_catalog.md",
    ROOT / "docs/diagnostic_maps.md",
    ROOT / "docs/release_v0_1.md",
)
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
SCRIPT_REFERENCE = re.compile(r"(?<![\w/])scripts/[a-z0-9_]+\.py\b")


def problems_for_document(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return [f"{path.relative_to(ROOT)}: missing documentation file"]
    contents = path.read_text(encoding="utf-8")
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
