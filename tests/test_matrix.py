from epah_diagnosis.cli import build_matrix, validate_matrix, write_matrix


def test_build_matrix_has_three_checks_per_municipality():
    municipalities = ["Comune A", "Comune B"]
    rows = build_matrix(municipalities)

    assert len(rows) == 6
    assert all(row["status"] == "Da verificare" for row in rows)


def test_validate_matrix(tmp_path):
    matrix = tmp_path / "matrix.csv"
    write_matrix(build_matrix(["Comune A", "Comune B"]), matrix)

    municipalities, checks, errors = validate_matrix(matrix)

    assert municipalities == 2
    assert checks == 6
    assert errors == []
