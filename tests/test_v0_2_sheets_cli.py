"""Ensure the unified command delegates rather than altering scientific data."""
from __future__ import annotations

from epah_diagnosis import workflow_cli


def test_sheets_cli_dispatch(monkeypatch, tmp_path):
    called = []
    monkeypatch.setattr(workflow_cli, "_script",
                        lambda *args: called.append(args) or 0)
    bundle = tmp_path / "original"
    dest = tmp_path / "new"
    assert workflow_cli.main([
        "sheets", "v0.2", "--bundle", str(bundle), "--out-dir", str(dest)
    ]) == 0
    assert called == [
        ("build_v0_2_municipality_sheets.py",
         "--bundle", str(bundle), "--out-dir", str(dest))
    ]
    assert not dest.exists()
