"""Acquire the shared official road/geography and MIM inputs for access QA.

No municipality observations are generated or promoted here. Use the existing
prepare_dea_accessibility.py and prepare_education_rail_access.py afterwards.

Examples on Windows:
  python scripts/acquire_accessibility_inputs.py --download --sources road,boundaries
  python scripts/acquire_accessibility_inputs.py --download --sources school_registry,school_pathways --out-dir outputs/quality/access_input_mim
  python scripts/acquire_accessibility_inputs.py --road-zip C:\Dati\Piemonte.zip --boundaries-zip C:\Dati\Limiti01012026_g.zip
"""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from epah_diagnosis.accessibility_source_intake import (
    HEALTH_PAGE, ROAD_PAGE, SCHOOL_REGISTRY_PAGE, SCHOOL_PATHWAYS_PAGE,
    SOURCE_SPECS, download_original, inspect_local,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/quality/accessibility_input_intake"
LOCAL_INPUT_KEYS = {
    "road": "road_zip",
    "boundaries": "boundaries_zip",
    "school_registry": "school_registry",
    "school_pathways": "school_pathways",
}


def run(
    out_dir: Path,
    *,
    selected: tuple[str, ...],
    download: bool = False,
    local: dict[str, Path] | None = None,
) -> dict:
    if not selected:
        raise ValueError("Select at least one original source")
    if len(set(selected)) != len(selected) or any(k not in SOURCE_SPECS for k in selected):
        raise ValueError("Sources must be distinct known source IDs")
    local = local or {}
    if out_dir.exists() and (out_dir / "audit.json").exists():
        raise FileExistsError("Existing audit: use a fresh --out-dir")
    out_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "scope": "Technical original-input preflight for 27 municipality accessibility proxies",
        "published_source_pages": {
            "road": ROAD_PAGE,
            "boundaries": SOURCE_SPECS["boundaries"]["url"],
            "school_registry": SCHOOL_REGISTRY_PAGE,
            "school_pathways": SCHOOL_PATHWAYS_PAGE,
            "dea_2025": HEALTH_PAGE,
        },
        "original_source_results": {},
        "target_indicators": [
            "dea_accessibility", "upper_secondary_accessibility",
            "rail_accessibility",
        ],
        "matrix_modified": False,
        "automatic_promotions": 0,
        "service_eligibility_reviewed": False,
        "out_of_region_coverage_reviewed": False,
        "travel_times_verified": False,
        "validated_for_release": False,
    }
    for key in selected:
        source = local.get(key)
        result = None
        try:
            if source is not None:
                result = inspect_local(key, source)
                result["status"] = "technical_preflight_pass"
            elif download:
                target = out_dir / "raw" / SOURCE_SPECS[key]["file"]
                result = download_original(key, target)
                result["local_original_path"] = str(target)
                result["status"] = "technical_preflight_pass"
            else:
                result = {"status": "not_acquired",
                          "source_url": SOURCE_SPECS[key]["url"]}
        except (OSError, ValueError, RuntimeError) as exc:
            result = {"status": "blocked", "source_url": SOURCE_SPECS[key]["url"],
                      "error": f"{type(exc).__name__}: {exc}"}
        data["original_source_results"][key] = result
    data["technical_pass_count"] = sum(
        x["status"] == "technical_preflight_pass"
        for x in data["original_source_results"].values()
    )
    data["selected_source_count"] = len(selected)
    data["all_selected_inputs_available"] = data["technical_pass_count"] == len(selected)
    data["next_checks_required"] = [
        "Review original file provenance, acquisition date and open-data licences.",
        "Run all three service-specific preparers with full 27×N route coverage.",
        "Confirm eligible DEA I/II from the 2025 Health Ministry dataset.",
        "Compare MIM school offer 2024/25 against 2026/27 school registry.",
        "Verify active rail timetable and bus substitutions at reporting date.",
        "Review 2021-to-2026 municipality code crosswalk and out-of-region destinations.",
        "Register independent route samples, person, date and HTTPS evidence before promotion.",
    ]
    (out_dir / "audit.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return data


def main() -> None:
    p = argparse.ArgumentParser(
        description="Acquire original ISTAT road/boundaries and MIM school inputs; no data promotion"
    )
    p.add_argument("--download", action="store_true", help="Download selected official originals")
    p.add_argument("--sources", default="road,boundaries",
                   help="Comma-separated source IDs: road,boundaries,school_registry,school_pathways")
    p.add_argument("--road-zip", type=Path, help="Use original downloaded Piemonte.zip")
    p.add_argument("--boundaries-zip", type=Path, help="Use original ISTAT 2026 boundaries ZIP")
    p.add_argument("--school-registry", type=Path, help="Use original MIM 2024/25 registry CSV")
    p.add_argument("--school-pathways", type=Path, help="Use original MIM 2024/25 pathways CSV")
    p.add_argument("--out-dir", type=Path, default=OUT)
    p.add_argument("--strict", action="store_true", help="Exit 1 on any blocked/unacquired source")
    args = p.parse_args()
    local = {
        source: getattr(args, flag)
        for source, flag in LOCAL_INPUT_KEYS.items()
        if getattr(args, flag) is not None
    }
    selected = tuple(x.strip() for x in args.sources.split(","))
    # Explicit local-file arguments are always inspected, even if omitted from
    # --sources (avoids accidentally skipping a human-supplied original).
    selected = tuple(dict.fromkeys((*selected, *local)))
    report = run(args.out_dir, selected=selected, download=args.download, local=local)
    print("EPAH official accessibility source intake — technical preflight only")
    for name, item in report["original_source_results"].items():
        detail = f" - {item['error']}" if item.get("error") else ""
        print(f"  {name}: {item['status']}{detail}")
    print(f"Official source preflights passed: {report['technical_pass_count']}/{report['selected_source_count']}")
    print(f"Report: {args.out_dir / 'audit.json'}")
    print("No 27×N access times measured; the verification matrix is unchanged.")
    if args.strict and not report["all_selected_inputs_available"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
