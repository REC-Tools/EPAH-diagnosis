"""Step 6: synthetic charts retain 27 names without value-sorted risk rankings."""
from __future__ import annotations

from copy import deepcopy
from xml.etree import ElementTree as ET

import matplotlib
matplotlib.use("Agg")
import pytest

from epah_diagnosis.distribution_charts_v0_4 import (
    _ordered_observations, render_distribution,
)
from test_v0_3_visual_atlas import mod as v3


def registry():
    return {f"001{i:03d}": f"Synthetic Comune {i:02d} with long geographic name"
            for i in range(1, 28)}


def numeric_values(reg):
    return {code: {"value": 27.0 - i, "year": "2024"}
            for i, code in enumerate(reg)}


def snai_values(reg):
    return {code: {"value": "ABCDEF"[i % 6], "year": "2020"}
            for i, code in enumerate(reg)}


def test_numeric_27_codes_order_by_istat_not_values_and_svg_readable(tmp_path):
    reg = registry()
    data = numeric_values(reg)
    frozen = deepcopy(data)
    results = []
    for fmt in ("png", "svg"):
        out = tmp_path / f"test.{fmt}"
        result = render_distribution(v3.BASE[0], data, reg, out, fmt)
        assert out.stat().st_size > 250
        assert result["municipality_order"] == sorted(reg)
        assert result["display_order_rule"] == "ascending_ISTAT_code_not_value"
        assert result["names_displayed"] == 27
        assert result["median_unweighted_descriptive"] == 14.0
        assert result["scientific_approval"] is False
        assert result["publication_allowed"] is False
        if fmt == "png":
            assert out.read_bytes().startswith(b"\x89PNG")
        else:
            text = out.read_text(encoding="utf-8")
            assert "<svg" in text and "<text" in text
            assert "Synthetic Comune 01 with long geographic name" in text
            assert "Synthetic Comune 27 with long geographic name" in text
            assert "non una soglia" in text
            ET.parse(out)
        results.append(result)
    assert results[0] == results[1]
    assert data == frozen  # No data or reference period rewrites


def test_categorical_snai_counts_not_numeric_rank(tmp_path):
    reg = registry()
    data = snai_values(reg)
    result = render_distribution(v3.BASE[-1], data, reg, tmp_path / "snai.svg", "svg")
    assert result["category"] == "categorical"
    assert result["display_order_rule"] == "SNAI_classes_A_to_F"
    assert result["median_unweighted_descriptive"] is None
    assert result["snai_class_counts"] == {"A": 5, "B": 5, "C": 5,
                                            "D": 4, "E": 4, "F": 4}
    assert sum(result["snai_class_counts"].values()) == 27
    svg = (tmp_path / "snai.svg").read_text(encoding="utf-8")
    assert "Classe territoriale SNAI" in svg
    ET.parse(tmp_path / "snai.svg")


def test_distribution_rejects_incomplete_or_invalid_observations(tmp_path):
    reg = registry()
    data = numeric_values(reg)
    with pytest.raises(ValueError, match="all 27"):
        render_distribution(v3.BASE[0], dict(list(data.items())[:-1]), reg,
                            tmp_path / "blocked.svg", "svg")
    data["001001"] = {"value": float("nan"), "year": "2024"}
    with pytest.raises(ValueError, match="Nonfinite"):
        _ordered_observations(v3.BASE[0], data, reg)
    data["001001"] = {"value": True, "year": "2024"}
    with pytest.raises(ValueError, match="Nonfinite"):
        _ordered_observations(v3.BASE[0], data, reg)
    data["001001"] = {"value": 1, "year": ""}
    with pytest.raises(ValueError, match="Missing value or period"):
        _ordered_observations(v3.BASE[0], data, reg)
    bad_snai = snai_values(reg)
    bad_snai["001001"] = {"value": "G", "year": "2020"}
    with pytest.raises(ValueError, match="Invalid SNAI"):
        _ordered_observations(v3.BASE[-1], bad_snai, reg)
    assert not (tmp_path / "blocked.svg").exists()


def test_all_equal_numbers_have_real_descriptive_median(tmp_path):
    reg = registry()
    vals = {code: {"value": 12.5, "year": "2024"} for code in reg}
    policy = render_distribution(v3.BASE[0], vals, reg, tmp_path / "equal.png", "png")
    assert policy["median_unweighted_descriptive"] == 12.5
    assert policy["municipalities"] == 27
    assert policy["names_displayed"] == 27
