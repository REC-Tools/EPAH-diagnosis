"""Offline, synthetic checks for the non-mutating pilot preflight."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "pilot_input_preflight", ROOT / "scripts/check_pilot_inputs.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_missing_inputs_are_blocked_without_creating_directories(tmp_path):
    result = MODULE.inspect(tmp_path)
    assert result["preflight_status"] == "blocked"
    assert all(item["status"] == "missing" for item in result["inputs"].values())
    assert list(tmp_path.iterdir()) == []
    assert result["scientific_validation"] == "not_assessed"


def test_complete_synthetic_inputs_are_hashed_without_mutation(tmp_path):
    for relative in MODULE.INPUTS.values():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"synthetic test input\n")
    result = MODULE.inspect(tmp_path)
    assert result["preflight_status"] == "inputs_present"
    assert all(item["status"] == "present" for item in result["inputs"].values())
    assert all(len(item["sha256"]) == 64 for item in result["inputs"].values())
    assert all((tmp_path / relative).read_bytes() == b"synthetic test input\n"
               for relative in MODULE.INPUTS.values())


def test_directory_in_place_of_file_is_not_accepted(tmp_path):
    (tmp_path / MODULE.INPUTS["matrix"]).mkdir(parents=True)
    result = MODULE.inspect(tmp_path)
    assert result["inputs"]["matrix"]["status"] == "missing"
    assert result["preflight_status"] == "blocked"
