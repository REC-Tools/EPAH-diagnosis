"""Single guarded entry point for EPAH diagnosis source-check and release tasks.

This is intentionally an orchestration layer over existing reviewed scripts.
It never changes approval state, canonical files, or individual builder gates.
Run from an editable repository checkout (pip install -e . / uv sync).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _call(*args: str) -> int:
    """Run one existing Python entry point; no shell, inherited stdio."""
    return subprocess.run([sys.executable, *args], cwd=ROOT, check=False).returncode


def _script(name: str, *args: str) -> int:
    """Refuse to run when installed outside the expected source checkout."""
    path = ROOT / "scripts" / name
    if not path.is_file():
        print(
            f"ERROR: Missing {path}. Use an editable checkout of the repository.",
            file=sys.stderr,
        )
        return 2
    return _call(str(path), *args)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="epah",
        description="Guarded EPAH diagnosis commands (source checkout required)",
    )
    command = parser.add_subparsers(dest="command", required=True)

    command.add_parser("status", help="Report pilot input availability and canonical readiness")

    sources = command.add_parser("sources", help="Inspect locally available pilot source inputs")
    sources_commands = sources.add_subparsers(dest="sources_command", required=True)
    sources_check = sources_commands.add_parser("check", help="Offline pilot input inventory")
    sources_check.add_argument("--json-out", type=Path, help="Write inventory to a NEW JSON file")

    data = command.add_parser("data", help="Validate canonical data and methodology")
    data_commands = data.add_subparsers(dest="data_command", required=True)
    data_commands.add_parser("validate", help="Read-only matrix, registry and catalog checks")

    local = command.add_parser("local", help="Inspect local untracked and ignored data")
    local_commands = local.add_subparsers(dest="local_command", required=True)
    audit = local_commands.add_parser("audit", help="Read-only Git inventory of local artifacts")
    audit.add_argument("--json-out", type=Path, help="Save to a NEW JSON file")

    build = command.add_parser("build", help="Generate an explicitly selected v0.1 bundle")
    build.add_argument("--profile", choices=("pilot", "canonical"), required=True)
    build.add_argument("--output-dir", type=Path, help="Choose a new output directory")
    build.add_argument("--archive", type=Path, help="Pilot only: choose a new ZIP path")

    replay = command.add_parser("replay", help="Compare existing build core datasets")
    replay_commands = replay.add_subparsers(dest="replay_command", required=True)
    compare = replay_commands.add_parser("compare", help="Read-only CSV/GeoJSON core comparison")
    compare.add_argument("first", type=Path)
    compare.add_argument("second", type=Path)

    args = parser.parse_args(argv)

    if args.command == "status":
        print("=== Canonical v0.1 input readiness (read-only, report-only) ===", flush=True)
        canonical = _script("check_v0_1_readiness.py", "--phase", "inputs", "--report-only")
        if canonical:
            return canonical
        print("=== Technical pilot local input inventory (not an approval) ===", flush=True)
        pilot = _script("check_pilot_inputs.py")
        if pilot == 1:
            print("Pilot input inventory is incomplete; this is not a canonical readiness failure.")
            return 0
        return pilot

    if args.command == "sources":
        argv = ["--json-out", str(args.json_out)] if args.json_out else []
        return _script("check_pilot_inputs.py", *argv)

    if args.command == "data":
        matrix = ROOT / "data" / "verification_matrix.csv"
        catalog = ROOT / "config" / "indicators.json"
        checks = (
            ("-m", "epah_diagnosis.cli", "validate-matrix", str(matrix),
             "--catalog", str(catalog)),
        )
        for check in checks:
            code = _call(*check)
            if code:
                return code
        for script in ("check_municipality_registry.py", "check_framework.py"):
            code = _script(script)
            if code:
                return code
        return 0

    if args.command == "local":
        argv = ["--json-out", str(args.json_out)] if args.json_out else []
        return _script("audit_local_artifacts.py", *argv)

    if args.command == "build":
        if args.profile == "canonical" and args.archive is not None:
            parser.error("--archive is only supported for --profile pilot")
        argv = ["--output-dir", str(args.output_dir)] if args.output_dir else []
        if args.profile == "pilot":
            if args.archive:
                argv.extend(["--archive", str(args.archive)])
            return _script("build_v0_1_owner_accepted.py", *argv)
        return _script("build_v0_1_bundle.py", *argv)

    if args.command == "replay":
        return _script("check_pilot_replay.py", str(args.first), str(args.second))

    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
