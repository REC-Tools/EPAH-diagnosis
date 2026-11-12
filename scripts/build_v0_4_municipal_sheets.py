"""Generate 27 two-page A4 technical municipal profiles from a verified atlas and review."""
from __future__ import annotations

import argparse
from pathlib import Path

from epah_diagnosis.municipality_sheets_v0_4 import build


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--atlas-dir", required=True, type=Path)
    parser.add_argument("--review-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = build(args.atlas_dir, args.review_dir, args.out_dir)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, f"BLOCKED: {exc}\n")
    print(f"27 technical municipal sheets (2 A4 pages each, NOT FOR PUBLICATION): {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
