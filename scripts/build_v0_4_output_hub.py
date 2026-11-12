"""Package verified atlas and technical review into one offline v0.4 output hub."""
from __future__ import annotations

import argparse
from pathlib import Path

from epah_diagnosis.output_hub_v0_4 import build


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--atlas-dir", type=Path, required=True)
    parser.add_argument("--review-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = build(args.atlas_dir, args.review_dir, args.out_dir)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, f"BLOCKED: {exc}\n")
    print(f"Output hub (TECHNICAL DRAFT - NOT FOR PUBLICATION): {result / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
