import csv
from pathlib import Path

from epah_diagnosis.climate import load_reference, summarize

ROOT = Path(__file__).resolve().parents[1]


def test_climate_artifacts_and_matrix_consistency():
    reference = load_reference(ROOT / "data/reference/climate_dpr412_green_community.csv")
    by_name = {record.municipality: record for record in reference}
    with (ROOT / "data/indicators/heating_degree_days.csv").open(encoding="utf-8", newline="") as file:
        output = list(csv.DictReader(file))
    with (ROOT / "data/verification_matrix.csv").open(encoding="utf-8", newline="") as file:
        matrix = list(csv.DictReader(file))
    climate = [row for row in matrix if row["indicator_id"] == "heating_degree_days"]
    assert len(output) == len(climate) == len(reference) == 27
    assert len({r["municipality"] for r in output}) == 27
    assert len(matrix) == 243
    for row in output:
        original = by_name[row["municipality"]]
        assert int(row["heating_degree_days"]) == original.heating_degree_days
        assert row["climate_zone"] == original.climate_zone
    for row in climate:
        assert row["status"] == "Dato acquisito"
        assert int(row["value"]) == by_name[row["municipality"]].heating_degree_days
    with (ROOT / "data/indicators/heating_degree_days_summary.csv").open(encoding="utf-8", newline="") as file:
        totals = list(csv.DictReader(file))
    assert len(totals) == 1
    summary = summarize(reference)
    for field in ("municipality_count", "zone_f_count", "zone_e_count",
                  "min_heating_degree_days", "max_heating_degree_days"):
        assert int(totals[0][field]) == summary[field]
