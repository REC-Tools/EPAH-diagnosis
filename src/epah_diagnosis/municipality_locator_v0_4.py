"""Technical-only A4 locator map for the 27 municipality boundaries.

Neutral cartography only: names and ISTAT codes, no data values, poverty scores,
source approvals or changes to the historical v0.3 atlas.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path as MplPath
from matplotlib.patches import PathPatch
from pyproj import Transformer

from epah_diagnosis.cartography import (
    _oriented_polygon_path, _polygons, check_source_crs, RENDER_CRS,
)
from epah_diagnosis.release_artifacts import check_geojson
from epah_diagnosis.cli import read_municipality_codes

STATUS = "technical_draft_do_not_publish"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _project(rings: list, transformer: Transformer) -> list[list[tuple[float, float]]]:
    return [[transformer.transform(float(x), float(y)) for x, y in ring]
            for ring in rings]


def _contains(point: tuple[float, float], rings: list[list[tuple[float, float]]]) -> bool:
    if not MplPath(rings[0]).contains_point(point):
        return False
    return not any(MplPath(hole).contains_point(point) for hole in rings[1:])


def interior_label_point(geometry: dict, transformer: Transformer) -> tuple[float, float]:
    """Find an interior label point; never use a potentially exterior centroid.

    Evaluate the largest multipart shell first. Both polygon holes and small
    islands are respected. Raise if the valid inside position cannot be found.
    """
    candidates = []
    for rings in _polygons(geometry):
        projected = _project(rings, transformer)
        shell = projected[0]
        area = abs(sum(shell[i][0] * shell[i + 1][1] -
                       shell[i + 1][0] * shell[i][1] for i in range(len(shell) - 1)))
        candidates.append((area, projected))
    for _, rings in sorted(candidates, key=lambda v: v[0], reverse=True):
        xs, ys = zip(*rings[0])
        xlo, xhi, ylo, yhi = min(xs), max(xs), min(ys), max(ys)
        fractions = (0.5, 0.35, 0.65, 0.2, 0.8, 0.1, 0.9)
        for fy in fractions:
            for fx in fractions:
                point = (xlo + (xhi - xlo) * fx, ylo + (yhi - ylo) * fy)
                if _contains(point, rings):
                    return point
        for ystep in range(1, 80):
            fy = ystep / 80
            for xstep in range(1, 80):
                fx = xstep / 80
                point = (xlo + (xhi - xlo) * fx, ylo + (yhi - ylo) * fy)
                if _contains(point, rings):
                    return point
        # Very narrow geometry: probe slightly inside shell edges as fallback.
        shell = rings[0]
        orient = sum(shell[i][0] * shell[i + 1][1] -
                     shell[i + 1][0] * shell[i][1] for i in range(len(shell) - 1))
        for a, b in zip(shell, shell[1:]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            length = math.hypot(dx, dy)
            if length == 0:
                continue
            sign = 1 if orient > 0 else -1
            for factor in (0.001, 0.00001):
                offset = factor * length
                point = ((a[0] + b[0]) / 2 - sign * dy / length * offset,
                         (a[1] + b[1]) / 2 + sign * dx / length * offset)
                if _contains(point, rings):
                    return point
    raise ValueError("Could not find an interior label point for municipality geometry")


def validate(geometry: dict, registry: Path) -> tuple[list[dict], dict[str, str]]:
    check_source_crs(geometry)
    by_name = read_municipality_codes(registry)
    if (len(by_name) != 27 or len(set(by_name.values())) != 27
            or any(len(code) != 6 or not code.isascii() or not code.isdigit()
                   for code in by_name.values())):
        raise ValueError("Locator requires exactly 27 unique municipality codes")
    check_geojson(geometry, by_name)
    return sorted(geometry["features"], key=lambda feature:
                  (feature["properties"]["municipality"].casefold(),
                   feature["properties"]["municipality_code"])), by_name


def render(features: list[dict], out: Path) -> list[dict]:
    transformer = Transformer.from_crs("EPSG:4326", RENDER_CRS, always_xy=True)
    fig = plt.figure(figsize=(11.69, 8.27), facecolor="white")
    map_axis = fig.add_axes([0.035, 0.12, 0.63, 0.73])
    index_axis = fig.add_axes([0.68, 0.12, 0.30, 0.73])
    index_axis.axis("off")
    index_axis.set_xlim(0, 1)
    index_axis.set_ylim(0, 1)
    labels = []
    xmin, xmax, ymin, ymax = float("inf"), float("-inf"), float("inf"), float("-inf")
    try:
        for pos, feature in enumerate(features, 1):
            code = feature["properties"]["municipality_code"]
            name = feature["properties"]["municipality"]
            for rings in _polygons(feature["geometry"]):
                projected = _project(rings, transformer)
                for x, y in projected[0]:
                    xmin, xmax = min(xmin, x), max(xmax, x)
                    ymin, ymax = min(ymin, y), max(ymax, y)
                map_axis.add_patch(PathPatch(_oriented_polygon_path(rings, transformer),
                                             facecolor="#e5edf0", edgecolor="#415b68",
                                             linewidth=0.65))
            x, y = interior_label_point(feature["geometry"], transformer)
            map_axis.text(x, y, str(pos), ha="center", va="center", fontsize=7,
                          fontweight="semibold", color="#102a41", zorder=3,
                          bbox={"boxstyle": "circle,pad=0.21", "facecolor": "#ffffff",
                                "edgecolor": "#6b8593", "linewidth": 0.5})
            labels.append({"index": pos, "municipality": name, "municipality_code": code})
        map_axis.set_aspect("equal", adjustable="box")
        width, height = xmax - xmin, ymax - ymin
        if width <= 0 or height <= 0:
            raise ValueError("Invalid map geometry extent")
        pad = max(width, height) * 0.035
        map_axis.set_xlim(xmin - pad, xmax + pad)
        map_axis.set_ylim(ymin - pad, ymax + pad)
        map_axis.axis("off")
        bar_km = 5 if width < 60000 else 10
        bx = xmin + 0.055 * width
        by = ymin + 0.04 * height
        map_axis.plot([bx, bx + bar_km * 1000], [by, by], color="#233d4d",
                      lw=3, solid_capstyle="butt", zorder=4)
        map_axis.text(bx, by + 0.012 * height, f"{bar_km} km", fontsize=8, color="#233d4d")
        map_axis.annotate("N", xy=(0.96, 0.96), xytext=(0.96, 0.86),
                          xycoords="axes fraction", textcoords="axes fraction",
                          arrowprops={"arrowstyle": "-|>", "color": "#233d4d", "lw": 1.8},
                          ha="center", fontsize=9)
        index_axis.text(0, 1.015, "Indice dei Comuni", fontsize=13,
                        weight="bold", color="#102a41", va="bottom")
        for item in labels:
            line = f"{item['index']:02d}  {item['municipality']}  ({item['municipality_code']})"
            index_axis.text(0, 0.985 - (item["index"] - 1) * 0.0352, line,
                            fontsize=7.6, va="top", color="#243e50")
        fig.text(0.047, 0.92, "I 27 Comuni della Green Community", fontsize=20,
                 weight="semibold", color="#102a41")
        fig.text(0.047, 0.877, "Tavola di orientamento · confini comunali · codici ISTAT",
                 fontsize=10, color="#4f6979")
        fig.text(0.047, 0.047,
                 "EPAH Diagnosis · Carta di riferimento, non misura di povertà energetica · BOZZA TECNICA — NON PUBBLICARE",
                 fontsize=8.4, color="#526c7c")
        out.mkdir()
        for ext in ("png", "svg", "pdf"):
            fig.savefig(out / f"municipality_locator.{ext}", format=ext,
                        dpi=180, facecolor="white")
    finally:
        plt.close(fig)
    return labels


def build(geojson: Path, registry: Path, out_dir: Path) -> Path:
    if out_dir.exists():
        raise FileExistsError("Choose a NEW destination for the reference map")
    dest = out_dir.resolve()
    if (dest.is_relative_to(geojson.resolve().parent)
            or dest.is_relative_to(registry.resolve().parent)):
        raise ValueError("Map destination must be outside input directories")
    geometry = json.loads(geojson.read_text(encoding="utf-8"))
    features, _ = validate(geometry, registry)
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".epah-v04-locator-", dir=out_dir.parent) as temp:
        stage = Path(temp) / "locator"
        labels = render(features, stage)
        report = {
            "schema_version": "0.4-technical-locator",
            "status": STATUS, "publication_allowed": False,
            "scientific_approval": False, "municipalities": 27,
            "projection": RENDER_CRS, "source_crs": "WGS84/CRS84",
            "geography_file_sha256": sha(geojson), "registry_sha256": sha(registry),
            "legend": labels, "content": "Neutral geographical reference, not indicator values",
        }
        (stage / "metadata.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        hashes = {p.name: sha(p) for p in stage.iterdir() if p.is_file()}
        (stage / "manifest.json").write_text(json.dumps({
            "status": STATUS, "publication_allowed": False,
            "inputs_sha256": {"geometry": sha(geojson), "registry": sha(registry)},
            "outputs_sha256": hashes,
        }, indent=2) + "\n", encoding="utf-8")
        if out_dir.exists():
            raise FileExistsError("Concurrent output detected; no overwrite allowed")
        os.replace(stage, out_dir)
    return out_dir
