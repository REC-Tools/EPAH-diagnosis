"""v0.4-only sparse geographic labels for thematic municipal maps.

Select at most five large *polygons*, not large indicator values or populations.
Labels are neutral cartographic anchors and never convey scientific priority.
The unchanged v0.3 chart builder remains the source of stable historical maps.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.patches import Patch, PathPatch
from matplotlib.transforms import Bbox
from pyproj import Transformer

from epah_diagnosis.cartography import (
    _oriented_polygon_path, _polygons, check_source_crs, RENDER_CRS,
)
from epah_diagnosis.municipality_locator_v0_4 import interior_label_point
from epah_diagnosis.release_artifacts import SNAI_COLORS

MAX_LABELS = 5


@dataclass(frozen=True)
class MapLabel:
    code: str
    name: str
    x: float
    y: float
    polygon_area_m2: float


def _ring_area_m2(ring: list, transform: Transformer) -> float:
    points = [transform.transform(float(x), float(y)) for x, y in ring]
    return abs(sum(
        ax * by - bx * ay
        for (ax, ay), (bx, by) in zip(points, points[1:])
    )) / 2.0


def polygon_area_m2(geometry: dict, transform: Transformer) -> float:
    """Total projected geometric polygon area, with holes subtracted."""
    total = 0.0
    for rings in _polygons(geometry):
        area = _ring_area_m2(rings[0], transform)
        area -= sum(_ring_area_m2(hole, transform) for hole in rings[1:])
        if not math.isfinite(area) or area <= 0:
            raise ValueError("Invalid projected municipality polygon area")
        total += area
    if not math.isfinite(total) or total <= 0:
        raise ValueError("Invalid municipality area")
    return total


def select_map_labels(geography: dict, *, max_labels: int = MAX_LABELS) -> list[MapLabel]:
    """Stable selection by drawn municipal surface only, tie-break ISTAT code."""
    check_source_crs(geography)
    if not 0 <= max_labels <= MAX_LABELS:
        raise ValueError("Map labels are limited to at most five municipalities")
    transform = Transformer.from_crs("EPSG:4326", RENDER_CRS, always_xy=True)
    indexed = []
    seen = set()
    for feature in geography["features"]:
        props = feature["properties"]
        code, name = props["municipality_code"], props["municipality"]
        if (not isinstance(code, str) or len(code) != 6 or not code.isascii()
                or not code.isdigit() or code in seen
                or not isinstance(name, str) or not name.strip()):
            raise ValueError("Invalid map label municipality name/code")
        seen.add(code)
        area = polygon_area_m2(feature["geometry"], transform)
        x, y = interior_label_point(feature["geometry"], transform)
        indexed.append(MapLabel(code, name, x, y, area))
    if len(indexed) != 27:
        raise ValueError("The v0.4 map label selection requires exactly 27 municipalities")
    indexed.sort(key=lambda r: (-r.polygon_area_m2, r.code))
    return indexed[:max_labels]


def _draw_sparse_labels(fig, ax, labels: list[MapLabel]) -> list[str]:
    """Skip colliding/off-plot labels instead of hiding geometry or shrinking text."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    allowed = ax.get_window_extent(renderer)
    shown = []
    placed: list[Bbox] = []
    for item in labels:
        artist = ax.text(
            item.x, item.y, item.name, ha="center", va="center",
            fontsize=7.5, color="#17354A", fontweight="semibold", zorder=8,
            bbox={"boxstyle": "round,pad=0.22", "facecolor": "white",
                  "edgecolor": "none", "alpha": 0.9},
        )
        fig.canvas.draw()
        bounds = artist.get_window_extent(fig.canvas.get_renderer()).padded(4)
        if (bounds.x0 < allowed.x0 or bounds.x1 > allowed.x1
                or bounds.y0 < allowed.y0 or bounds.y1 > allowed.y1
                or any(bounds.overlaps(previous) for previous in placed)):
            artist.remove()
            continue
        shown.append(item.code)
        placed.append(bounds)
    return shown


def render_thematic_map(geography: dict, metric, values: dict,
                        output: Path, fmt: str, labels: list[MapLabel]) -> list[str]:
    """Draw the same v0.3 absolute numeric/categorical scale with sparse labels."""
    if fmt not in {"png", "svg"}:
        raise ValueError("Map output must be PNG or SVG")
    if not values:
        raise ValueError("No mapped observations")
    categorical = metric.category == "categorical"
    present = [entry["value"] for entry in values.values()]
    transform = Transformer.from_crs("EPSG:4326", RENDER_CRS, always_xy=True)
    fig, ax = plt.subplots(figsize=(9.4, 7.3), facecolor="#FFFFFF")
    try:
        if not categorical:
            lo, hi = min(present), max(present)
            if lo == hi:
                lo -= .5
                hi += .5
            scale = Normalize(vmin=lo, vmax=hi)
            palette = plt.get_cmap("cividis")
        for feature in geography["features"]:
            code = feature["properties"]["municipality_code"]
            observation = values.get(code)
            if observation:
                color = (SNAI_COLORS[observation["value"]] if categorical
                         else palette(scale(observation["value"])))
            else:
                color = "#E5E7EB"
            for rings in _polygons(feature["geometry"]):
                ax.add_patch(PathPatch(
                    _oriented_polygon_path(rings, transform),
                    facecolor=color, edgecolor="#FFFFFF", linewidth=.45,
                ))
        ax.autoscale_view()
        ax.set_aspect("equal", adjustable="box")
        ax.set_axis_off()
        ax.set_title(metric.name, loc="left", fontsize=17,
                     fontweight="semibold", color="#0F2940", pad=17)
        if categorical:
            legend = [Patch(facecolor=SNAI_COLORS[key], label="SNAI " + key)
                      for key in sorted(set(present))]
            ax.legend(handles=legend, loc="upper left", bbox_to_anchor=(0, -.01),
                      ncol=min(6, len(legend)), frameon=False, fontsize=9)
        else:
            fig.colorbar(
                plt.cm.ScalarMappable(norm=scale, cmap=palette),
                ax=ax, fraction=.033, pad=.024, shrink=.74, label=metric.unit,
            )
        shown = _draw_sparse_labels(fig, ax, labels)
        fig.text(
            .07, .075,
            f"{metric.source}  |  Copertura: {len(values)}/27  |  valori assoluti",
            fontsize=9, color="#405267",
        )
        fig.text(
            .07, .045,
            "Nomi: fino a 5 Comuni con poligoni più estesi; tutti i 27 nella tabella. "
            "NON indica priorità. BOZZA TECNICA.",
            fontsize=7.5, color="#64748B",
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output, format=fmt, dpi=170, facecolor="white",
                    bbox_inches="tight", pad_inches=.24)
        return shown
    finally:
        plt.close(fig)
