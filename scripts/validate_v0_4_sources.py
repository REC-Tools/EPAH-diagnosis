"""Offline evidence replay for H03/H04 and H05; no scientific approval."""
from __future__ import annotations

import argparse
from pathlib import Path

from epah_diagnosis.source_validation_v0_4 import assess, publish_report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=Path("data/municipalities.csv"))
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--require", choices=("both", "climate", "h05"), default="both",
                        help="Required independent technical replays; never a scientific approval")
    parser.add_argument("--climate-daily", type=Path)
    parser.add_argument("--h03-dir", type=Path)
    parser.add_argument("--h04-dir", type=Path)
    parser.add_argument("--tmin-netcdf", type=Path)
    parser.add_argument("--tmax-netcdf", type=Path)
    parser.add_argument("--mask-netcdf", type=Path)
    parser.add_argument("--boundaries", type=Path)
    parser.add_argument("--extraction-qa", type=Path)
    parser.add_argument("--h05-normalized", type=Path)
    parser.add_argument("--h05-original", type=Path)
    parser.add_argument("--h05-dir", type=Path)
    args = parser.parse_args(argv)
    climate = {
        "daily": args.climate_daily, "h03_dir": args.h03_dir, "h04_dir": args.h04_dir,
        "tmin": args.tmin_netcdf, "tmax": args.tmax_netcdf,
        "mask": args.mask_netcdf, "boundaries": args.boundaries,
        "extraction_qa": args.extraction_qa,
    }
    housing = {"normalized": args.h05_normalized, "original": args.h05_original,
               "h05_dir": args.h05_dir}
    climate = {k: v for k, v in climate.items() if v is not None}
    housing = {k: v for k, v in housing.items() if v is not None}
    try:
        report = assess(args.registry, climate=climate or None, h05=housing or None)
        out_dir = publish_report(args.out_dir, report)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f"BLOCKED: {exc}\n")
    required = ("climate_h03_h04", "residential_h05") if args.require == "both" else (
        "climate_h03_h04",) if args.require == "climate" else ("residential_h05",)
    passed = all(report[key]["status"] == "technical_replay_passed_review_pending" for key in required)
    print(f"Validation report (scientific_approval=false): {out_dir / 'validation.json'}")
    for key in ("climate_h03_h04", "residential_h05"):
        print(f"  {key}: {report[key]['status']}")
    if not passed:
        parser.exit(2, "BLOCKED: one or more required original-source technical replays are missing\n")
    print("TECHNICAL REPLAY PASSED; independent source mapping and scientific approval remain pending")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
