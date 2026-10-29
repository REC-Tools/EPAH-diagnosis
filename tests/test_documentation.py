"""Guard the operational documentation against dead local links and commands."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_documentation_references_are_valid() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_documentation.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
