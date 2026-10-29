"""Compare the 27 municipal climate rows with a historical official annex.

This is non-destructive and does not change verification_matrix.csv.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from epah_diagnosis.climate_verification import compare_reference


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REFERENCE = ROOT / "data/reference/climate_dpr412_green_community.csv"
DEFAULT_HISTORICAL = ROOT / "data/reference/climate_dpr412_official_2008_transcription.csv"
DEFAULT_REPORT = ROOT / "outputs/quality/heating_degree_days_comparison.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Independent historical annex comparison")
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument("--historical", type=Path, default=DEFAULT_HISTORICAL)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    if args.output.resolve() in {args.snapshot.resolve(), args.historical.resolve()}:
        parser.error("Output cannot overwrite reference inputs")
    result = compare_reference(args.snapshot, args.historical)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(f"Climate checks: {result['municipalities']} municipalities")
    print(f"Heating degree day mismatches: {len(result['value_mismatches'])}")
    print(f"Climate zone mismatches: {len(result['zone_mismatches'])}")
    print(f"Ancillary altitude discrepancies: {len(result['altitude_mismatches'])}")
    print("Legal version 2016: human review required before validation.")
    print(f"Report: {args.output}")
    if not result["gg_zone_comparison_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
