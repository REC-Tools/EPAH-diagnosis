"""Exploratory thematic comparisons. These are not EPAH-certified poverty rates.

The selected metrics, polarity, relative normalisation and equal weighting are
explicit analytical choices, not definitions imported from the EPAH documents.
No missing-data imputation, canonical promotion or automatic policy targeting.
"""
from __future__ import annotations

import math
import statistics

THEMES = {
    "demographic": ("Sensibilità demografica", ("population_65_plus", "H47")),
    "economic": ("Fragilità socioeconomica", ("income_vulnerability", "H46", "H50")),
    "housing": ("Proxy del patrimonio residenziale", ("old_building_stock", "H05")),
    "accessibility": ("Accessibilità stradale ai servizi", (
        "dea_accessibility", "upper_secondary_accessibility", "rail_accessibility")),
    "climate": ("Esposizione climatica caldo/freddo", ("H03", "H04")),
}
PERCENTAGES = {"population_65_plus", "H47", "income_vulnerability", "H46", "H50", "old_building_stock", "H05"}
STATUS = "experimental_scenario_do_not_publish"


def normalise(values: list[float], method: str = "percentile") -> list[float]:
    """Higher means more of the stated proxy/exposure, never measured poverty."""
    if not values or any(not math.isfinite(v) for v in values):
        raise ValueError("Normalisation requires finite observations")
    low, high = min(values), max(values)
    if low == high:
        return [50.0] * len(values)
    if method == "minmax":
        return [100 * (v - low) / (high - low) for v in values]
    if method != "percentile":
        raise ValueError("Unknown normalisation")
    ordered = sorted(values)
    # Average ranks for ties, scaled using the fixed cohort of municipalities.
    ranks = {value: statistics.mean(i for i, x in enumerate(ordered) if x == value)
             for value in set(ordered)}
    return [100 * ranks[v] / (len(values) - 1) for v in values]


def competition_ranks(scores: list[float]) -> list[int]:
    """Descending competition ranks: equal scores share rank (1, 1, 3)."""
    return [1 + sum(other > value and not math.isclose(other, value, rel_tol=0, abs_tol=1e-9)
                    for other in scores) for value in scores]


def _mean(vectors: list[list[float]]) -> list[float]:
    return [statistics.fmean(row) for row in zip(*vectors)]


def _spearman(a: list[float], b: list[float]) -> float | None:
    x, y = normalise(a), normalise(b)
    mx, my = statistics.fmean(x), statistics.fmean(y)
    numerator = math.fsum((u - mx) * (v - my) for u, v in zip(x, y))
    denominator = math.sqrt(math.fsum((u - mx) ** 2 for u in x) * math.fsum((v - my) ** 2 for v in y))
    return numerator / denominator if denominator else None


