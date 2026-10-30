"""Read-only status table from the strict v0.1 release gate JSON."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "release_v0_1.json"


def indicator_progress(report: dict, core: list[str]) -> list[dict]:
    """Exclude overlapping row blockers exactly once."""
    expected = report["municipalities"]
    blockers = report["blockers"]
    progress = []
    for indicator_id in core:
        blocked = set()
        for category in ("missing_core", "unvalidated_core", "empty_core_values"):
            blocked.update(blockers.get(category, {}).get(indicator_id, []))
        blocked.update(blockers.get("invalid_validated_rows", {}).get(indicator_id, {}))
        passed = expected - len(blocked)
        if not 0 <= passed <= expected:
            raise ValueError(f"Inconsistent readiness counts for {indicator_id}")
        progress.append({
            "indicator_id": indicator_id,
            "passed": passed,
            "expected": expected,
            "blocked": len(blocked),
            "reviewed": report["methodology_approved"]
            or (indicator_id not in report["review_blockers"]
                and "manifest" not in report["review_blockers"]),
        })
    return progress


def render_markdown(report: dict, config: dict) -> str:
    progress = indicator_progress(report, config["core_indicators"])
    passed = sum(item["passed"] for item in progress)
    total = sum(item["expected"] for item in progress)
    lines = [
        "## EPAH Diagnosis v0.1 — release progress",
        "",
        f"**Data prerequisites:** {passed}/{total} core observations ({passed / total:.1%}).",
        f"**Methodology approvals:** {'complete' if report['methodology_approved'] else 'pending'}.",
        f"**Input gate:** {'PASS' if report['inputs_ready'] else 'BLOCKED'}.",
        f"**Release gate:** {'PASS' if report['release_ready'] else 'BLOCKED'}.",
        "",
        "| Core indicator | Data gate | Methodology gate |",
        "| --- | ---: | --- |",
    ]
    for item in progress:
        lines.append(
            f"| {item['indicator_id']} | {item['passed']}/{item['expected']} | "
            f"{'PASS' if item['reviewed'] else 'pending'} |"
        )
    integrity = [
        key for key in ("configuration", "duplicates", "unexpected_municipalities",
                        "unexpected_indicators")
        if report["blockers"].get(key)
    ]
    if integrity:
        lines.extend(("", "**Additional integrity blockers:** " + ", ".join(integrity) + "."))
    if report["review_blockers"].get("manifest"):
        lines.extend(("", "**Review manifest:** missing or invalid."))
    lines.extend((
        "",
        "Data gate coverage does **not** constitute independent scientific "
        "review, official source authentication or release authorization.",
        "Bundle artifacts must be built and validated only after inputs pass.",
        "",
    ))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Report v0.1 progress without data changes")
    parser.add_argument("--readiness", type=Path, required=True)
    parser.add_argument("--release-config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = json.loads(args.readiness.read_text(encoding="utf-8"))
    config = json.loads(args.release_config.read_text(encoding="utf-8"))
    markdown = render_markdown(report, config)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(markdown, encoding="utf-8")
    print(markdown, end="")


if __name__ == "__main__":
    main()
