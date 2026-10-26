from pathlib import Path

from epah_diagnosis.climate import load_reference, summarize


def test_climate_reference_has_27_valid_records(tmp_path: Path):
    data = """municipality,province,climate_zone,heating_degree_days,municipal_seat_altitude_m
"""
    rows = []
    for index in range(27):
        zone = "F" if index < 20 else "E"
        gg = 3200 + index if zone == "F" else 2600 + index
        rows.append(f"Comune {index},TO,{zone},{gg},{500 + index}")
    path = tmp_path / "climate.csv"
    path.write_text(data + "\n".join(rows) + "\n", encoding="utf-8")

    records = load_reference(path)
    summary = summarize(records)

    assert len(records) == 27
    assert summary["zone_f_count"] == 20
    assert summary["zone_e_count"] == 7
    assert summary["max_heating_degree_days"] > summary["min_heating_degree_days"]
