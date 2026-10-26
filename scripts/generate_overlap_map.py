from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Polygon


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "derived" / "municipality_overlap.geojson"
OUTPUT = ROOT / "outputs" / "maps" / "map_multidimensional_overlap.png"


def polygon_rings(geometry: dict):
    if geometry["type"] == "Polygon":
        yield geometry["coordinates"]
    elif geometry["type"] == "MultiPolygon":
        yield from geometry["coordinates"]
    else:
        raise ValueError(f"Unsupported geometry type: {geometry['type']}")


def main() -> None:
    if not INPUT.exists():
        raise FileNotFoundError(
            f"Missing {INPUT}. Run build_multidimensional_overlap.py first."
        )

    data = json.loads(INPUT.read_text(encoding="utf-8"))
    cmap = plt.get_cmap("YlOrRd", 4)

    fig, ax = plt.subplots(figsize=(8, 9))

    for feature in data["features"]:
        count = int(feature["properties"]["vulnerability_overlap_count"])
        for polygon in polygon_rings(feature["geometry"]):
            patch = Polygon(
                polygon[0],
                closed=True,
                facecolor=cmap(count),
                edgecolor="black",
                linewidth=0.6,
            )
            ax.add_patch(patch)

    ax.autoscale_view()
    ax.set_aspect("equal", adjustable="box")
    ax.set_axis_off()
    ax.set_title(
        "Sovrapposizione dei segnali territoriali di vulnerabilità\n"
        "(numero di dimensioni sopra il benchmark ponderato della Green Community)"
    )

    legend = [
        Patch(facecolor=cmap(level), edgecolor="black", label=f"{level} dimensioni")
        for level in range(4)
    ]
    ax.legend(handles=legend, loc="lower left", frameon=True)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=180, bbox_inches="tight")
    plt.close(fig)

    print(f"Created: {OUTPUT}")


if __name__ == "__main__":
    main()
