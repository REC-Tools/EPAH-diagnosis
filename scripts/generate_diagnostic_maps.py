"""Preview only: absolute and relative diagnostic maps on existing GeoJSON."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from epah_diagnosis.release_artifacts import draw_maps

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "outputs/v0.1.0-pilot/municipality_profile.geojson"
OUTPUT_DIR = ROOT / "outputs/maps_v0_2"

def main() -> None:
    p = argparse.ArgumentParser(description="Generate v0.2 municipal map previews")
    p.add_argument("--input", type=Path, default=INPUT)
    p.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    p.add_argument("--map-mode", choices=("absolute","relative","both"), default="both")
    p.add_argument("--relative-unit", choices=("auto","difference",
                                                "percentage_points","percent_change"),
                   default="auto")
    a = p.parse_args()
    if not a.input.exists():
        raise FileNotFoundError(f"Missing {a.input}. Supply an enriched 27-town GeoJSON.")
    if a.output_dir.exists() and any(a.output_dir.iterdir()):
        raise FileExistsError("Use a fresh --output-dir to preserve previous map sets")
    names = draw_maps(json.loads(a.input.read_text(encoding="utf-8")),
                      a.output_dir, map_mode=a.map_mode, relative_unit=a.relative_unit)
    print("PREVIEW ONLY - no source data or canonical approval changed")
    print("Relative grey = 27-town mean; green better, red worse")
    for name in names:
        print("Created:", a.output_dir / Path(name).name)

if __name__ == "__main__":
    main()
