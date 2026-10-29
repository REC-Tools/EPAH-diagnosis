"""Review-gated publication of ISTAT municipal mean altitude.

Usage: prepare_territorial_context.py -> human QA -> this script.
No implicit downloads or unreviewed promotion.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from epah_diagnosis.territorial_context_qa import promote

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish reviewed ISTAT mean altitude 2021")
    parser.add_argument("--source-xlsx", type=Path, required=True)
    parser.add_argument("--draft-dir", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=ROOT / "data/municipalities.csv")
    parser.add_argument("--matrix", type=Path, default=ROOT / "data/verification_matrix.csv")
    parser.add_argument("--indicator-dir", type=Path, default=ROOT / "data/indicators")
    args = parser.parse_args()
    count = promote("mean_altitude", args.source_xlsx, args.registry, args.draft_dir,
                    args.approval, args.matrix, args.indicator_dir)
    print(f"Promoted {count} independently reviewed mean-altitude observations")


if __name__ == "__main__":
    main()
