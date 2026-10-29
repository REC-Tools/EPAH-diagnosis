"""Review-gated publication of DEA I/II road accessibility.

No network downloads, no auto-validation. Explicit approval must cover the
limited Piemonte hospital reference and its 2023/2025 vintages.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from epah_diagnosis.dea_accessibility_qa import promote

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    p = argparse.ArgumentParser(description="Publish independently reviewed Piemonte DEA accessibility")
    p.add_argument("--road-zip", required=True, type=Path)
    p.add_argument("--boundaries-zip", required=True, type=Path)
    p.add_argument("--draft-dir", required=True, type=Path)
    p.add_argument("--approval", required=True, type=Path)
    p.add_argument("--hospitals", type=Path,
                   default=ROOT / "data/reference/piemonte_dea_hospitals.csv")
    p.add_argument("--registry", type=Path,
                   default=ROOT / "data/municipalities.csv")
    p.add_argument("--matrix", type=Path,
                   default=ROOT / "data/verification_matrix.csv")
    p.add_argument("--indicator-dir", type=Path,
                   default=ROOT / "data/indicators")
    a = p.parse_args()
    count = promote(a.road_zip, a.boundaries_zip, a.hospitals, a.registry,
                    a.draft_dir, a.approval, a.matrix, a.indicator_dir)
    print(f"Reviewed and promoted {count} Piemonte DEA accessibility rows")


if __name__ == "__main__":
    main()
