from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Polygon


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "derived" / "municipality_profile.geojson"
OUTPUT_DIR = ROOT / "outputs" / "maps"

MAPS = (
    (
        "population_65_plus_pct",
        "Popolazione di 65 anni e oltre (%)",
        "%",
        "map_population_65_plus.png",
    ),
    (
        "income_vulnerability_pct",
        "Contribuenti con reddito <= 15.000 EUR (%)",
        "%",
        "map_income_vulnerability.png",
    ),
    (
        "old_building_stock_pct",
        "Edifici residenziali costruiti prima del 1981 (%)",
        "%",
        "map_old_building_stock.png",
    ),
    (
        "heating_degree_days",
        "Gradi-giorno di riscaldamento",
        "GG",
        "map_heating_degree_days.png",
    ),
    (
        "mean_altitude_m",
        "Altitudine media comunale",
        "m s.l.m.",
        "map_mean_altitude.png",
    ),
    (
        "dea_access_minutes",
        "Tempo stradale al DEA I/II piu vicino",
        "minuti",
        "map_dea_access_minutes.png",
    ),
    (
        "upper_secondary_access_minutes",
        "Tempo stradale al polo scolastico superiore piu vicino",
        "minuti",
        "map_upper_secondary_access_minutes.png",
    ),
    (
        "rail_access_minutes",
        "Tempo stradale al gateway ferroviario attivo piu vicino",
        "minuti",
        "map_rail_access_minutes.png",
    ),
)


def polygon_rings(geometry: dict):
    if geometry["type"] == "Polygon":
        yield geometry["coordinates"]
    elif geometry["type"] == "MultiPolygon":
        yield from geometry["coordinates"]
    else:
        raise ValueError(f"Unsupported geometry type: {geometry['type']}")


def draw_map(
    data: dict,
    indicator: str,
    title: str,
    unit: str,
    output: Path,
) -> None:
    values = [
        float(feature["properties"][indicator])
        for feature in data["features"]
    ]
    vmin, vmax = min(values), max(values)

    fig, ax = plt.subplots(figsize=(8, 9))

    for feature in data["features"]:
        value = float(feature["properties"][indicator])
        normalized = 0.5 if vmax == vmin else (value - vmin) / (vmax - vmin)

        for polygon in polygon_rings(feature["geometry"]):
            exterior = polygon[0]
            patch = Polygon(
                exterior,
                closed=True,
                facecolor=plt.cm.viridis(normalized),
                edgecolor="black",
                linewidth=0.5,
            )
            ax.add_patch(patch)

    ax.autoscale_view()
    ax.set_aspect("equal", adjustable="box")
    ax.set_axis_off()
    ax.set_title(title)

    sm = plt.cm.ScalarMappable(
        cmap="viridis",
        norm=plt.Normalize(vmin=vmin, vmax=vmax),
    )
    sm.set_array([])
    fig.colorbar(sm, ax=ax, fraction=0.035, pad=0.02, label=unit)

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    if not INPUT.exists():
        raise FileNotFoundError(
            f"Missing {INPUT}. Run build_municipality_geojson.py first."
        )

    data = json.loads(INPUT.read_text(encoding="utf-8"))

    for indicator, title, unit, filename in MAPS:
        output = OUTPUT_DIR / filename
        draw_map(data, indicator, title, unit, output)
        print(f"Created: {output}")


if __name__ == "__main__":
    main()
