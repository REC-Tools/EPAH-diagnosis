import csv
import io
import zipfile

from epah_diagnosis.service_access import nearest_services_from_zip


def _matrix_zip() -> bytes:
    text = io.StringIO()
    writer = csv.writer(text, delimiter=";")
    writer.writerow([
        "Comune origine",
        "Comune destinazione",
        "Tempo_minuti",
        "Distanza_km",
    ])
    writer.writerow(["Comune A", "Ivrea", "35,5", "42,0"])
    writer.writerow(["Comune A", "Cirie", "28,0", "33,0"])
    writer.writerow(["Comune B", "Ivrea", "20,0", "21,0"])
    writer.writerow(["Comune B", "Torino", "50,0", "60,0"])

    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("matrix.csv", text.getvalue())
    return payload.getvalue()


def test_nearest_services_from_zip_selects_fastest_dea():
    results = nearest_services_from_zip(
        _matrix_zip(),
        {"Comune A", "Comune B"},
        {"Ivrea", "Cirie", "Torino"},
    )

    by_name = {result.municipality: result for result in results}

    assert by_name["Comune A"].service_municipality == "Cirie"
    assert by_name["Comune A"].travel_time_minutes == 28.0
    assert by_name["Comune B"].service_municipality == "Ivrea"
    assert by_name["Comune B"].travel_time_minutes == 20.0
