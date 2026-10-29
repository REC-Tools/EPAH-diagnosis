"""Fail-closed PR scope gate for canonical EPAH data and source evidence.

Runs from a trusted base-branch copy in GitHub Actions. It examines the
actual Git diff, not a PR author's self-reported file list. It does not
certify scientific data or grant release/methodology approval.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

MATRIX = "data/verification_matrix.csv"
PROTECTED_PREFIXES = ("data/indicators/", "data/quality/", "data/reference/")
PROTECTED_PATHS = {
    MATRIX, "data/municipalities.csv", "config/indicators.json",
    "config/sources.json", "config/release_v0_1.json",
    "config/release_reviews_v0_1.json",
}
FIELDS = ("municipality", "indicator_id", "status", "value")


@dataclass(frozen=True)
class Change:
    status: str
    path: str
    old_path: str | None = None


def protected(path: str) -> bool:
    return path in PROTECTED_PATHS or path.startswith(PROTECTED_PREFIXES)


def changed_protected(changes: list[Change]) -> list[Change]:
    return [c for c in changes if protected(c.path) or
            (c.old_path is not None and protected(c.old_path))]


def declarations(body: str, key: str) -> list[str]:
    return [
        item.strip() for item in re.findall(
            rf"(?im)^[ \t]*{re.escape(key)}:[ \t]*(.+?)[ \t]*$",
            body,
        )
    ]


def csv_index(content: str) -> dict[tuple[str, str], dict[str, str]]:
    reader = csv.DictReader(io.StringIO(content, newline=""))
    if not reader.fieldnames or not set(FIELDS).issubset(reader.fieldnames):
        raise ValueError("Canonical matrix missing required columns")
    result: dict[tuple[str, str], dict[str, str]] = {}
    for row in reader:
        key = (row["municipality"], row["indicator_id"])
        if not all(key) or key in result:
            raise ValueError(f"Empty or duplicate matrix key: {key}")
        result[key] = row
    return result


def matrix_problems(before: str, after: str, body: str) -> list[str]:
    """Protect row identity and require explicit consent for value regressions."""
    previous, current = csv_index(before), csv_index(after)
    errors: list[str] = []
    removed = set(previous) - set(current)
    added = set(current) - set(previous)
    if removed or added:
        errors.append(
            f"Matrix key set changed: {len(removed)} removed, {len(added)} added; "
            "perform a separate, reviewed migration instead."
        )
    allowed_downgrades = set(declarations(body, "Data-downgrade"))
    allowed_revisions = set(declarations(body, "Data-revise"))
    for key in sorted(set(previous) & set(current)):
        old, new = previous[key], current[key]
        indicator = key[1]
        if (old["status"] == "Dato validato" and
                new["status"] != "Dato validato" and
                indicator not in allowed_downgrades):
            errors.append(
                f"{key}: validated status would be downgraded; "
                f"explicitly document 'Data-downgrade: {indicator}' after QA."
            )
        if (old["status"] == "Dato acquisito" and
                new["status"] in {"Da verificare", "Fonte individuata"} and
                indicator not in allowed_downgrades):
            errors.append(
                f"{key}: acquired status would be downgraded; "
                f"add 'Data-downgrade: {indicator}' after QA."
            )
        important = ("value", "year", "unit", "source_url")
        if (old["status"] == "Dato validato" and
                new["status"] == "Dato validato" and
                any(old.get(field) != new.get(field) for field in important) and
                indicator not in allowed_revisions):
            errors.append(
                f"{key}: validated value/source/year changed; "
                f"add 'Data-revise: {indicator}' and evidence."
            )
    return errors


def scope_problems(changes: list[Change], body: str, *, before: str | None = None,
                   after: str | None = None) -> list[str]:
    sensitive = changed_protected(changes)
    if not sensitive:
        return []
    errors = []
    if declarations(body, "Data-change") != ["yes"]:
        errors.append(
            "Protected files changed but PR body lacks the exact line "
            "'Data-change: yes' (once). See docs/data_change_protection.md."
        )
    evidence = declarations(body, "Data-evidence")
    if (len(evidence) != 1 or len(evidence[0]) < 8 or
            evidence[0].startswith("[") or
            not (re.match(r"^https://[^\s]+$", evidence[0]) or
                 re.match(r"^(docs|data|config|outputs)/[^\s]+$", evidence[0]))):
        errors.append("Add one concrete 'Data-evidence: <path or URL>' line.")
    if declarations(body, "Data-review") != ["required"]:
        errors.append("Add the exact line 'Data-review: required'.")
    # A contradictory assurance is particularly dangerous: PR #80 did this.
    contradictions = (
        r"\bNON\s+modifica\s+(?:i\s+)?dati\b",
        r"\bNON\s+modifica\s+(?:la\s+)?(?:matrice|data/verification_matrix\.csv)\b",
        r"\bnessuna\s+modifica\s+(?:ai\s+)?dati\b",
        r"\b(?:no|without)\s+data\s+changes\b",
        r"\bmatrix\s+unchanged\b",
    )
    if any(re.search(expr, body, re.IGNORECASE) for expr in contradictions):
        errors.append(
            "PR asserts that data/matrix are unchanged, but protected paths "
            "are modified. Correct the PR scope; do not hide the diff."
        )
    allowed_deletions = set(declarations(body, "Data-delete"))
    for change in sensitive:
        if change.status == "D" and change.path not in allowed_deletions:
            errors.append(
                f"Protected deletion {change.path!r} needs exact "
                f"'Data-delete: {change.path}' in the PR body."
            )
        if change.status == "R" and change.old_path and protected(change.old_path):
            if change.old_path not in allowed_deletions:
                errors.append(
                    f"Protected rename from {change.old_path!r} needs "
                    f"'Data-delete: {change.old_path}'."
                )
    if any(c.path == MATRIX or c.old_path == MATRIX for c in sensitive):
        if before is None or after is None:
            errors.append("Matrix changed but base/head CSV comparison is missing.")
        else:
            try:
                errors.extend(matrix_problems(before, after, body))
            except (csv.Error, ValueError, TypeError, KeyError) as exc:
                errors.append(f"Invalid canonical matrix in diff: {exc}")
    return errors


def diff_changes(base: str, head: str) -> list[Change]:
    raw = subprocess.check_output(
        ["git", "diff", "--name-status", "-z", "--find-renames", base, head]
    )
    parts = raw.decode("utf-8", "surrogateescape").split("\0")
    if parts[-1] == "":
        parts.pop()
    result = []
    position = 0
    while position < len(parts):
        status = parts[position]
        position += 1
        kind = status[0]
        if kind in ("R", "C"):
            old_path, path = parts[position:position + 2]
            position += 2
            result.append(Change("R" if kind == "R" else "C", path, old_path))
        else:
            path = parts[position]
            position += 1
            result.append(Change(kind, path))
    return result


def git_file(revision: str, path: str) -> str:
    return subprocess.check_output(
        ["git", "show", f"{revision}:{path}"], text=True, encoding="utf-8"
    )


def valid_approval(reviews: list[dict], author: str, head: str) -> bool:
    """Use latest decisive review per reviewer; reject stale and self reviews."""
    decisions: dict[str, dict] = {}
    for review in reviews:
        user = review.get("user") or {}
        login = user.get("login", "")
        state = review.get("state")
        if not login or login.casefold() == author.casefold():
            continue
        if state in {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"}:
            decisions[login.casefold()] = review
    return any(
        entry.get("state") == "APPROVED" and entry.get("commit_id") == head
        for entry in decisions.values()
    )


def fetch_reviews(repository: str, number: int, token: str) -> list[dict]:
    """Paginate the official GitHub review API; fail rather than assume approval."""
    if not token:
        raise ValueError("GITHUB_TOKEN unavailable for authenticated review check")
    reviews = []
    for page in range(1, 21):
        request = Request(
            f"https://api.github.com/repos/{repository}/pulls/{number}/reviews"
            f"?per_page=100&page={page}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "EPAH-data-guard",
            },
        )
        with urlopen(request, timeout=20) as response:
            batch = json.load(response)
        if not isinstance(batch, list):
            raise ValueError("GitHub review API did not return a list")
        reviews.extend(batch)
        if len(batch) < 100:
            return reviews
    raise ValueError("Review pagination exceeds safety limit")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="PR base commit SHA")
    parser.add_argument("--head", required=True, help="PR head commit SHA")
    parser.add_argument("--event", required=True, help="GitHub event JSON")
    parser.add_argument("--require-review", action="store_true")
    args = parser.parse_args()
    try:
        with open(args.event, encoding="utf-8") as handle:
            event = json.load(handle)
        pr = event["pull_request"]
        body = pr.get("body") or ""
        changes = diff_changes(args.base, args.head)
        sensitive = changed_protected(changes)
        print(
            f"PR #{pr['number']}: {len(changes)} changed paths, "
            f"{len(sensitive)} protected; draft={pr.get('draft', False)}"
        )
        before = after = None
        if any(c.path == MATRIX or c.old_path == MATRIX for c in sensitive):
            before = git_file(args.base, MATRIX)
            after = git_file(args.head, MATRIX)
        problems = scope_problems(changes, body, before=before, after=after)
        if sensitive and args.require_review:
            if pr.get("draft"):
                print("REVIEW PENDING: draft data PR cannot be merged; "
                      "human approval will be checked when ready.")
            else:
                reviews = fetch_reviews(
                    os.environ.get("GITHUB_REPOSITORY", ""),
                    int(pr["number"]), os.environ.get("GITHUB_TOKEN", ""),
                )
                if not valid_approval(reviews, pr["user"]["login"], args.head):
                    problems.append(
                        "Protected data PR requires a GitHub APPROVED review "
                        "by another account for the current head commit. "
                        "It must be authenticated; a self-declared JSON flag "
                        "or PR body is not approval."
                    )
    except (OSError, KeyError, TypeError, ValueError, subprocess.CalledProcessError,
            HTTPError, URLError) as exc:
        print(f"BLOCK: unable to verify scope safely: {exc}")
        return 1
    if problems:
        for problem in problems[:30]:
            print("BLOCK:", problem)
        if len(problems) > 30:
            print(f"BLOCK: {len(problems) - 30} additional problems omitted")
        return 1
    print("PASS: PR scope integrity checked (not a scientific release approval).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
