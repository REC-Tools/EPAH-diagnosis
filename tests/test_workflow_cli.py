"""Offline and non-mutating orchestration tests for the unified EPAH CLI."""
from __future__ import annotations

import pytest

from epah_diagnosis import workflow_cli as cli


def test_status_reports_both_gates_without_claiming_pilot_approval(monkeypatch):
    calls = []
    def fake(name, *argv):
        calls.append((name, argv))
        return 1 if name == "check_pilot_inputs.py" else 0
    monkeypatch.setattr(cli, "_script", fake)
    assert cli.main(["status"]) == 0
    assert calls == [
        ("check_v0_1_readiness.py", ("--phase", "inputs", "--report-only")),
        ("check_pilot_inputs.py", ()),
    ]


def test_status_does_not_hide_unexpected_canonical_failure(monkeypatch):
    calls = []
    def fake(name, *argv):
        calls.append(name)
        return 2
    monkeypatch.setattr(cli, "_script", fake)
    assert cli.main(["status"]) == 2
    assert calls == ["check_v0_1_readiness.py"]


def test_sources_check_preserves_missing_source_exit_status(monkeypatch, tmp_path):
    calls = []
    def fake(name, *argv):
        calls.append((name, argv))
        return 1
    monkeypatch.setattr(cli, "_script", fake)
    report = tmp_path / "new.json"
    assert cli.main(["sources", "check", "--json-out", str(report)]) == 1
    assert calls == [("check_pilot_inputs.py", ("--json-out", str(report)))]
    assert not report.exists()


def test_data_validate_reuses_existing_validators_in_order(monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "_call", lambda *argv: calls.append(("module", argv)) or 0)
    monkeypatch.setattr(cli, "_script", lambda name, *argv: calls.append((name, argv)) or 0)
    assert cli.main(["data", "validate"]) == 0
    assert calls[0][1][:3] == ("-m", "epah_diagnosis.cli", "validate-matrix")
    assert calls[0][1][-2:] == ("--municipalities", str(cli.ROOT / "data/municipalities.csv"))
    assert calls[1][0] == "check_municipality_registry.py"
    assert calls[2][0] == "check_framework.py"


def test_validation_failure_stops_without_running_other_checks(monkeypatch):
    called = []
    monkeypatch.setattr(cli, "_call", lambda *argv: 1)
    monkeypatch.setattr(cli, "_script", lambda *argv: called.append(argv) or 0)
    assert cli.main(["data", "validate"]) == 1
    assert not called


@pytest.mark.parametrize("profile,expected", [
    ("pilot", "build_v0_1_owner_accepted.py"),
    ("canonical", "build_v0_1_bundle.py"),
])
def test_build_delegates_to_existing_guarded_builder(monkeypatch, tmp_path, profile, expected):
    calls = []
    monkeypatch.setattr(cli, "_script", lambda name, *argv: calls.append((name, argv)) or 0)
    out = tmp_path / "fresh"
    assert cli.main(["build", "--profile", profile, "--output-dir", str(out)]) == 0
    assert calls == [(expected, ("--output-dir", str(out)))]
    assert not out.exists()


def test_archive_cannot_be_sent_to_canonical_builder(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(cli, "_script", lambda *argv: calls.append(argv))
    with pytest.raises(SystemExit) as err:
        cli.main(["build", "--profile", "canonical", "--archive", str(tmp_path / "x.zip")])
    assert err.value.code == 2
    assert not calls


def test_pilot_archive_forwarded_without_overwrite_override(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(cli, "_script", lambda name, *argv: calls.append((name, argv)) or 0)
    archive = tmp_path / "new.zip"
    assert cli.main(["build", "--profile", "pilot", "--archive", str(archive)]) == 0
    assert calls == [
        ("build_v0_1_owner_accepted.py", ("--archive", str(archive)))
    ]


def test_replay_delegates_to_existing_read_only_comparator(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(cli, "_script", lambda name, *argv: calls.append((name, argv)) or 0)
    first, second = tmp_path / "first", tmp_path / "second"
    assert cli.main(["replay", "compare", str(first), str(second)]) == 0
    assert calls == [("check_pilot_replay.py", (str(first), str(second)))]


def test_missing_script_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    assert cli._script("nonexistent.py") == 2

def test_local_audit_uses_read_only_inventory(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        cli, "_script", lambda name, *args: calls.append((name, args)) or 0
    )
    assert cli.main(["local", "audit"]) == 0
    target = tmp_path / "new-inventory.json"
    assert cli.main(["local", "audit", "--json-out", str(target)]) == 0
    assert calls == [
        ("audit_local_artifacts.py", ()),
        ("audit_local_artifacts.py", ("--json-out", str(target))),
    ]
    assert not target.exists()

def test_pipeline_is_dispatched_without_implicit_execution(monkeypatch):
    from epah_diagnosis import pipeline as pipeline_module
    called = []
    monkeypatch.setattr(
        pipeline_module, "main",
        lambda argv: called.append(argv) or 0,
    )
    assert cli.main(["pipeline", "plan", "--profile", "cit-quarantine",
                     "--out-dir", "outputs/quality/unique"]) == 0
    assert called == [
        ["plan", "--profile", "cit-quarantine",
         "--out-dir", "outputs/quality/unique"]
    ]


def test_pipeline_run_requires_explicit_action_and_profile():
    from epah_diagnosis import pipeline as pipeline_module
    import pytest
    with pytest.raises(SystemExit) as missing_profile:
        pipeline_module.main(["run", "--out-dir", "outputs/quality/example"])
    assert missing_profile.value.code == 2

def test_cit_review_packet_dispatch_reuses_existing_guarded_script(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        cli, "_script", lambda name, *argv: calls.append((name, argv)) or 0
    )
    run = tmp_path / "qa-source"
    output = tmp_path / "qa-destination"
    assert cli.main([
        "cit", "review-packet", "--run-dir", str(run),
        "--out-dir", str(output),
    ]) == 0
    assert calls == [(
        "build_cit_source_review_packet.py",
        ("--run-dir", str(run), "--out-dir", str(output)),
    )]
    assert not output.exists()

def test_v02_report_dispatch_only_invokes_guarded_builder(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(cli, "_script", lambda name, *args: calls.append((name, args)) or 0)
    bundle = tmp_path / "pilot"
    out = tmp_path / "new-v02"
    assert cli.main(["report", "v0.2", "--bundle", str(bundle), "--out-dir", str(out)]) == 0
    assert calls == [
        ("build_v0_2_territorial_report.py",
         ("--bundle", str(bundle), "--out-dir", str(out)))
    ]
    assert not out.exists()