def analyse(municipalities: list[dict], selected_themes: list[str], *,
            global_scenario: bool = False) -> dict:
    if (not selected_themes or len(set(selected_themes)) != len(selected_themes)
            or any(key not in THEMES for key in selected_themes)):
        raise ValueError("Select distinct, known themes")
    if global_scenario and len(selected_themes) < 2:
        raise ValueError("A global scenario requires at least two explicitly selected themes")
    if (len(municipalities) != 27 or len({r["code"] for r in municipalities}) != 27
            or len({r["name"] for r in municipalities}) != 27
            or any(not r["name"].strip() or not isinstance(r["code"], str)
                   or len(r["code"]) != 6 or not r["code"].isascii() or not r["code"].isdigit()
                   for r in municipalities)):
        raise ValueError("Expected exactly 27 unique municipal names and six-digit codes")
    rows = sorted(municipalities, key=lambda r: r["code"])
    fields = sorted({field for theme in selected_themes for field in THEMES[theme][1]})
    raw, periods = {}, {}
    for field in fields:
        raw[field], periods[field] = [], set()
        for row in rows:
            observation = row.get("values", {}).get(field)
            if not isinstance(observation, dict) or observation.get("value") is None:
                raise ValueError(f"Missing or suppressed {field} for {row['code']}; no imputation")
            value = observation["value"]
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or value < 0 or field in PERCENTAGES and value > 100):
                raise ValueError(f"Invalid observation {field}/{row['code']}")
            period = observation.get("year")
            if not isinstance(period, str) or not period.strip():
                raise ValueError(f"Missing reference period {field}/{row['code']}")
            raw[field].append(float(value))
            periods[field].add(period)
        if len(periods[field]) != 1:
            raise ValueError(f"Mixed municipal periods within {field}; align the vintage first")
    # H03/H04 must describe the same climatic year, not different seasons/years.
    if "climate" in selected_themes and periods["H03"] != periods["H04"]:
        raise ValueError("HDD and CDD must use the same calendar year")
    groups, definitions = {}, {}
    for theme in selected_themes:
        groups[theme] = []
        for field in THEMES[theme][1]:
            # Exactly identical series in the same period receive one shared
            # weight. Similar correlations alone never trigger automatic removal.
            match = next((group for group in groups[theme]
                          if raw[group[0]] == raw[field] and periods[group[0]] == periods[field]), None)
            if match is None:
                groups[theme].append([field])
            else:
                match.append(field)
        definitions[theme] = {"label": THEMES[theme][0], "indicator_groups": groups[theme],
                              "group_weights": [1 / len(groups[theme])] * len(groups[theme]),
                              "higher_means": "more of the selected proxy or exposure; not a poverty probability"}
    scenarios = []
    thematic = {}
    for method in ("percentile", "minmax"):
        normalised = {field: normalise(raw[field], method) for field in fields}
        thematic[method] = {theme: _mean([normalised[g[0]] for g in groups[theme]]) for theme in selected_themes}
        if global_scenario:
            weights = {theme: 1.0 for theme in selected_themes}
            variants = [(f"{method}:equal_themes", weights)]
            for theme in selected_themes:
                for factor in (0.75, 1.25):
                    variants.append((f"{method}:{theme}:weight_x{factor}", {**weights, theme: factor}))
            for name, weight in variants:
                total = sum(weight.values())
                score = [math.fsum(thematic[method][t][i] * weight[t] for t in selected_themes) / total
                         for i in range(27)]
                scenarios.append({"id": name, "theme_weights": {t: w / total for t, w in weight.items()},
                                  "scores": score, "ranks": competition_ranks(score)})
    rankings = {method: {t: competition_ranks(scores) for t, scores in themes.items()}
                for method, themes in thematic.items()}
    output_rows = []
    for i, row in enumerate(rows):
        item = {"code": row["code"], "name": row["name"], "themes": {}}
        for theme in selected_themes:
            item["themes"][theme] = {
                "percentile_score": thematic["percentile"][theme][i],
                "percentile_rank": rankings["percentile"][theme][i],
                "minmax_score": thematic["minmax"][theme][i],
                "minmax_rank": rankings["minmax"][theme][i],
            }
        if global_scenario:
            item["global_selected_themes"] = {
                "baseline_score": scenarios[0]["scores"][i], "baseline_rank": scenarios[0]["ranks"][i],
                "best_scenario_rank": min(s["ranks"][i] for s in scenarios),
                "worst_scenario_rank": max(s["ranks"][i] for s in scenarios),
            }
        output_rows.append(item)
    return {
        "schema_version": "0.1-experimental", "status": STATUS,
        "contains_composite_scores": True, "scientific_approval": False, "publication_allowed": False,
        "not_a_household_energy_poverty_measure": True, "population_weighted": False,
        "themes": definitions, "global_scenario_enabled": global_scenario,
        "reference_periods": {key: sorted(period) for key, period in periods.items()},
        "mixed_reference_periods": len({p for period in periods.values() for p in period}) > 1,
        "constant_indicators": [key for key, values in raw.items() if min(values) == max(values)],
        "spearman": {a: {b: _spearman(raw[a], raw[b]) for b in fields} for a in fields},
        "municipalities": output_rows, "global_sensitivity_scenarios": scenarios,
        "limitations": [
            "Exploratory relative positions within these 27 municipalities, not official EPAH scores or prevalence.",
            "Weights and higher-value polarity are scenario assumptions, not causal estimates or approved definitions.",
            "Global results concern only explicitly selected themes; missing themes are not implicitly represented.",
            "Different source periods/universes may coexist; this is a cross-sectional snapshot, not a trend.",
            "Identical same-period series within a theme share one weight; high correlation alone does not establish redundancy.",
            "Constant indicators receive neutral 50; tied ranks are shared, not broken alphabetically.",
            "Rank ranges compare tested normalisation/weight scenarios; they are not confidence intervals.",
            "No imputation, individual attribution, expenditure estimate, scientific approval or allocation recommendation.",
        ],
    }
