"""Prepare non-validated 27-municipality DEA I/II accessibility from original ZIPs.

Offline. Never writes to the canonical matrix or claims current hospital coverage.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from epah_diagnosis.dea_accessibility_qa import write_draft

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    p = argparse.ArgumentParser(description="Prepare reviewable ISTAT DEA road access draft")
    p.add_argument("--road-zip", required=True, type=Path,
                   help="Original ISTAT Piemonte road-distance matrix ZIP (2021 geography)")
    p.add_argument("--boundaries-zip", required=True, type=Path,
                   help="Original ISTAT 2026 municipality boundaries ZIP")
    p.add_argument("--hospitals", type=Path,
                   default=ROOT / "data/reference/piemonte_dea_hospitals.csv")
    p.add_argument("--registry", type=Path,
                   default=ROOT / "data/municipalities.csv")
    p.add_argument("--out-dir", type=Path,
                   default=ROOT / "outputs/quality/dea_accessibility")
    args = p.parse_args()
    report = write_draft(args.road_zip, args.boundaries_zip, args.hospitals,
                         args.registry, args.out_dir)
    print(
        f"DEA I/II draft: {report['origin_count']} origins x "
        f"{report['eligible_dea_municipality_count']} Piemonte DEA municipalities; "
        f"{report['route_pair_count']} audited routes. "
        "Technical QA only: hospital network, source and vintage review pending. "
        "Verification matrix unchanged."
    )


if __name__ == "__main__":
    main()
