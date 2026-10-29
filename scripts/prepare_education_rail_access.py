"""Produce audit-ready, unvalidated school or rail road-access drafts from local files."""
from __future__ import annotations

import argparse
from pathlib import Path
from epah_diagnosis.education_rail_access_qa import INDICATORS, write_draft

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    p = argparse.ArgumentParser(description="Prepare unvalidated school/rail accessibility drafts")
    p.add_argument("--indicator", required=True, choices=sorted(INDICATORS))
    p.add_argument("--road-zip", required=True, type=Path)
    p.add_argument("--boundaries-zip", required=True, type=Path)
    p.add_argument("--registry", type=Path, default=ROOT / "data/municipalities.csv")
    p.add_argument("--school-registry", type=Path)
    p.add_argument("--school-pathways", type=Path)
    p.add_argument("--rail-gateways", type=Path,
                   default=ROOT / "data/reference/canavese_active_rail_gateways.csv")
    p.add_argument("--out-dir", type=Path)
    a = p.parse_args()
    if a.indicator == "upper_secondary_accessibility":
        if a.school_registry is None or a.school_pathways is None:
            p.error("School indicator requires --school-registry and --school-pathways CSV")
        sources = {"school_registry": a.school_registry, "school_pathways": a.school_pathways}
    else:
        sources = {"rail_gateways": a.rail_gateways}
    output = a.out_dir or ROOT / "outputs/quality" / a.indicator
    report = write_draft(
        a.indicator, a.road_zip, a.boundaries_zip, a.registry, output, **sources
    )
    print(
        f"Unvalidated {a.indicator}: {report['origin_count']}/27 municipalities, "
        f"{report['destination_municipality_count']} destination municipalities, "
        f"{report['complete_route_pairs']} verified matrix pairs. "
        "Only technical QA; canonical matrix unchanged."
    )


if __name__ == "__main__":
    main()
