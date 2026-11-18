"""Offline application service for the reviewed v0.4 output chain.

No scientific calculations or source acquisition live here. The existing
builders and independent audits retain their own input and semantic gates.
Plans are informational: execution always builds its own allowlisted plan.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, fields
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
STATUS = "technical_draft_do_not_publish"
CANDIDATES = ("h47_zip", "h50_dir", "h46_dir", "h03_dir", "h04_dir", "h05_dir", "housing_dir")


@dataclass(frozen=True)
class ReviewInputs:
    bundle: Path
    registry: Path
    release_config: Path
    h47_zip: Path | None = None
    h50_dir: Path | None = None
    h46_dir: Path | None = None
    h03_dir: Path | None = None
    h04_dir: Path | None = None
    h05_dir: Path | None = None
    housing_dir: Path | None = None


def _path(path: Path, root: Path) -> Path:
    return (root / path).resolve() if not path.is_absolute() else path.resolve()


def load_inputs_file(path: Path) -> tuple[ReviewInputs, dict]:
    """Read declarative source paths only; never execute a saved plan or commands."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate input configuration key: {key}")
            result[key] = value
        return result

    path = path.resolve()
    raw = path.read_bytes()
    document = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique)
    if (not isinstance(document, dict) or set(document) != {"schema_version", "inputs"}
            or document["schema_version"] != "0.4-review-inputs-1"):
        raise ValueError("Expected a 0.4-review-inputs-1 configuration containing only inputs")
    values = document["inputs"]
    allowed = {field.name for field in fields(ReviewInputs)}
    if (not isinstance(values, dict) or not {"bundle", "registry", "release_config"} <= set(values)
            or set(values) - allowed):
        raise ValueError("Input configuration requires bundle/registry/release_config and known source keys only")
    if any(not isinstance(value, str) or not value.strip() for value in values.values()):
        raise ValueError("Input configuration paths must be nonempty strings")
    inputs = ReviewInputs(**{key: _path(Path(value), path.parent) for key, value in values.items()})
    return inputs, {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(),
                    "relative_paths_base": "configuration_directory"}


def make_plan(inputs: ReviewInputs, out_dir: Path, *, root: Path = ROOT,
              allow_incomplete: bool = False, input_configuration: dict | None = None) -> dict:
    """Read-only plan; input presence is not scientific or semantic validation."""
    root = root.resolve()
    raw_target = root / out_dir if not out_dir.is_absolute() else out_dir
    target = raw_target.resolve()
    if raw_target.is_symlink() or target.exists():
        raise FileExistsError("Choose a new run directory; preserve previous evidence")
    if target == root or any(target.is_relative_to(root / name) for name in (
        "src", "scripts", "tests", "docs", "data", "config", ".git", ".github", ".agents", ".codex",
    )):
        raise ValueError("Run output must be outside protected project directories")
    values = {}
    for field in fields(inputs):
        value = getattr(inputs, field.name)
        if value is None:
            continue
        value = _path(value, root)
        directory = field.name == "bundle" or field.name.endswith("_dir")
        if not (value.is_dir() if directory else value.is_file()):
            raise ValueError(f"Missing local input: {field.name}")
        if target.is_relative_to(value) or value.is_relative_to(target):
            raise ValueError("Run output and source inputs must not overlap")
        values[field.name] = str(value)
    if ("h03_dir" in values) != ("h04_dir" in values):
        raise ValueError("Supply H03 and H04 together from the same reviewed extraction")
    missing = [name for name in CANDIDATES if name not in values]
    common = ["--registry", values["registry"]]
    candidates = [arg for name in CANDIDATES if name in values
                  for arg in ("--" + name.replace("_", "-"), values[name])]
    counts = [arg for name in CANDIDATES[:3] if name in values
              for arg in ("--" + name.replace("_", "-"), values[name])]
    steps = [
        ("atlas", "build_v0_4_visual_atlas.py", ["--bundle", values["bundle"], *common,
         "--release-config", values["release_config"], *candidates, "--out-dir", str(target / "atlas")]),
        ("review", "build_v0_4_review_pack.py", ["--atlas-dir", str(target / "atlas"),
         *common, *counts, "--out-dir", str(target / "review")]),
        ("hub", "build_v0_4_output_hub.py", ["--atlas-dir", str(target / "atlas"),
         "--review-dir", str(target / "review"), "--out-dir", str(target / "hub")]),
        ("audit_pack", "audit_v0_4_output_quality.py", ["--pack", str(target / "review"),
         "--atlas", str(target / "atlas"), "--json-out", str(target / "qa/pack.json")]),
        ("audit_hub", "audit_v0_4_output_quality.py", ["--hub", str(target / "hub"),
         "--json-out", str(target / "qa/hub.json")]),
    ]
    commands = []
    for name, script, args in steps:
        implementation = root / "scripts" / script
        if not implementation.is_file():
            raise ValueError(f"Missing reviewed script: {script}; use a source checkout")
        commands.append({"name": name, "command": [sys.executable, "-B", str(implementation), *args]})
    return {"schema_version": "0.4-output-run-plan-1", "status": STATUS,
            "scientific_approval": False, "publication_allowed": False,
            "network_download": False, "destination": str(target), "inputs": values,
            "allow_incomplete": allow_incomplete, "missing_candidate_arguments": missing,
            "can_run": allow_incomplete or not missing,
            "input_validation": "presence_only; builders and audits must still pass",
            "steps": commands, **({"input_configuration": input_configuration}
                                  if input_configuration is not None else {})}


