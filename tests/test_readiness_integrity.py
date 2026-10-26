import csv
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_integrated_profile_readiness.py"
spec = importlib.util.spec_from_file_location("readiness_checker", SCRIPT)
checker = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(checker)


def test_readiness_rejects_empty_matrix(tmp_path, monkeypatch, capsys):
    data = tmp_path / "data"
    data.mkdir()
    (data / "municipalities.csv").write_text(
        "municipality\n" + "".join(f"Comune {i}\n" for i in range(27)),
        encoding="utf-8",
    )
    (data / "verification_matrix.csv").write_text(
        "municipality,indicator_id,status\n", encoding="utf-8"
    )
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    monkeypatch.setattr(checker, "MATRIX_FILE", data / "verification_matrix.csv")
    with pytest.raises(SystemExit) as exc:
        checker.main()
    assert exc.value.code == 1
    assert "Missing indicators" in capsys.readouterr().out


def test_readiness_rejects_unexpected_and_duplicate_rows(tmp_path, monkeypatch, capsys):
    data = tmp_path / "data"
    data.mkdir()
    (data / "municipalities.csv").write_text(
        "municipality\n" + "".join(f"Comune {i}\n" for i in range(27)),
        encoding="utf-8",
    )
    with (data / "verification_matrix.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["municipality", "indicator_id", "status"])
        writer.writeheader()
        writer.writerow({"municipality": "Altro", "indicator_id": "population_65_plus", "status": "Dato validato"})
        writer.writerow({"municipality": "Altro", "indicator_id": "population_65_plus", "status": "Dato validato"})
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    monkeypatch.setattr(checker, "MATRIX_FILE", data / "verification_matrix.csv")
    with pytest.raises(SystemExit):
        checker.main()
    out = capsys.readouterr().out
    assert "Unexpected municipalities" in out
    assert "Duplicate municipality-indicator" in out
