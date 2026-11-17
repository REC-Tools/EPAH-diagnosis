"""Prepare a local scheduled Codex task without invoking a paid model API.

GitHub metadata reads use gh's existing login. This command never invokes a
model, installs a schedule, changes the checkout or writes to GitHub.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

import v0_4_agent_cycle as policy


def prepare(root: Path, output: Path, issue: int | None = None) -> dict:
    root = root.resolve()
    output = output.resolve()
    if issue is not None and (type(issue) is not int or issue <= 0):
        raise ValueError("Issue number must be positive")
    if output.is_relative_to(root) or output.exists():
        raise ValueError("Choose a NEW plan directory outside the working checkout")
    top = Path(policy._git(root, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    if top != root:
        raise ValueError("Use the Git checkout root, not a subdirectory")
    if policy._git(root, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("Local task requires a clean checkout; preserve unfinished work")
    base = policy._git(root, "rev-parse", "HEAD").decode().strip()
    # Derive identity from the active gh credential, never a supplied actor name.
    # This authenticates the local login, not a GitHub-hosted workflow actor.
    actor = policy._gh("user").get("login")
    if not isinstance(actor, str):
        raise ValueError("Authenticated GitHub login is missing")
    snapshot = policy.live_snapshot(actor, issue)
    if snapshot["base_sha"] != base:
        raise ValueError("Checkout differs from current main; update a disposable checkout first")
    result = policy.write_plan(snapshot, output, simulation=False, issue=issue)
    if result["status"] == "ready":
        # Desktop tasks read the plan directly: no fixed shared /tmp input and
        # no secrets, installation or model subprocess in this preflight.
        prompt = policy.PROMPT.replace(policy.TASK_INPUT_FILE, str(output / "issue_input.json"))
        prompt += (
            "\nLOCAL REVIEW ONLY: do not call paid model APIs or the GitHub Action.\n"
            "Return the proposed diff for human review; do not commit or publish it.\n"
            "Use the trusted base patch gate and locked checks; a plan alone is not approval.\n"
        )
        (output / "local_task.txt").write_text(prompt, encoding="utf-8")
    return {
        "status": result["status"], "reason": result["reason"],
        "base_sha": base, "actor": actor,
        "identity_source": "authenticated_local_gh_login",
        "model_invoked": False, "schedule_installed": False,
        "github_writes": False, "publication_allowed": False,
        "scientific_approval": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--issue", type=int)
    args = parser.parse_args(argv)
    try:
        result = prepare(args.repo, args.out_dir, args.issue)
    except (ValueError, OSError, UnicodeError, subprocess.SubprocessError) as exc:
        parser.exit(2, f"BLOCKED: {exc}\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
