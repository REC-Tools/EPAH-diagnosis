from __future__ import annotations

import argparse
import json
from pathlib import Path

from epah_diagnosis.source_monitor import render_markdown, run_checks


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "config" / "sources.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Check external data sources.")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument(
        "--fail-on-update",
        action="store_true",
        help="Return exit code 2 when a newer source version is detected.",
    )
    args = parser.parse_args()

    results = run_checks(args.registry)
    payload = [result.to_dict() for result in results]
    markdown = render_markdown(results)

    print(markdown)

    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(markdown + "\n", encoding="utf-8")

    if any(result.status == "error" for result in results):
        raise SystemExit(1)
    if args.fail_on_update and any(
        result.status == "update_available" for result in results
    ):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
