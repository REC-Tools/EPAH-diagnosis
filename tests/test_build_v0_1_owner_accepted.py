"""Fail-closed checks for owner-accepted technical pilot (synthetic data only)."""
import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_v0_1_owner_accepted.py"
SPEC = importlib.util.spec_from_file_location("owner_pilot", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def samples():
    return {
        "technical_pass": True, "routes_checked": 9, "matches": 9,
        "validated_for_release": False,
        "comparisons": [
            {"indicator_id": key, "matches_original": True}
            for key in MODULE.PILOT_FIELDS for _ in range(3)
        ],
    }


def test_nine_samples_required(tmp_path):
    path = tmp_path / "samples.json"
    path.write_text(json.dumps(samples()), encoding="utf-8")
    assert len(MODULE.check_sample_evidence(path)["comparisons"]) == 9


@pytest.mark.parametrize("modify", [
    lambda x: x.update(matches=8),
    lambda x: x["comparisons"][0].update(matches_original=False),
    lambda x: x.update(validated_for_release=True),
    lambda x: x["comparisons"].pop(),
])
def test_not_all_sample_checks_refused(tmp_path, modify):
    obj = samples()
    modify(obj)
    path = tmp_path / "samples.json"
    path.write_text(json.dumps(obj), encoding="utf-8")
    with pytest.raises(ValueError, match="9/9"):
        MODULE.check_sample_evidence(path)


def test_signoff_does_not_rewrite_canonical_data(tmp_path):
    assert "data/verification_matrix.csv" not in str(MODULE.EVIDENCE)
    assert MODULE.DATE == "2026-10-30"
    assert MODULE.OWNER == "Tommaso Ferrucci"