def _save_receipt(path: Path, receipt: dict) -> None:
    # Only updates this run's own receipt, never an input or product manifest.
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     prefix=".run-", suffix=".json", delete=False) as handle:
        temporary = Path(handle.name)
        json.dump(receipt, handle, ensure_ascii=False, indent=2)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run(inputs: ReviewInputs, out_dir: Path, *, root: Path = ROOT,
        allow_incomplete: bool = False, runner=None, input_configuration: dict | None = None) -> dict:
    """Run the allowlisted chain, stopping at the first failure and retaining QA."""
    plan = make_plan(inputs, out_dir, root=root, allow_incomplete=allow_incomplete,
                     input_configuration=input_configuration)
    if not plan["can_run"]:
        raise ValueError("Incomplete inputs; recover missing candidates or explicitly use --allow-incomplete")
    target = Path(plan["destination"])
    target.mkdir(parents=True, exist_ok=False)
    (target / "logs").mkdir()
    (target / "qa").mkdir()
    receipt = {"schema_version": "0.4-output-run-1", "status": "running",
               "scientific_approval": False, "publication_allowed": False,
               "plan": plan, "steps": []}
    receipt_path = target / "run.json"
    _save_receipt(receipt_path, receipt)
    execute = subprocess.run if runner is None else runner
    environment = {**os.environ, "PYTHONPATH": str(root.resolve() / "src") + os.pathsep +
                   os.environ.get("PYTHONPATH", ""), "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        for step in plan["steps"]:
            with (target / "logs" / (step["name"] + ".log")).open("x", encoding="utf-8") as log:
                result = execute(step["command"], cwd=root, env=environment,
                                 stdout=log, stderr=subprocess.STDOUT, check=False)
            receipt["steps"].append({"name": step["name"], "exit_code": result.returncode})
            _save_receipt(receipt_path, receipt)
            if result.returncode:
                raise RuntimeError(f"Stage {step['name']} failed; inspect this run's logs")
        atlas = _json(target / "atlas/atlas_manifest.json")
        pending = atlas.get("indicators_pending")
        available = atlas.get("indicators_available")
        if (atlas.get("indicator_slots") != 16 or atlas.get("municipalities") != 27
                or atlas.get("status") != STATUS or atlas.get("publication_allowed") is not False
                or not isinstance(pending, list) or not isinstance(available, list)
                or len(set(pending + available)) != 16 or len(pending + available) != 16):
            raise ValueError("Atlas does not satisfy the 27 x 16 technical snapshot contract")
        for filename, expected in (("pack.json", "technical_output_consistency_passed"),
                                   ("hub.json", "technical_bundle_consistency_passed")):
            audit = _json(target / "qa" / filename)
            if (audit.get("status") != expected or audit.get("scientific_approval") is not False
                    or audit.get("publication_allowed") is not False):
                raise ValueError(f"Missing or unsuccessful independent audit: {filename}")
        if pending and not allow_incomplete:
            raise ValueError("Missing indicator observations; a complete output run was requested")
        names = ("atlas/atlas_manifest.json", "review/manifest.json", "hub/manifest.json",
                 "qa/pack.json", "qa/hub.json")
        receipt.update(status="technical_review_incomplete" if pending else "technical_review_ready",
                       indicators_available=available, indicators_pending=pending,
                       complete_snapshot=not pending, visual_review_completed=False,
                       artifacts_sha256={n: hashlib.sha256((target / n).read_bytes()).hexdigest() for n in names})
    except Exception as exc:
        receipt.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        _save_receipt(receipt_path, receipt)
        raise
    _save_receipt(receipt_path, receipt)
    return receipt


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Plan or run the offline v0.4 output chain")
    parser.add_argument("action", choices=("plan", "run"))
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--bundle", type=Path)
    source.add_argument("--inputs-file", type=Path, help="Declarative local source paths; never a saved plan")
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--release-config", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--allow-incomplete", action="store_true",
                        help="Explicitly permit a technical snapshot with absent candidates")
    for name in CANDIDATES:
        parser.add_argument("--" + name.replace("_", "-"), type=Path)
    args = parser.parse_args(argv)
    try:
        configuration = None
        if args.inputs_file is not None:
            if any(getattr(args, name) is not None for name in ("registry", "release_config", *CANDIDATES)):
                raise ValueError("Do not mix --inputs-file with individual input options")
            inputs, configuration = load_inputs_file(_path(args.inputs_file, ROOT))
        else:
            values = {field.name: getattr(args, field.name) for field in fields(ReviewInputs)}
            values["registry"] = values["registry"] or ROOT / "data/municipalities.csv"
            values["release_config"] = values["release_config"] or ROOT / "config/release_v0_1.json"
            inputs = ReviewInputs(**values)
        operation = make_plan if args.action == "plan" else run
        result = operation(inputs, args.out_dir, allow_incomplete=args.allow_incomplete,
                           **({"input_configuration": configuration} if configuration is not None else {}))
    except (ValueError, OSError, RuntimeError) as exc:
        parser.exit(2, f"BLOCKED: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
