import io
import zipfile

from epah_diagnosis.istat_building_stock import parse_cpa_zip


def test_parse_cpa_zip_finds_required_table():
    table = (
        "PRO_COM;E3;E8;E9;E10;E11;E12;E13;E14;E15;E16\n"
        "001001;100;10;10;10;10;10;20;10;10;10\n"
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("readme.txt", "not a census table")
        archive.writestr("Sezioni_2011.csv", table)

    result = parse_cpa_zip(buffer.getvalue())

    assert len(result) == 1
    assert result[0].municipality_code == "001001"
    assert result[0].buildings_pre_1981 == 50
    assert result[0].share_pre_1981 == 50.0
