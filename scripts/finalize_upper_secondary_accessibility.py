"""Review-gated finalizer: never download or automatically validate services."""
from __future__ import annotations

import argparse
from pathlib import Path
from epah_diagnosis.education_rail_access_qa import promote

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    p = argparse.ArgumentParser(description="Review-gated upper_secondary_accessibility accessibility promotion")
    p.add_argument("--road-zip", type=Path, required=True)
    p.add_argument("--boundaries-zip", type=Path, required=True)
    p.add_argument("--draft-dir", type=Path, required=True)
    p.add_argument("--approval", type=Path, required=True)
    p.add_argument("--registry", type=Path, default=ROOT / "data/municipalities.csv")
    p.add_argument("--school-registry", type=Path)
    p.add_argument("--school-pathways", type=Path)
    p.add_argument("--rail-gateways", type=Path,
                   default=ROOT / "data/reference/canavese_active_rail_gateways.csv")
    p.add_argument("--matrix", type=Path, default=ROOT / "data/verification_matrix.csv")
    p.add_argument("--indicator-dir", type=Path, default=ROOT / "data/indicators")
    a = p.parse_args()
    if "upper_secondary_accessibility" == "upper_secondary_accessibility":
        if a.school_registry is None or a.school_pathways is None:
            p.error("School indicator requires --school-registry and --school-pathways")
        sources = {"school_registry": a.school_registry, "school_pathways": a.school_pathways}
    else:
        sources = {"rail_gateways": a.rail_gateways}
    updated = promote(
        "upper_secondary_accessibility", a.road_zip, a.boundaries_zip, a.registry,
        a.draft_dir, a.approval, a.matrix, a.indicator_dir, **sources
    )
    print(f"Promoted {updated} independently reviewed upper_secondary_accessibility rows")


if __name__ == "__main__":
    main()
