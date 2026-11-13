"""v0.4-only distribution charts with readable, consistently identified communes.

Numeric dot plots show all 27 names in ISTAT-code order (never vulnerability
order). The median is an unweighted contextual reference, not a risk cut-off.
Categorical SNAI charts show category counts, without ordinal scoring.
"""
from __future__ import annotations

from collections import Counter
import math
from pathlib import Path
import statistics
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from epah_diagnosis.release_artifacts import SNAI_COLORS

SNAI_CLASSES = tuple("ABCDEF")
STATUS = "technical_draft_do_not_publish"


def _ordered_observations(metric, values: dict, registry: dict) -> list[tuple[str, str, object]]:
    """Validate 27 unique municipality values without changing any observation."""
    if (len(registry) != 27 or len(values) != 27 or set(values) != set(registry)
            or len(set(registry.values())) != 27):
        raise ValueError("The distribution requires all 27 registered municipalities")
    if metric.category not in {"numeric", "categorical"}:
        raise ValueError("Unknown indicator category")
    result = []
    for code in sorted(registry):
        if (not isinstance(code, str) or len(code) != 6 or not code.isascii()
                or not code.isdigit() or not isinstance(registry[code], str)
                or not registry[code].strip()):
            raise ValueError("Invalid ISTAT code or municipality label")
        record = values[code]
        if not isinstance(record, dict) or "value" not in record or not record.get("year"):
            raise ValueError(f"Missing value or period for {code}")
        value = record["value"]
        if metric.category == "numeric":
            # Explicitly forbid booleans and nonfinite values as source observations.
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"Nonfinite or nonnumeric series: {code}")
        elif not isinstance(value, str) or value not in SNAI_CLASSES:
            raise ValueError(f"Invalid SNAI category: {code}")
        result.append((code, registry[code], value))
    return result


def render_distribution(metric, values: dict, registry: dict,
                        output: Path, fmt: str) -> dict:
    """Save PNG/SVG and return an audit-friendly policy for the exact same data."""
    if fmt not in {"png", "svg"}:
        raise ValueError("Distribution output format must be PNG or SVG")
    observations = _ordered_observations(metric, values, registry)
    categorical = metric.category == "categorical"
    fig_height = 5.8 if categorical else 12.0
    fig, ax = plt.subplots(figsize=(11.5, fig_height), facecolor="white")
    try:
        if categorical:
            counts = Counter(value for _, _, value in observations)
            count_series = [counts.get(k, 0) for k in SNAI_CLASSES]
            bars = ax.bar(
                SNAI_CLASSES, count_series,
                color=[SNAI_COLORS[k] for k in SNAI_CLASSES],
                width=.65,
            )
            ax.bar_label(bars, labels=[str(v) for v in count_series],
                         padding=4, fontsize=10, color="#16374A")
            ax.set_ylim(0, max(count_series) + max(2, int(max(count_series) * .2)))
            ax.yaxis.set_major_locator(MaxNLocator(integer=True))
            ax.set_ylabel("Numero di Comuni (totale 27)")
            ax.set_xlabel("Classe territoriale SNAI (categoria, non punteggio)")
            ax.grid(axis="y", alpha=.18)
            order = "SNAI_classes_A_to_F"
            median = None
            category_counts = {key: counts.get(key, 0) for key in SNAI_CLASSES}
            fig.subplots_adjust(left=.12, right=.94, top=.82, bottom=.21)
            description = (
                "Conteggio dei 27 Comuni per classe SNAI. "
                "Lo zero indica una classe senza Comuni, non un dato comunale mancante."
            )
        else:
            # Unchanging ISTAT order makes different indicators easier to navigate;
            # sorting dots by numeric value could imply a priority ranking.
            data = [float(value) for _, _, value in observations]
            median = statistics.median(data)
            n = len(observations)
            for i in range(0, n, 2):
                ax.axhspan(i - .5, i + .5, color="#F1F5F7", zorder=0)
            ax.scatter(data, list(range(n)), s=51, color="#156B82", zorder=3)
            ax.set_yticks(range(n), [name for _, name, _ in observations],
                          fontsize=9.3)
            ax.set_ylim(n - .35, -.65)
            ax.axvline(median, color="#A65B24", linestyle="--",
                       linewidth=1.5, label=f"Mediana descrittiva: {median:.2f} {metric.unit}")
            ax.legend(loc="lower right", bbox_to_anchor=(1, 1.012),
                      frameon=False, fontsize=9)
            ax.set_xlabel(metric.unit)
            ax.set_ylabel("Comuni (ordine codice ISTAT)")
            ax.grid(axis="x", alpha=.2)
            ax.set_axisbelow(True)
            order = "ascending_ISTAT_code_not_value"
            category_counts = None
            # Reserve a wider margin for full municipal names, never ellipsize.
            fig.subplots_adjust(left=.37, right=.93, top=.88, bottom=.11)
            description = (
                "27 Comuni in ordine ISTAT; mediana non ponderata, non una soglia "
                "di rischio. Le scale si riferiscono al singolo indicatore."
            )
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        if not categorical:
            ax.spines["left"].set_visible(False)
            ax.tick_params(axis="y", length=0, pad=10)
        # Reserve the full figure width for the heading. An axes title starts
        # after the long municipal labels and can collide with the median legend.
        fig.suptitle(
            textwrap.fill("Confronto descrittivo · " + metric.name, width=72,
                          break_long_words=False, break_on_hyphens=False),
            x=.08, y=.965, ha="left", va="top", color="#0F2940", fontsize=15.5,
        )
        fig.text(.08 if categorical else .10, .035, description,
                 fontsize=8.3, color="#455A6B")
        fig.text(.08 if categorical else .10, .016,
                 f"{metric.source}  |  BOZZA TECNICA · NON PUBBLICARE",
                 fontsize=8, color="#64748B")
        output.parent.mkdir(parents=True, exist_ok=True)
        # Keep SVG text machine-readable for accessibility and inspection.
        with plt.rc_context({"svg.fonttype": "none"}):
            fig.savefig(output, format=fmt, dpi=170, facecolor="white")
    finally:
        plt.close(fig)
    return {
        "category": metric.category,
        "municipalities": 27,
        "municipality_order": [code for code, _, _ in observations],
        "display_order_rule": order,
        "names_displayed": 27 if not categorical else 0,
        "median_unweighted_descriptive": median,
        "snai_class_counts": category_counts,
        "same_values_as_atlas": True,
        "scientific_approval": False,
        "publication_allowed": False,
        "status": STATUS,
    }
