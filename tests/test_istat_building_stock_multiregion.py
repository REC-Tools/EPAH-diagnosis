import io
import zipfile

from epah_diagnosis.istat_building_stock import parse_cpa_zip


def test_parse_cpa_zip_supports_procom_and_merges_regions():
    r01 = (
        "CODREG;PROCOM;COMUNE;E3;E8;E9;E10;E11;E12;E13;E14;E15;E16\n"
        "1;001001;Comune A;100;10;10;10;10;10;20;10;10;10\n"
    )
    r02 = (
        "CODREG;PROCOM;COMUNE;E3;E8;E9;E10;E11;E12;E13;E14;E15;E16\n"
        "2;002001;Comune B;50;5;5;5;5;5;10;5;5;5\n"
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("Sezioni di Censimento/R01_indicatori_2011_sezioni.csv", r01)
        archive.writestr("Sezioni di Censimento/R02_indicatori_2011_sezioni.csv", r02)

    result = parse_cpa_zip(buffer.getvalue())

    assert len(result) == 2
    assert {item.municipality_code for item in result} == {"001001", "002001"}
    assert result[0].buildings_pre_1981 == 50
    assert result[1].buildings_pre_1981 == 25
