"""CLI for private nonpublishable v0.2 editorial review package."""
from __future__ import annotations

import argparse
from pathlib import Path

from epah_diagnosis.review_package_v0_2 import build

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "outputs/v0.1.0-pilot"
REPORT = ROOT / "outputs/v0.2-territorial-technical"
SHEETS = ROOT / "outputs/v0.2-municipal-sheets"
ANALYSIS = ROOT / "outputs/v0.2-multidimensional-analysis"
DASHBOARD = ROOT / "outputs/v0.2-offline-dashboard"
OUT = ROOT / "outputs/v0.2-review-candidate"


def main() -> int:
    p = argparse.ArgumentParser(
        description="Prepare verified v0.2 internal review ZIP, not an institutional release"
    )
    p.add_argument("--bundle", type=Path, default=BUNDLE)
    p.add_argument("--report-dir", type=Path, default=REPORT)
    p.add_argument("--sheets-dir", type=Path, default=SHEETS)
    p.add_argument("--analysis-dir", type=Path, default=ANALYSIS)
    p.add_argument("--dashboard-dir", type=Path, default=DASHBOARD)
    p.add_argument("--out-dir", type=Path, default=OUT)
    p.add_argument("--registry", type=Path, default=ROOT / "data/municipalities.csv")
    p.add_argument("--release-config", type=Path, default=ROOT / "config/release_v0_1.json")
    args = p.parse_args()
    try:
        result = build(
            args.bundle, args.report_dir, args.sheets_dir, args.analysis_dir,
            args.dashboard_dir, args.out_dir, args.registry, args.release_config,
        )
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"BLOCKED: {exc}")
        return 1
    print("V0.2 technical review candidate:", result)
    print("NOT APPROVED FOR PUBLICATION. Manual checklist is entirely pending.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
