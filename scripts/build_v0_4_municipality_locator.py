"""Build an A4 locator of all 27 municipalities, without thematic values."""
from __future__ import annotations

import argparse
from pathlib import Path

from epah_diagnosis.municipality_locator_v0_4 import build

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--geojson", required=True, type=Path,
                        help="Audited pilot municipality_profile.geojson, CRS84/WGS84")
    parser.add_argument("--registry", type=Path, default=ROOT / "data/municipalities.csv")
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = build(args.geojson, args.registry, args.out_dir)
    except (OSError, KeyError, ValueError, TypeError) as exc:
        parser.exit(2, f"BLOCKED: {exc}\n")
    print(f"27-municipality locator (TECHNICAL DRAFT): {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
