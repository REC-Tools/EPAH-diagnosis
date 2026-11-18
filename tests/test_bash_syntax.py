"""Portable workflow syntax checks must preserve source and still reject errors."""
import shlex
import subprocess
import sys

import pytest

import bash_syntax


@pytest.mark.parametrize("script", [
    "if true; then\nprintf '%s' 'città sintetica'\nfi\n",
    "cat <<'END'\nSYNTHETIC ONLY\nEND\n",
])
def test_source_reaches_a_real_child_as_exact_utf8_bytes(tmp_path, monkeypatch, script):
    # A Python receiver observes the actual pipe bytes on every platform,
    # independently of Git Bash's tolerance for CRLF on some installations.
    selected = tmp_path / "chosen shell" / "bash.exe"
    selected.parent.mkdir()
    selected.touch()
    monkeypatch.setattr(bash_syntax.shutil, "which", lambda name: str(selected))
    run = subprocess.run
    commands = []

    def receive(command, **kwargs):
        commands.append(command)
        result = run([sys.executable, "-c",
                      "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())"], **kwargs)
        assert result.stdout == script.encode("utf-8")
        return result

    monkeypatch.setattr(bash_syntax.subprocess, "run", receive)
    bash_syntax.check_bash_syntax(script, label="synthetic byte transport")
    assert commands == [[str(selected.resolve()), "-n"]]


def test_valid_heredoc_is_parsed_without_executing_the_script(tmp_path):
    marker = tmp_path / "must-not-exist.txt"
    script = (
        "if true; then\ncat <<'END'\ncittà sintetica\nEND\n"
        f"printf executed > {shlex.quote(marker.as_posix())}\nfi\n"
    )
    bash_syntax.check_bash_syntax(script, label="valid synthetic here-document")
    assert not marker.exists()


@pytest.mark.parametrize("script", [
    "if true; then\ncat <<'END'\nSYNTHETIC ONLY\nEND\n",  # Missing fi.
    "printf '%s' 'unclosed synthetic quote\n",
    "if ; then\ntrue\nfi\n",
])
def test_invalid_shell_source_is_rejected(script):
    with pytest.raises(AssertionError, match="Bash syntax check failed for invalid synthetic"):
        bash_syntax.check_bash_syntax(script, label="invalid synthetic")


def test_missing_bash_is_an_actionable_failure_not_a_skip(monkeypatch):
    monkeypatch.setattr(bash_syntax.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError, match="Bash is required.*Git for Windows"):
        bash_syntax.check_bash_syntax("true\n", label="missing capability")
