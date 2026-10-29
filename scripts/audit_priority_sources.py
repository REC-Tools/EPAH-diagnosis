"""Audit the three priority official sources, without promoting matrix data.

Windows example:
  python scripts/audit_priority_sources.py --download

Or use original files saved via an institutional web browser:
  python scripts/audit_priority_sources.py --altitude-xlsx PATH --snai-xlsx PATH --annex-html PATH

The raw original files and JSON evidence remain untracked in outputs/quality/.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from epah_diagnosis.priority_source_audit import (
    OFFICIAL_SOURCES, audit_workbook, compare_current_annex,
    fetch_official, sha256_bytes,
)
from epah_diagnosis.territorial_context_qa import write_draft


ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "data/verification_matrix.csv"
REGISTRY = ROOT / "data/municipalities.csv"
SNAPSHOT = ROOT / "data/reference/climate_dpr412_green_community.csv"
OUTPUT = ROOT / "outputs/quality/priority_source_audit"
INDICATORS = ("heating_degree_days", "mean_altitude", "snai_classification")


def matrix_status(path: Path) -> dict:
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    report = {}
    for iid in INDICATORS:
        selected = [r for r in rows if r["indicator_id"] == iid]
        report[iid] = {
            "rows": len(selected),
            "status_counts": dict(sorted(Counter(r["status"] for r in selected).items())),
            "values_present": sum(bool(r["value"].strip()) for r in selected),
        }
    return report


def run(
    out_dir: Path,
    registry: Path,
    snapshot: Path,
    matrix: Path,
    source_files: dict[str, Path | None],
    *,
    download: bool = False,
) -> dict:
    """Create an evidence report. Errors are explicit blockers, not false approvals."""
    if (out_dir / "audit.json").exists():
        raise FileExistsError("Audit exists; use a new --out-dir for a new run")
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "goal": "Official-source audit for three priority core indicators (81 observations)",
        "matrix_before": matrix_status(matrix),
        "indicator_results": {},
        "matrix_modified": False,
        "automatic_promotions": 0,
        "validated_for_release": False,
        "human_review_required": True,
    }
    files = dict(source_files)
    for iid in INDICATORS:
        item = {"source_url": OFFICIAL_SOURCES[iid]["url"],
                "status": "not_acquired", "validated_for_release": False,
                "human_reviewed": False}
        source = files.get(iid)
        if download and source is None:
            source = out_dir / "raw" / OFFICIAL_SOURCES[iid]["filename"]
            try:
                item["download"] = fetch_official(iid, source)
            except (OSError, ValueError, TimeoutError) as exc:
                item["status"] = "download_failed"
                item["error"] = f"{type(exc).__name__}: {exc}"
                report["indicator_results"][iid] = item
                continue
        if source is None:
            report["indicator_results"][iid] = item
            continue
        item["original_source_path"] = str(source)
        try:
            if iid == "heating_degree_days":
                qa = compare_current_annex(source.read_bytes(), snapshot, registry)
                destination = out_dir / iid
                destination.mkdir(parents=True, exist_ok=True)
                (destination / "consolidated_annex_comparison.json").write_text(
                    json.dumps(qa, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                item.update({
                    "status": "technical_pass" if qa["technical_crosscheck_passed"] else "blocked",
                    "technical_comparison": qa["technical_crosscheck_passed"],
                    "values_match_on_27_municipalities": qa["values_match_on_27_municipalities"],
                    "edition_marker_present": qa["edition_marker_present"],
                    "edition_marker_location": qa["edition_marker_location"],
                    "annex_title_present": qa["annex_title_present"],
                    "blocking_reason": qa["blocking_reason"],
                    "source_to_table_rows_parsed": qa["source_to_table_rows_parsed"],
                    "rows_examined": qa["rows_examined"],
                    "missing_municipalities": qa["missing_municipalities"],
                    "differences": qa["differences"],
                    "official_file_sha256": qa["official_file_sha256"],
                    "qa_report": "consolidated_annex_comparison.json",
                })
            else:
                rows, summary, qa = audit_workbook(iid, source, registry)
                # A second pass writes the exact canonical PR-05 draft and its
                # own SHA-256; no canonical matrix or data/indicators touched.
                draft = write_draft(iid, source, registry, out_dir / iid)
                item.update({
                    "status": "technical_pass",
                    "rows_examined": len(rows),
                    "official_file_sha256": qa["source_file_sha256"],
                    "qa_report": f"{iid}_qa.json",
                    "reference_year": draft["reference_year"],
                    "summary_rows": len(summary),
                })
        except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
            item["status"] = "blocked"
            item["error"] = f"{type(exc).__name__}: {exc}"
        report["indicator_results"][iid] = item
    report["technical_pass_count"] = sum(
        r["status"] == "technical_pass" for r in report["indicator_results"].values()
    )
    report["outstanding_checks"] = [
        f"{iid}: {r['status']}" for iid, r in report["indicator_results"].items()
        if r["status"] != "technical_pass"
    ] + [
        "Verify the official host, original source, reference year and licensing.",
        "Human sample review and 2021/2020-to-2026 municipality crosswalk.",
        "Only an independently documented review may approve release promotion.",
    ]
    report["matrix_after"] = matrix_status(matrix)
    if report["matrix_after"] != report["matrix_before"]:
        raise ValueError("Canonical verification matrix unexpectedly changed")
    (out_dir / "audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit official HDD 2016, ISTAT altitude 2021 and SNAI 2020, without validation"
    )
    parser.add_argument("--download", action="store_true",
                        help="Attempt official HTTPS downloads; report each failure")
    parser.add_argument("--annex-file", "--annex-html", dest="annex_html", type=Path,
                        help="Original official 2016 Annex A PDF, HTML, or plain text")
    parser.add_argument("--altitude-xlsx", type=Path, help="Original ISTAT altitude 2021 workbook")
    parser.add_argument("--snai-xlsx", type=Path, help="Original government SNAI 2020 workbook")
    parser.add_argument("--out-dir", type=Path, default=OUTPUT)
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT)
    parser.add_argument("--matrix", type=Path, default=MATRIX)
    parser.add_argument("--strict", action="store_true",
                        help="Exit 1 if any requested source lacks a technical pass")
    args = parser.parse_args()
    selected = {
        "heating_degree_days": args.annex_html,
        "mean_altitude": args.altitude_xlsx,
        "snai_classification": args.snai_xlsx,
    }
    report = run(args.out_dir, args.registry, args.snapshot, args.matrix,
                 selected, download=args.download)
    print("EPAH priority official-source audit (no automatic validation)")
    for iid, result in report["indicator_results"].items():
        reason = result.get("error") or result.get("blocking_reason")
        suffix = f" - {reason}" if reason else ""
        if iid == "heating_degree_days" and "rows_examined" in result:
            suffix += (
                f" (rows {result['rows_examined']}/27, "
                f"values match: {result['values_match_on_27_municipalities']}, "
                f"legal date found: {result['edition_marker_present']})"
            )
        print(f"  {iid}: {result['status']}{suffix}")
    print(f"Technical source checks passed: {report['technical_pass_count']}/3")
    print(f"Report: {args.out_dir / 'audit.json'}")
    print("Release unchanged: human reviews and promotion required.")
    if args.strict and report["technical_pass_count"] != 3:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
