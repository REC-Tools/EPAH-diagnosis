"""Review-gated publication of SNAI 2020 classification.

Usage: prepare_territorial_context.py -> human QA -> this script.
No implicit downloads or unreviewed promotion.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from epah_diagnosis.territorial_context_qa import promote

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish reviewed SNAI classes A-F (2020)")
    parser.add_argument("--source-xlsx", type=Path, required=True)
    parser.add_argument("--draft-dir", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=ROOT / "data/municipalities.csv")
    parser.add_argument("--matrix", type=Path, default=ROOT / "data/verification_matrix.csv")
    parser.add_argument("--indicator-dir", type=Path, default=ROOT / "data/indicators")
    args = parser.parse_args()
    count = promote("snai_classification", args.source_xlsx, args.registry, args.draft_dir,
                    args.approval, args.matrix, args.indicator_dir)
    print(f"Promoted {count} independently reviewed categorical SNAI observations")


if __name__ == "__main__":
    main()
