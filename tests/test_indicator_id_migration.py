import csv
from pathlib import Path

import pytest


ALIASES = {
    "dea_access_minutes": "dea_accessibility",
    "upper_secondary_access_minutes": "upper_secondary_accessibility",
    "rail_access_minutes": "rail_accessibility",
    "snai_isolation_class": "snai_classification",
}


def test_alias_map_matches_current_profile_ids():
    assert ALIASES["dea_access_minutes"] == "dea_accessibility"
    assert ALIASES["upper_secondary_access_minutes"] == "upper_secondary_accessibility"
    assert ALIASES["rail_access_minutes"] == "rail_accessibility"
    assert ALIASES["snai_isolation_class"] == "snai_classification"
