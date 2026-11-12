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

    pipeline = command.add_parser("pipeline", help="Plan or run guarded technical QA pipelines")
    pipeline.add_argument("pipeline_args", nargs=argparse.REMAINDER,
                          help="plan|run --profile <name> --out-dir <fresh-folder> ...")

    cit = command.add_parser("cit", help="Prepare a human-only CIT source review dossier")
    cit_actions = cit.add_subparsers(dest="cit_command", required=True)
    packet = cit_actions.add_parser("review-packet", help="Create an internal Pont source clarification packet")
    packet.add_argument("--run-dir", type=Path, required=True)
    packet.add_argument("--out-dir", type=Path, required=True)

    report = command.add_parser("report", help="Create independent technical diagnostic reports")
    report_versions = report.add_subparsers(dest="report_version", required=True)
    report_v02 = report_versions.add_parser("v0.2", help="V0.2 technical PDF from verified v0.1 pilot")
    report_v02.add_argument("--bundle", type=Path, help="Existing v0.1 pilot bundle")
    report_v02.add_argument("--out-dir", type=Path, help="New output directory, never overwritten")

    sheets = command.add_parser("sheets", help="Build 27 technical municipal PDF factsheets")
    sheets_actions = sheets.add_subparsers(dest="sheets_version", required=True)
    sheets_v02 = sheets_actions.add_parser("v0.2")
    sheets_v02.add_argument("--bundle", type=Path)
    sheets_v02.add_argument("--out-dir", type=Path)

    analysis = command.add_parser("analysis", help="Independent municipal comparisons")
    analysis_commands = analysis.add_subparsers(dest="analysis_version", required=True)
    analysis_v02 = analysis_commands.add_parser("v0.2")
    analysis_v02.add_argument("--bundle", type=Path)
    analysis_v02.add_argument("--out-dir", type=Path)

    dashboard = command.add_parser("dashboard", help="Create offline technical dashboard")
    dashboard_actions = dashboard.add_subparsers(dest="dashboard_version", required=True)
    dashboard_v02 = dashboard_actions.add_parser("v0.2")
    dashboard_v02.add_argument("--analysis-dir", type=Path)
    dashboard_v02.add_argument("--bundle", type=Path)
    dashboard_v02.add_argument("--out-dir", type=Path)

    review = command.add_parser("review-pack", help="Generate internal nonpublishable v0.2 review bundle")
    review_versions = review.add_subparsers(dest="review_version", required=True)
    review_v02 = review_versions.add_parser("v0.2")
    for option in ("bundle", "report-dir", "sheets-dir", "analysis-dir",
                   "dashboard-dir", "out-dir"):
        review_v02.add_argument("--" + option, type=Path)

    audit_release = command.add_parser("audit", help="Read-only postbuild technical v0.2 checks")
    audit_actions = audit_release.add_subparsers(dest="audit_version", required=True)
    audit_v02 = audit_actions.add_parser("v0.2", help="Verify local review folder and ZIP integrity")
    audit_v02.add_argument("--dir", type=Path)

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
             "--catalog", str(catalog),
             "--municipalities", str(ROOT / "data" / "municipalities.csv")),
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

    if args.command == "pipeline":
        from .pipeline import main as pipeline_main
        return pipeline_main(args.pipeline_args)

    if args.command == "cit":
        return _script(
            "build_cit_source_review_packet.py",
            "--run-dir", str(args.run_dir), "--out-dir", str(args.out_dir),
        )

    if args.command == "report":
        cmd = []
        if args.bundle is not None:
            cmd.extend(["--bundle", str(args.bundle)])
        if args.out_dir is not None:
            cmd.extend(["--out-dir", str(args.out_dir)])
        return _script("build_v0_2_territorial_report.py", *cmd)

    if args.command == "sheets":
        flags = []
        if args.bundle is not None:
            flags.extend(["--bundle", str(args.bundle)])
        if args.out_dir is not None:
            flags.extend(["--out-dir", str(args.out_dir)])
        return _script("build_v0_2_municipality_sheets.py", *flags)

    if args.command == "analysis":
        values = []
        if args.bundle is not None:
            values.extend(["--bundle", str(args.bundle)])
        if args.out_dir is not None:
            values.extend(["--out-dir", str(args.out_dir)])
        return _script("build_v0_2_multidimensional_analysis.py", *values)

    if args.command == "dashboard":
        flags = []
        for key, flag in (("analysis_dir", "--analysis-dir"), ("bundle", "--bundle"),
                          ("out_dir", "--out-dir")):
            value = getattr(args, key)
            if value is not None:
                flags.extend([flag, str(value)])
        return _script("build_v0_2_dashboard.py", *flags)

    if args.command == "review-pack":
        flags = []
        for option in ("bundle", "report_dir", "sheets_dir", "analysis_dir",
                       "dashboard_dir", "out_dir"):
            value = getattr(args, option)
            if value is not None:
                flags.extend(["--" + option.replace("_", "-"), str(value)])
        return _script("build_v0_2_review_package.py", *flags)

    if args.command == "audit":
        flags = ["--dir", str(args.dir)] if args.dir else []
        return _script("check_v0_2_review_package.py", *flags)

    if args.command == "replay":
        return _script("check_pilot_replay.py", str(args.first), str(args.second))

    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
