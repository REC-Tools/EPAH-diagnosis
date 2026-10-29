"""Legacy overlap-map preview, now using canonical metric cartography."""
from __future__ import annotations
import json
from pathlib import Path
from epah_diagnosis.cartography import render_thematic_map

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "derived" / "municipality_overlap.geojson"
OUTPUT = ROOT / "outputs" / "maps" / "map_multidimensional_overlap.png"

def main() -> None:
    if not INPUT.exists():
        raise FileNotFoundError(f"Missing {INPUT}. Build multidimensional overlap first.")
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    colors = {"0": "#ffffcc", "1": "#feb24c", "2": "#f03b20", "3": "#bd0026"}
    render_thematic_map(
        data, "vulnerability_overlap_count",
        "Sovrapposizione dei segnali di vulnerabilita territoriale",
        "dimensioni", OUTPUT, category_colors=colors,
        category_labels={key: f"{key} dimensioni" for key in colors},
        footer="ANTEPRIMA | 3 proxy | Non e una misura di poverta energetica",
    )
    print(f"Created preview: {OUTPUT}")

if __name__ == "__main__":
    main()
