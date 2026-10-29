"""Local preview wrapper; the official release uses the same map renderer."""
from __future__ import annotations
import json
from pathlib import Path
from epah_diagnosis.release_artifacts import draw_maps

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "derived" / "municipality_profile.geojson"
OUTPUT_DIR = ROOT / "outputs" / "maps"

def main() -> None:
    if not INPUT.exists():
        raise FileNotFoundError(f"Missing {INPUT}. Build municipality GeoJSON first.")
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    names = draw_maps(data, OUTPUT_DIR)
    print("PREVIEW ONLY - not an approved release")
    for name in names:
        print(f"Created: {OUTPUT_DIR / Path(name).name}")

if __name__ == "__main__":
    main()
