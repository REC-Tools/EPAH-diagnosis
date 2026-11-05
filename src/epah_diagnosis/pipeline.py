"""Fail-closed orchestration of technical EPAH intake and QA-only workflows.

Two strictly allowlisted profiles:
  cit-quarantine: local original SHA check -> fuel/age drafts -> 26-town QA
  accessibility-intake: explicit local/official acquisition -> technical audit
Never calls a finalizer, canonical release builder, map or PDF publisher.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_BASE = Path("outputs/quality")
CIT_HASHES = {
    "fuel": "7659242c31a4dd47d24e4d65b9075f90845a8f81829eff27cf485c24027793b4",
    "age": "4b506567cb3ea3aeb355eed021a30aa83f4c55d6729e9ae99bb825e71484712a",
}
ACCESS_SOURCES = {
    "road": "--road-zip",
    "boundaries": "--boundaries-zip",
    "school_registry": "--school-registry",
    "school_pathways": "--school-pathways",
}
STATUS_CIT = "technical_incomplete_do_not_publish"
STATUS_ACCESS = "technical_source_intake_only_do_not_publish"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _absolute(path: Path, root: Path) -> Path:
    return (path if path.is_absolute() else root / path).resolve()


def _new_destination(path: Path, root: Path) -> Path:
    target = _absolute(path, root)
    base = (root / OUTPUT_BASE).resolve()
    if target == base or not target.is_relative_to(base):
        raise ValueError("Pipeline output must be a fresh directory under outputs/quality/")
    if target.exists():
        raise FileExistsError("Preserve prior QA evidence; choose a fresh --out-dir")
    return target


def _verified_source(path: Path, label: str, expected: str | None = None) -> dict:
    if not path.is_file():
        raise ValueError(f"{label}: required original file missing: {path}")
    actual = _sha256(path)
    if expected is not None and actual != expected:
        raise ValueError(f"{label}: original SHA-256 mismatch; do not reinterpret or repair source")
    return {"name": label, "file_name": path.name, "sha256": actual}


def _step(name: str, script: str, *args: str, root: Path) -> dict:
    file = root / "scripts" / script
    if not file.is_file():
        raise ValueError(f"Missing reviewed implementation: {file}")
    return {"name": name, "command": [sys.executable, str(file), *args]}


def make_plan(args: argparse.Namespace, root: Path = ROOT) -> dict:
    root = root.resolve()
    target = _new_destination(args.out_dir, root)
    registry = root / "data/municipalities.csv"
    _verified_source(registry, "canonical_municipality_registry")
    if args.profile == "cit-quarantine":
        if args.download or args.sources is not None or any(
            getattr(args, key) is not None for key in ACCESS_SOURCES.values()
            for key in [key.lstrip("-").replace("-", "_")]
        ):
            raise ValueError("CIT accepts only local --fuel-source and --age-source; no downloads")
        if args.fuel_source is None or args.age_source is None or args.as_of is None:
            raise ValueError("CIT requires --fuel-source, --age-source and --as-of")
        try:
            date.fromisoformat(args.as_of)
        except ValueError as exc:
            raise ValueError("--as-of must be YYYY-MM-DD (analysis date, not source vintage)") from exc
        fuel = _absolute(args.fuel_source, root)
        age = _absolute(args.age_source, root)
        if fuel == age:
            raise ValueError("Fuel and age originals must be distinct files")
        inputs = [
            _verified_source(fuel, "fuel", CIT_HASHES["fuel"]),
            _verified_source(age, "age", CIT_HASHES["age"]),
        ]
        fuel_dir = target / "cit_fuel"
        age_dir = target / "cit_age"
        review_dir = target / "cit_review"
        stages = [
            _step(
                "prepare_fuel", "prepare_piemonte_cit_wide.py",
                "--mode", "fuel", "--input", str(fuel),
                "--as-of", args.as_of, "--registry", str(registry),
                "--quarantine-conflicts", "--out-dir", str(fuel_dir),
                root=root,
            ),
            _step(
                "prepare_age", "prepare_piemonte_cit_wide.py",
                "--mode", "age", "--input", str(age),
                "--as-of", args.as_of, "--registry", str(registry),
                "--quarantine-conflicts", "--out-dir", str(age_dir),
                root=root,
            ),
            _step(
                "qa_compare", "build_v0_2_cit_quarantine_comparison.py",
                "--fuel-dir", str(fuel_dir), "--age-dir", str(age_dir),
                "--registry", str(registry), "--out-dir", str(review_dir),
                root=root,
            ),
        ]
        return {
            "profile": args.profile, "destination": str(target),
            "inputs": inputs, "reference_date": args.as_of,
            "network_download": False, "steps": stages,
            "review_file": str(review_dir / "cit_26_qa_summary.json"),
            "review_status": STATUS_CIT, "publication_allowed": False,
        }

    if args.profile != "accessibility-intake":
        raise ValueError("Unknown pipeline profile")
    if any(x is not None for x in (args.fuel_source, args.age_source, args.as_of)):
        raise ValueError("Accessibility intake does not accept CIT inputs")
    selected = tuple(x.strip() for x in (args.sources or "road,boundaries").split(","))
    if (not selected or len(set(selected)) != len(selected)
            or any(x not in ACCESS_SOURCES for x in selected)):
        raise ValueError("Select distinct, known accessibility source IDs")
    extra = []
    inputs = []
    for source, flag in ACCESS_SOURCES.items():
        local = getattr(args, flag.lstrip("-").replace("-", "_"))
        if local is not None:
            if source not in selected:
                raise ValueError(f"{source}: add source to --sources before supplying local original")
            original = _absolute(local, root)
            inputs.append(_verified_source(original, source))
            extra.extend([flag, str(original)])
        elif source in selected and not args.download:
            raise ValueError(f"{source}: supply a local file or explicitly enable --download")
    stages = [
        _step(
            "official_source_intake", "acquire_accessibility_inputs.py",
            "--sources", ",".join(selected),
            "--out-dir", str(target / "intake"), "--strict",
            *(["--download"] if args.download else []),
            *extra,
            root=root,
        ),
    ]
    return {
        "profile": args.profile, "destination": str(target),
        "inputs": inputs, "selected_sources": list(selected),
        "network_download": bool(args.download), "steps": stages,
        "review_file": str(target / "intake/audit.json"),
        "review_status": STATUS_ACCESS, "publication_allowed": False,
    }


def _execute_command(command: list[str], root: Path) -> int:
    return subprocess.run(command, cwd=root, check=False).returncode


def _validate_review(plan: dict) -> dict:
    file = Path(plan["review_file"])
    review = json.loads(file.read_text(encoding="utf-8"))
    if plan["profile"] == "cit-quarantine":
        excluded = review.get("excluded") or []
        if (review.get("status") != "technical_QA_only_incomplete_do_not_publish"
                or review.get("valid_municipalities") != 26
                or review.get("municipalities_expected") != 27
                or len(excluded) != 1
                or excluded[0].get("istat_code") != "001199"):
            raise ValueError("CIT review is not the expected quarantined 26/27 technical evidence")
        return {
            "review_status": review["status"],
            "valid_municipalities": 26,
            "excluded_istat_codes": ["001199"],
            "review_sha256": _sha256(file),
        }
    if (review.get("all_selected_inputs_available") is not True
            or review.get("selected_source_count") != len(plan["selected_sources"])
            or review.get("validated_for_release") is not False
            or review.get("automatic_promotions") != 0):
        raise ValueError("Official accessibility source intake is incomplete or lacks release safeguards")
    return {
        "review_status": STATUS_ACCESS,
        "available_sources": review["selected_source_count"],
        "review_sha256": _sha256(file),
    }


def execute(plan: dict, root: Path = ROOT) -> int:
    target = Path(plan["destination"])
    target.mkdir(parents=True, exist_ok=False)
    report = {
        "schema_version": "1.0",
        "profile": plan["profile"],
        "created_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "run_status": "blocked",
        "publication_allowed": False,
        "scientific_approval": "not_assessed",
        "automatic_promotions": 0,
        "canonical_files_modified_by_orchestrator": False,
        "source_inputs": plan["inputs"],
        "steps": [],
    }
    try:
        for step in plan["steps"]:
            print(f"EPAH pipeline: {step['name']}", flush=True)
            code = _execute_command(step["command"], root)
            report["steps"].append({"name": step["name"], "return_code": code})
            if code:
                raise ValueError(f"{step['name']}: implementation exited with code {code}")
        report["review"] = _validate_review(plan)
        report["run_status"] = plan["review_status"]
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        report["blocked_reason"] = f"{type(exc).__name__}: {exc}"
        print("BLOCKED:", report["blocked_reason"], file=sys.stderr)
    (target / "pipeline_run_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
    )
    print("Report:", target / "pipeline_run_report.json")
    if report["run_status"] == "blocked":
        return 1
    print("Technical QA completed. NOT APPROVED FOR PUBLICATION.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="epah pipeline",
        description="Guarded technical pipelines: plan first; run only explicitly",
    )
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("plan", "run"):
        p = sub.add_parser(action, help=("Dry-run: no files written" if action == "plan"
                                         else "Execute allowlisted QA-only steps"))
        p.add_argument("--profile", choices=("cit-quarantine", "accessibility-intake"), required=True)
        p.add_argument("--out-dir", type=Path, required=True,
                       help="FRESH directory under outputs/quality (no overwrite)")
        p.add_argument("--fuel-source", type=Path)
        p.add_argument("--age-source", type=Path)
        p.add_argument("--as-of", help="CIT local analysis date YYYY-MM-DD")
        p.add_argument("--sources", help="Accessibility: comma-separated official source IDs")
        for flag in ACCESS_SOURCES.values():
            p.add_argument(flag, type=Path)
        p.add_argument("--download", action="store_true",
                       help="Accessibility only: explicitly request official HTTPS source downloads")
    args = parser.parse_args(argv)
    try:
        plan = make_plan(args)
        if args.action == "plan":
            print(json.dumps(plan, indent=2, ensure_ascii=False))
            print("PLAN ONLY: no download, output or matrix changes.")
            return 0
        return execute(plan)
    except (OSError, ValueError, FileExistsError) as exc:
        print("BLOCKED:", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
