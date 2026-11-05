"""Non-causal, unweighted municipal comparisons for the 27-town v0.2 pilot.

No risk score, clustering, household attribution, cross-year causal claims,
or automatic decisions about the meaning of relative municipal differences.
"""
from __future__ import annotations

import itertools
import math
import statistics

from epah_diagnosis.report_v0_2 import FIELDS

DIMENSIONS = tuple(x[0] for x in FIELDS)


def compare(profiles: list[dict], registry: dict[str, str]) -> tuple[list[dict], dict]:
    if (len(profiles) != 27 or len(registry) != 27
            or len({p["municipality"] for p in profiles}) != 27
            or {p["municipality"] for p in profiles} != set(registry)
            or len(set(registry.values())) != 27):
        raise ValueError("Expected 27 unique, matched municipal profiles and codes")
    median = {}
    for field in DIMENSIONS:
        vals = [float(p[field]) for p in profiles]
        if any(not math.isfinite(x) for x in vals):
            raise ValueError(f"{field} contains non-finite observations")
        median[field] = statistics.median(vals)  # NOT rounded for classification
    result = []
    flags = {}
    for item in sorted(profiles, key=lambda p: registry[p["municipality"]]):
        name = item["municipality"]
        code = registry[name]
        if len(code) != 6 or not code.isdigit():
            raise ValueError("Invalid ISTAT code")
        row = {"municipality": name, "istat_code": code, "snai_class": item["snai_class"],
               "snai_year": item["snai_year"]}
        flags[code] = {}
        for field, _, unit, year_key in FIELDS:
            v = float(item[field])
            above = v > median[field]
            flags[code][field] = above
            row[field] = f"{v:.4f}"
            row[field + "_year"] = item[year_key]
            row[field + "_median_27"] = f"{median[field]:.4f}"
            row[field + "_delta_from_median"] = f"{v - median[field]:.4f}"
            row[field + "_above_median"] = "true" if above else "false"
        result.append(row)
    pairs = []
    for a, b in itertools.combinations(DIMENSIONS, 2):
        both = sum(flags[code][a] and flags[code][b] for code in flags)
        pairs.append({
            "indicator_a": a, "indicator_b": b,
            "municipalities_above_both": both,
            "municipalities_total": 27,
            "share_municipalities_pct": round(both * 100 / 27, 2),
        })
    summary = {
        "schema_version": "1.0",
        "status": "technical_draft_do_not_publish",
        "scope": "27 registered municipalities; not population-weighted",
        "municipalities": 27,
        "independent_numeric_dimensions": len(DIMENSIONS),
        "no_composite_score": True,
        "not_a_household_energy_poverty_measure": True,
        "threshold_rule": "strictly_above_unweighted_median_of_27_municipalities",
        "medians_unrounded_for_comparison": {key: median[key] for key in DIMENSIONS},
        "count_above_median": {
            key: sum(flags[c][key] for c in flags) for key in DIMENSIONS
        },
        "pairwise_cooccurrences": pairs,
        "snai_is_categorical": True,
        "limitations": [
            "Overlap counts are exploratory, not a composite ranking or causal result.",
            "Inputs come from differing periods, populations and denominators.",
            "Above-median does not necessarily mean higher energy-poverty risk.",
            "No household observations, CIT quarantine results or estimated energy bills.",
        ],
    }
    return result, summary
