import io
import zipfile

import shapefile

from epah_diagnosis.geography import parse_boundaries_zip


def test_parse_boundaries_zip_filters_and_transforms(tmp_path):
    shp_base = tmp_path / "Com01012026_g_WGS84"
    writer = shapefile.Writer(str(shp_base), shapeType=shapefile.POLYGON)
    writer.field("PRO_COM_T", "C", size=6)
    writer.field("COMUNE", "C", size=80)

    writer.poly(
        [[
            [400000, 5000000],
            [401000, 5000000],
            [401000, 5001000],
            [400000, 5001000],
            [400000, 5000000],
        ]]
    )
    writer.record("001001", "Comune A")
    writer.close()

    (tmp_path / "Com01012026_g_WGS84.cpg").write_text("UTF-8", encoding="utf-8")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for suffix in (".shp", ".shx", ".dbf", ".cpg"):
            path = tmp_path / f"Com01012026_g_WGS84{suffix}"
            archive.write(path, f"Limiti01012026_g/Com01012026_g/Com01012026_g_WGS84{suffix}")

    result = parse_boundaries_zip(buffer.getvalue(), {"Comune A"})

    assert result["type"] == "FeatureCollection"
    assert len(result["features"]) == 1

    feature = result["features"][0]
    assert feature["properties"]["municipality_code"] == "001001"
    assert feature["properties"]["municipality"] == "Comune A"
    assert feature["geometry"]["type"] == "Polygon"

    first_x, first_y = feature["geometry"]["coordinates"][0][0]
    assert 5 < first_x < 15
    assert 40 < first_y < 50
