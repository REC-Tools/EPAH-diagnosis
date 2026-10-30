"""Audit three local accessibility drafts as a read-only release review packet.

No source downloads, no canonical matrix writes, and no human sign-off inferred.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
INDICATORS = {
    "dea_accessibility": ("dea_accessibility_v01", "dea_accessibility_minutes.csv", "dea_accessibility_qa.json", "data_csv_sha256", "nearest_dea_code"),
    "rail_accessibility": ("rail_accessibility_v01", "rail_accessibility_minutes.csv", "rail_accessibility_qa.json", "data_csv_sha256", "nearest_service_code"),
    "upper_secondary_accessibility": ("upper_secondary_accessibility_v01", "upper_secondary_accessibility_minutes.csv", "upper_secondary_accessibility_qa.json", "data_csv_sha256", "nearest_service_code"),
}
DESTINATIONS = {
    "rail_accessibility": ("active_rail_gateways_review_snapshot.csv", "destination_csv_sha256"),
    "upper_secondary_accessibility": ("upper_secondary_poles_2024_25.csv", "destination_csv_sha256"),
}


class QualityFiles:
    def __init__(self, directory: Path | None = None, archive: Path | None = None):
        if (directory is None) == (archive is None):
            raise ValueError("Supply either a directory or ZIP, not both")
        self.directory = directory
        self.archive = archive

    def read(self, relative: str) -> bytes:
        if self.directory is not None:
            return (self.directory / relative).read_bytes()
        with ZipFile(self.archive) as bundle:
            names = set(bundle.namelist())
            for prefix in ("quality/", ""):
                candidate = prefix + relative
                if candidate in names:
                    return bundle.read(candidate)
        raise FileNotFoundError(f"Missing member in quality ZIP: {relative}")


def _json(raw: bytes) -> dict:
    return json.loads(raw.decode("utf-8-sig"))


def _csv(raw: bytes) -> list[dict]:
    return list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig")), strict=True))


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _check_sha(content: bytes, declared: str | None, label: str, problems: list[str]) -> None:
    if not declared or _hash(content) != declared:
        problems.append(f"{label}: SHA-256 inconsistent with QA report")


def _source_audit(files: QualityFiles, directory: str, expected: list[str], problems: list[str]) -> dict:
    try:
        audit = _json(files.read(f"{directory}/audit.json"))
    except (OSError, ValueError, KeyError) as exc:
        problems.append(f"{directory}: missing or invalid intake report: {exc}")
        return {}
    results = audit.get("original_source_results", {})
    for name in expected:
        result = results.get(name, {})
        if result.get("status") != "technical_preflight_pass" or not result.get("technical_preflight_passed"):
            problems.append(f"{directory}: {name} did not pass source preflight")
    return results


def evaluate(files: QualityFiles, municipality_csv: bytes) -> dict:
    problems: list[str] = []
    registry = _csv(municipality_csv)
    expected = {row["istat_code"] for row in registry}
    if len(expected) != 27 or len(registry) != 27:
        problems.append("Canonical registry must contain 27 distinct ISTAT codes")

    road_sources = _source_audit(files, "access_inputs_manual_v01", ["road", "boundaries"], problems)
    mim_sources = _source_audit(files, "access_inputs_mim_202425", ["school_registry", "school_pathways"], problems)
    details: dict[str, dict] = {}
    observations: dict[str, dict] = {}
    for indicator, (folder, csv_name, qa_name, hash_key, dest_column) in INDICATORS.items():
        qa = _json(files.read(f"{folder}/{qa_name}"))
        data_bytes = files.read(f"{folder}/{csv_name}")
        _check_sha(data_bytes, qa.get(hash_key), f"{indicator}/data", problems)
        rows = _csv(data_bytes)
        by_origin = {row["municipality_code"]: row for row in rows}
        if len(rows) != 27 or len(by_origin) != 27 or set(by_origin) != expected:
            problems.append(f"{indicator}: origins do not match the 27 canonical municipalities")
        if qa.get("indicator_id") != indicator or qa.get("origin_count") != 27:
            problems.append(f"{indicator}: QA indicator ID or origin_count mismatch")
        if qa.get("qa_status") != "technical_checks_only" or qa.get("validated_for_release") is not False:
            problems.append(f"{indicator}: expected unvalidated technical-only QA status")
        for origin, row in by_origin.items():
            if not row.get(dest_column) or len(row[dest_column]) != 6 or not row[dest_column].isdigit():
                problems.append(f"{indicator}: invalid destination code for {origin}")
            try:
                minutes = float(row["travel_time_minutes"])
                km = float(row["distance_km"])
                if not (math.isfinite(minutes) and 0 <= minutes <= 1440 and
                        math.isfinite(km) and km >= 0):
                    raise ValueError("out of range")
            except (ValueError, TypeError, KeyError):
                problems.append(f"{indicator}: invalid time or distance for {origin}")
        n = (qa.get("eligible_dea_municipality_count") if indicator == "dea_accessibility"
             else qa.get("destination_municipality_count"))
        observed_pairs = qa.get("route_pair_count", qa.get("complete_route_pairs"))
        if not isinstance(n, int) or not isinstance(observed_pairs, int) or observed_pairs != 27 * n or qa.get("expected_route_pairs") != observed_pairs:
            problems.append(f"{indicator}: incomplete origin-by-destination route grid")
        if indicator in DESTINATIONS:
            destination_file, key = DESTINATIONS[indicator]
            dest_bytes = files.read(f"{folder}/{destination_file}")
            _check_sha(dest_bytes, qa.get(key), f"{indicator}/destinations", problems)
            destinations = _csv(dest_bytes)
            codes = {row["municipality_code"] for row in destinations}
            if len(destinations) != n or len(codes) != n or not {r[dest_column] for r in rows} <= codes:
                problems.append(f"{indicator}: selected service not in candidate destination list")
        summary_bytes = files.read(f"{folder}/{indicator}_summary.csv")
        _check_sha(summary_bytes, qa.get("summary_csv_sha256"), f"{indicator}/summary", problems)
        for source_id in ("road", "boundaries"):
            intake_hash = road_sources.get(source_id, {}).get("sha256")
            qa_hash = qa.get("road_zip_sha256" if source_id == "road" else "boundaries_zip_sha256")
            if not intake_hash or intake_hash != qa_hash:
                problems.append(f"{indicator}: {source_id} original SHA disagrees with intake")
        if indicator == "upper_secondary_accessibility":
            for source_id in ("school_registry", "school_pathways"):
                if not mim_sources.get(source_id, {}).get("sha256") or qa.get(f"{source_id}_sha256") != mim_sources[source_id]["sha256"]:
                    problems.append(f"{indicator}: {source_id} SHA disagrees with MIM intake")
        details[indicator] = {
            "origins": len(by_origin), "candidate_destinations": n,
            "routes_reported": observed_pairs, "qa_status": qa.get("qa_status"),
            "validated_for_release": False,
            "data_sha256": _hash(data_bytes),
            "human_checks_pending": sorted(k for k, v in qa.items() if k.endswith("_reviewed") and v is False),
        }
        observations[indicator] = by_origin

    rail = observations["rail_accessibility"]
    school = observations["upper_secondary_accessibility"]
    matches = [code for code in sorted(expected) if code in rail and code in school and
               all(rail[code][field] == school[code][field]
                   for field in ("nearest_service_code", "travel_time_minutes", "distance_km"))]
    pattern = Counter(rail[code]["nearest_service_code"] for code in matches)
    return {
        "schema_version": "1.0", "study_municipalities": len(expected),
        "indicator_results": details, "technical_integrity_pass": not problems,
        "technical_blockers": problems,
        "school_rail_identical_triples": len(matches),
        "school_rail_identical_origins": matches,
        "school_rail_shared_destinations_by_code": dict(sorted(pattern.items())),
        "interpretation": "Identical school/rail minimum municipality, minutes, and km do not establish independent indicators; verify service coverage and avoid double-counting.",
        "release_authorized": False, "human_review_required": True,
    }


def render(report: dict) -> str:
    lines = ["# Accessibility v0.1 — independent review packet", "",
             f"Technical consistency: **{'PASS' if report['technical_integrity_pass'] else 'FAIL'}** (not scientific validation).", "",
             "| Indicator | Origins | Eligible destinations | Routes | Human review |",
             "| --- | ---: | ---: | ---: | --- |"]
    for name, item in report["indicator_results"].items():
        lines.append(f"| {name} | {item['origins']} | {item['candidate_destinations']} | {item['routes_reported']} | Required |")
    lines += ["", f"**School/rail matching destinations, times and km:** {report['school_rail_identical_triples']}/27 origins.",
              "This is a correlation alert, not an automatic source error. Neither indicator should be treated as independently confirming the other.", "",
              "## Decisions still required", "",
              "- DEA: independently reconcile Piemonte-only candidate DEA I/II list with Ministry of Health network active in 2025; check cross-region alternatives.",
              "- School: independently verify complete 2024/25 offering and compare available 2026/27 registry; do not relabel historical 2024/25 offering as current.",
              "- Rail: verify passenger-train service, bus substitutions and eligible gateway coverage at publication date.",
              "- All: audit at least three original ISTAT route pairs per indicator, historical municipality crosswalk, licences, source authenticity and review evidence.",
              "- Record actual reviewer, dated evidence URL and methodological scope decision before invoking finalizers. No simulated approvals.", "",
              f"**Release authorized: {report['release_authorized']}**. Matrix was not modified.", ""]
    if report["technical_blockers"]:
        lines += ["", "## Technical blockers", ""]
        lines += [f"- {msg}" for msg in report["technical_blockers"]]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit QA ZIP or directory, without promoting data")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--quality-dir", type=Path)
    source.add_argument("--quality-zip", type=Path)
    parser.add_argument("--registry", type=Path, default=ROOT / "data/municipalities.csv")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "outputs/quality/accessibility_candidate_review")
    parser.add_argument("--strict", action="store_true", help="Fail on technical integrity mismatch; human review remains separate")
    args = parser.parse_args()
    report = evaluate(QualityFiles(args.quality_dir, args.quality_zip), args.registry.read_bytes())
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "review_packet.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.out_dir / "review_packet.md").write_text(render(report), encoding="utf-8")
    print(render(report), end="")
    if args.strict and not report["technical_integrity_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
