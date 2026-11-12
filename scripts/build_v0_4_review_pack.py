"""Produce one technical-only HTML/CSV/PDF review pack from a verified atlas."""
from __future__ import annotations

import argparse
from pathlib import Path

from epah_diagnosis.review_pack_v0_4 import build

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--atlas-dir", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=ROOT / "data/municipalities.csv")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = build(args.atlas_dir, args.registry, args.out_dir)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, f"BLOCKED: {exc}\n")
    print(f"v0.4 technical review pack (NOT FOR PUBLICATION): {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
