"""Shared metric-correct municipality maps; geographic GeoJSON stays unchanged."""
from __future__ import annotations

import math
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.path import Path as MplPath
from matplotlib.patches import Patch, PathPatch
from pyproj import Transformer

INPUT_CRS = "EPSG:4326"
RENDER_CRS = "EPSG:32632"
WGS84_NAMES = {"EPSG:4326", "OGC:CRS84", "CRS84", "URN:OGC:DEF:CRS:OGC:1.3:CRS84"}

def check_source_crs(data: dict) -> None:
    if data.get("type") != "FeatureCollection" or not data.get("features"):
        raise ValueError("Expected a nonempty GeoJSON FeatureCollection")
    crs = data.get("crs")
    if crs is not None:
        name = crs.get("properties", {}).get("name") if isinstance(crs, dict) else None
        if not isinstance(name, str) or name.upper() not in WGS84_NAMES:
            raise ValueError("Map input must be geographic WGS84/CRS84")

def _ring_area(ring: list) -> float:
    return 0.5 * sum(
        float(ring[i][0]) * float(ring[i + 1][1])
        - float(ring[i + 1][0]) * float(ring[i][1])
        for i in range(len(ring) - 1)
    )


def _polygons(geometry: dict):
    kind = geometry.get("type")
    coords = geometry.get("coordinates")
    if kind == "Polygon":
        polygons = [coords]
    elif kind == "MultiPolygon":
        polygons = coords
    else:
        raise ValueError(f"Expected Polygon or MultiPolygon; got {kind!r}")
    if not isinstance(polygons, list) or not polygons:
        raise ValueError("Geometry missing polygons")
    for rings in polygons:
        if not isinstance(rings, list) or not rings:
            raise ValueError("Geometry missing exterior ring")
        for ring in rings:
            if not isinstance(ring, list) or len(ring) < 4 or ring[0] != ring[-1]:
                raise ValueError("Polygon ring must be closed with at least four coordinates")
            for point in ring:
                if (not isinstance(point, list) or len(point) != 2
                    or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in point)
                    or not -180 <= point[0] <= 180 or not -90 <= point[1] <= 90):
                    raise ValueError("Invalid or non-geographic WGS84 coordinate")
            if abs(_ring_area(ring)) < 1e-14:
                raise ValueError("Zero-area polygon ring")
        yield rings



def _oriented_polygon_path(rings: list, transformer: Transformer | None = None) -> MplPath:
    """Compound SVG-style path: counterclockwise shell, clockwise holes.

    Matplotlib uses the nonzero fill rule for PathPatch. Opposite orientations
    prevent a lake/municipal hole from being filled with the thematic color.
    """
    vertices = []
    codes = []
    for i, ring in enumerate(rings):
        points = [list(transformer.transform(float(x), float(y))) for x, y in ring] if transformer else [list(p) for p in ring]
        if (_ring_area(points) > 0) != (i == 0):
            points.reverse()
        for j, point in enumerate(points):
            vertices.append(tuple(point))
            codes.append(
                MplPath.MOVETO if j == 0 else
                MplPath.CLOSEPOLY if j == len(points) - 1 else MplPath.LINETO
            )
    return MplPath(vertices, codes)




def render_thematic_map(
    geojson: dict, field: str, title: str, unit: str, output: Path,
    *, category_colors: dict | None = None, category_labels: dict | None = None,
    footer: str = "EPAH Diagnosis | Sinergie in Canavese | Dati aggregati",
) -> None:
    """Project WGS84 lon/lat to UTM 32N in memory before drawing at metric 1:1."""
    check_source_crs(geojson)
    transformer = Transformer.from_crs(INPUT_CRS, RENDER_CRS, always_xy=True)
    categorical = category_colors is not None
    if not categorical:
        vals = [float(feature["properties"][field]) for feature in geojson["features"]]
        if not all(math.isfinite(v) for v in vals):
            raise ValueError(f"Non-finite map value for {field}")
        vmin, vmax = min(vals), max(vals)
        norm = Normalize(vmin=vmin - 1e-9 if vmin == vmax else vmin,
                         vmax=vmax + 1e-9 if vmin == vmax else vmax)
        cmap = plt.get_cmap("viridis")
    fig, ax = plt.subplots(figsize=(8, 8))
    try:
        for feature in geojson["features"]:
            props = feature["properties"]
            if categorical:
                key = str(props[field])
                if key not in category_colors:
                    raise ValueError(f"Unrecognized category for {field}: {key}")
                color = category_colors[key]
            else:
                color = cmap(norm(float(props[field])))
            for rings in _polygons(feature["geometry"]):
                ax.add_patch(PathPatch(
                    _oriented_polygon_path(rings, transformer),
                    facecolor=color, edgecolor="#262626", linewidth=0.34,
                ))
        ax.autoscale_view()
        ax.set_aspect("equal", adjustable="box")  # projected metres, never degrees
        ax.set_axis_off()
        ax.set_title(title, fontsize=13, pad=16)
        if categorical:
            labels = category_labels or {key: f"Classe {key}" for key in category_colors}
            legend = [Patch(facecolor=color, label=labels.get(key, key))
                      for key, color in category_colors.items()]
            ax.legend(handles=legend, loc="lower center",
                      bbox_to_anchor=(0.5, -0.08), ncol=min(3, len(legend)),
                      frameon=False, fontsize=9)
        else:
            fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap),
                         ax=ax, fraction=0.035, pad=0.02, label=unit)
        fig.text(0.5, 0.015, footer, ha="center", fontsize=8, color="#666666")
        output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output, dpi=140, bbox_inches="tight", facecolor="white")
    finally:
        plt.close(fig)
