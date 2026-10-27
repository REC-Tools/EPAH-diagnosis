import csv
import json
from pathlib import Path

import importlib.util


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_v0_1_readiness.py"
SPEC = importlib.util.spec_from_file_location("check_v0_1_readiness", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load check_v0_1_readiness.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
evaluate = MODULE.evaluate


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_v0_1_readiness_requires_all_core_values(tmp_path):
    municipalities = [f"Comune {i}" for i in range(27)]
    municipality_file = tmp_path / "municipalities.csv"
    _write_csv(
        municipality_file,
        ["municipality"],
        [{"municipality": name} for name in municipalities],
    )

    core = ["a", "b"]
    config = tmp_path / "release.json"
    config.write_text(
        json.dumps(
            {
                "release": "0.1.0",
                "core_indicators": core,
                "extensions": [],
                "release_criteria": {"municipalities": 27},
            }
        ),
        encoding="utf-8",
    )

    matrix = tmp_path / "matrix.csv"
    fields = ["municipality", "indicator_id", "status", "value"]
    rows = [
        {
            "municipality": municipality,
            "indicator_id": indicator,
            "status": "Dato validato",
            "value": "1",
        }
        for municipality in municipalities
        for indicator in core
    ]
    _write_csv(matrix, fields, rows)

    result = evaluate(matrix, municipality_file, config)
    assert result["ready"] is True

    rows[-1]["value"] = ""
    _write_csv(matrix, fields, rows)

    result = evaluate(matrix, municipality_file, config)
    assert result["ready"] is False
    assert "b" in result["blockers"]["empty_core_values"]
