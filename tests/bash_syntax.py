"""Check Bash source without Windows executable or text-stream ambiguity."""
from pathlib import Path
import shutil
import subprocess


def check_bash_syntax(script: str, *, label: str) -> None:
    """Parse the exact UTF-8 source with the Bash selected by PATH; never run it."""
    executable = shutil.which("bash")
    if executable is None:
        raise RuntimeError(
            "Bash is required for workflow syntax checks. Install Bash (Git for "
            "Windows on Windows) and put its directory on PATH."
        )
    # CreateProcess can select the System32 WSL launcher before PATH when only
    # given 'bash'. Passing the resolved executable honors the chosen tool.
    command = [str(Path(executable).resolve()), "-n"]
    try:
        # Text-mode stdin changes LF to CRLF on Windows, breaking here-documents
        # in shells that do not ignore CR. Preserve the JSON workflow's source.
        subprocess.run(command, input=script.encode("utf-8"),
                       capture_output=True, check=True)
    except subprocess.CalledProcessError as exc:
        diagnostic = exc.stderr.decode("utf-8", errors="replace").strip()
        raise AssertionError(
            f"Bash syntax check failed for {label} using {command[0]} "
            f"(exit {exc.returncode}): {diagnostic}"
        ) from exc
