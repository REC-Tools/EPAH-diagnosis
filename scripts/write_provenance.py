"""Create a draft provenance manifest for an existing local artifact, offline."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from epah_diagnosis.provenance import build_manifest

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Draft SHA-256 provenance manifest")
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--indicator-id", required=True)
    parser.add_argument("--reference-year", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--source-file", action="append", default=[],
                        help="source_id=/local/path (may be repeated)")
    parser.add_argument("--git-commit")
    parser.add_argument("--entrypoint")
    args = parser.parse_args()

    if args.output.exists():
        parser.error(f"Refusing to overwrite existing provenance manifest: {args.output}")
    mappings = {}
    for pair in args.source_file:
        if "=" not in pair:
            parser.error("--source-file must be source_id=/path")
        identifier, path = pair.split("=", 1)
        if not identifier or not path or identifier in mappings:
            parser.error("Duplicate or empty --source-file identifier/path")
        mappings[identifier] = Path(path)
    inputs = {args.artifact.resolve(), *(path.resolve() for path in mappings.values())}
    if args.output.resolve() in inputs:
        parser.error("Output must not replace an input file")
    try:
        result = build_manifest(
            args.artifact, args.indicator_id, ROOT / "config/indicators.json",
            ROOT / "config/sources.json", reference_year=args.reference_year,
            source_files=mappings, git_commit=args.git_commit, entrypoint=args.entrypoint,
        )
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Draft manifest saved: {args.output} (QA not assessed)")


if __name__ == "__main__":
    main()
