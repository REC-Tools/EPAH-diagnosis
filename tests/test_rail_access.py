from pathlib import Path

from epah_diagnosis.rail_access import load_rail_gateways


def test_load_rail_gateways_filters_active_passenger(tmp_path: Path):
    path = tmp_path / "rail.csv"
    path.write_text(
        "station_name,municipality,province,status,source,source_url,notes\n"
        "Rivarolo,Rivarolo Canavese,Torino,active passenger rail,RFI,x,ok\n"
        "Pont,Pont Canavese,Torino,bus substitution,RFI,x,suspended rail\n",
        encoding="utf-8",
    )

    gateways = load_rail_gateways(path)

    assert len(gateways) == 1
    assert gateways[0].municipality == "Rivarolo Canavese"
