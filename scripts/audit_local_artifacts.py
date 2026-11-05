"""Read-only local Git inventory for EPAH data and generated artifacts.

The report is a triage aid, not a publication, license or scientific approval.
It never moves, deletes, stages, hashes or alters any source. Ignored inputs
are shown by directory to avoid scanning large/private original downloads.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCOPES = ("data", "artifacts", "outputs", "*.zip")


def category(relative: str) -> str:
    path = relative.replace("\\", "/")
    if path.startswith(("data/raw/", "data/downloads/")):
        return "local_originals_keep_private"
    if path.startswith("data/cache/"):
        return "regenerable_cache"
    if path.startswith(("outputs/", "artifacts/")):
        return "generated_or_qa_artifact"
    if path.startswith("data/derived/"):
        return "derived_needs_provenance_review"
    if path.startswith("data/geography/"):
        return "geography_needs_source_review"
    if path.startswith("data/indicators/"):
        return "indicator_needs_source_review"
    if path.startswith("data/reference/"):
        return "reference_needs_license_review"
    if path.endswith(".pre_indicator_id_migration.csv"):
        return "migration_backup_keep_local"
    if path.endswith(".zip"):
        return "archive_review_before_publication"
    return "other_data_requires_review"


def parse_porcelain(raw: bytes) -> list[tuple[str, str]]:
    """Parse NUL-delimited porcelain v1 including optional rename origins."""
    tokens = raw.decode("utf-8", errors="surrogateescape").split("\0")
    records: list[tuple[str, str]] = []
    index = 0
    while index < len(tokens) and tokens[index]:
        token = tokens[index]
        if len(token) < 4 or token[2] != " ":
            raise ValueError("Unexpected Git status porcelain format")
        state = token[:2]
        name = token[3:]
        if not name:
            raise ValueError("Git status entry has empty path")
        records.append((state, name))
        index += 1
        if "R" in state or "C" in state:
            if index >= len(tokens) or not tokens[index]:
                raise ValueError("Git rename/copy entry lacks origin")
            index += 1
    return records


def inventory(root: Path) -> dict:
    command = [
        "git", "status", "--porcelain=v1", "-z",
        "--untracked-files=all", "--ignored=matching",
        "--", *SCOPES,
    ]
    proc = subprocess.run(
        command, cwd=root, capture_output=True, check=False,
    )
    if proc.returncode != 0:
        error = proc.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError("Cannot inspect Git working tree: " + error)

    entries = []
    for status, relative in parse_porcelain(proc.stdout):
        path = root / relative
        if status == "??":
            tracking = "untracked"
        elif status == "!!":
            tracking = "ignored"
        else:
            tracking = "tracked_change"
        is_directory = path.is_dir() and not path.is_symlink()
        try:
            size = path.stat().st_size if path.is_file() and not path.is_symlink() else None
        except OSError:
            size = None
        entries.append({
            "path": relative.replace("\\", "/"),
            "tracking": tracking,
            "kind": "directory" if is_directory else "file_or_other",
            "bytes": size,
            "category": category(relative),
        })

    entries.sort(key=lambda x: x["path"])
    counts = Counter(item["tracking"] for item in entries)
    return {
        "schema_version": "1.0",
        "scope": "local Git working tree (selected data and artifact paths)",
        "scientific_validation": "not_assessed",
        "approval_for_publication": "not_assessed",
        "changes_made": False,
        "summary": {
            "untracked": counts["untracked"],
            "ignored": counts["ignored"],
            "tracked_change": counts["tracked_change"],
            "entries": len(entries),
        },
        "entries": entries,
        "notes": [
            "Ignored directories are summarized, not inventoried file by file.",
            "An untracked indicator or geometry file needs source and licensing review.",
            "No file is safe to delete or publish merely because of its category.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only inventory of local EPAH data and artifact paths"
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--json-out", type=Path,
        help="Write inventory to a NEW JSON file only (not overwritten)",
    )
    args = parser.parse_args()
    try:
        result = inventory(args.root)
        print("EPAH local inventory (no files modified)")
        for name, value in result["summary"].items():
            print(f"  {name}: {value}")
        for entry in result["entries"]:
            print(f"  {entry['tracking']:14} {entry['category']:35} {entry['path']}")
        if args.json_out is not None:
            # The report can include revealing local filenames; user controls
            # the destination. Never overwrite an existing report.
            args.json_out.parent.mkdir(parents=True, exist_ok=True)
            with args.json_out.open("x", encoding="utf-8") as out:
                json.dump(result, out, indent=2, ensure_ascii=False)
                out.write("\n")
            print(f"New report: {args.json_out}")
        return 0
    except (ValueError, OSError, FileExistsError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
