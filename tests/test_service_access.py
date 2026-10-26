import csv
import io
import zipfile

from epah_diagnosis.service_access import nearest_services_from_zip


def _matrix_zip() -> bytes:
    text = io.StringIO()
    writer = csv.writer(text, delimiter=";")
    writer.writerow([
        "OR_DEST",
        "OR_REG",
        "OR_PROV",
        "OR_PROCOM",
        "DEST_REG",
        "DEST_PROV",
        "DEST_PROCOM",
        "TEP_TOT",
        "KM_TOT",
        "TTP_TOT",
    ])
    writer.writerow(["001001001125", "01", "001", "1001", "01", "001", "1125", "35,5", "42,0", "31,0"])
    writer.writerow(["001001001086", "01", "001", "1001", "01", "001", "1086", "28,0", "33,0", "25,0"])
    writer.writerow(["001002001125", "01", "001", "1002", "01", "001", "1125", "20,0", "21,0", "18,0"])
    writer.writerow(["001002001272", "01", "001", "1002", "01", "001", "1272", "50,0", "60,0", "45,0"])

    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("R01_TO.csv", text.getvalue())
    return payload.getvalue()


def test_nearest_services_from_zip_selects_fastest_dea_by_istat_code():
    results = nearest_services_from_zip(
        _matrix_zip(),
        {"001001": "Comune A", "001002": "Comune B"},
        {"001125": "Ivrea", "001086": "Cirie", "001272": "Torino"},
    )

    by_name = {result.municipality: result for result in results}

    assert by_name["Comune A"].service_municipality == "Cirie"
    assert by_name["Comune A"].travel_time_minutes == 28.0
    assert by_name["Comune A"].distance_km == 33.0
    assert by_name["Comune B"].service_municipality == "Ivrea"
    assert by_name["Comune B"].travel_time_minutes == 20.0
