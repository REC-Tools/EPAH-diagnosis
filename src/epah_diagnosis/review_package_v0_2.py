"""Fail-closed v0.2 editorial review pack, explicitly NOT a public release.

Combines the separately audited technical report, municipal sheets,
descriptive analysis and local dashboard only when all lineage hashes
point to the same verified pilot. Human approvals stay pending.
"""
from __future__ import annotations

import csv
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

from pypdf import PdfReader

from epah_diagnosis.analysis_v0_2 import compare
from epah_diagnosis.release_artifacts import sha256_file
from epah_diagnosis.report_v0_2 import verified_data

STATUS = "technical_review_candidate_not_authorized_for_publication"
SOURCE_STATUS = "technical_draft_do_not_publish"
SHEET_PDF = "diagnostic_report_v0_2_technical.pdf"


def _read_json(path: Path) -> dict:
    v = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(v, dict):
        raise ValueError(f"Invalid JSON document: {path.name}")
    return v


def _checked_file(base: Path, relative: str) -> Path:
    path = base / relative
    if (path.is_symlink() or not path.is_file()
            or not path.resolve().is_relative_to(base.resolve())
            or path.stat().st_size == 0):
        raise ValueError(f"Required artifact absent, symlinked or empty: {relative}")
    return path


def _verify_hashes(base: Path, artifacts: dict, expected: set[str]) -> None:
    if not isinstance(artifacts, dict) or set(artifacts) != expected:
        raise ValueError("Artifact inventory differs from technical contract")
    for name in expected:
        if name.startswith("/") or ".." in Path(name).parts:
            raise ValueError("Unsafe artifact path")
        item = artifacts[name]
        path = _checked_file(base, name)
        if (item.get("sha256") != sha256_file(path)
                or item.get("bytes") != path.stat().st_size):
            raise ValueError("Artifact SHA-256 mismatch: " + name)


def inspect(bundle: Path, report: Path, sheets: Path, analysis: Path,
            dashboard: Path, registry: Path, release_config: Path) -> list[tuple[Path, str]]:
    """Validate all source files and return source/relative-package path pairs."""
    profiles, _ = verified_data(bundle, registry, release_config)
    pilot_sha = sha256_file(bundle / "release_manifest.json")
    with registry.open(encoding="utf-8-sig", newline="") as f:
        codes = {r["municipality"]: r["istat_code"] for r in csv.DictReader(f)}
    expected_rows, expected_summary = compare(profiles, codes)
    all_files: list[tuple[Path, str]] = []

    # Complete technical report (from PR #122).
    m = _read_json(report / "report_manifest_v0_2.json")
    expected_report = {SHEET_PDF, "diagnostic_facts_v0_2.json"}
    if (m.get("status") != SOURCE_STATUS or m.get("source_manifest_sha256") != pilot_sha
            or m.get("cit_included") is not False or m.get("no_composite_score") is not True
            or m.get("no_household_attribution") is not True
            or not 9 <= m.get("output_pdf_pages", 0) <= 12):
        raise ValueError("Technical PDF provenance or nonpublication gate invalid")
    _verify_hashes(report, m.get("artifacts"), expected_report)
    reader = PdfReader(str(_checked_file(report, SHEET_PDF)))
    text = "\n".join(p.extract_text() or "" for p in reader.pages)
    if len(reader.pages) != m["output_pdf_pages"] or "NON PUBBLICARE" not in text:
        raise ValueError("Technical PDF has wrong page count or missing draft warning")
    for name in sorted(expected_report | {"report_manifest_v0_2.json"}):
        all_files.append((_checked_file(report, name), "report/" + name))

    # All 27 one-page A4 municipal factsheets (PR #123).
    index = _read_json(sheets / "sheets_index_v0_2.json")
    items = index.get("sheets")
    if (index.get("status") != SOURCE_STATUS
            or index.get("no_composite_score") is not True
            or index.get("source_manifest_sha256") != pilot_sha
            or index.get("municipalities") != 27 or not isinstance(items, list)
            or len(items) != 27
            or {r.get("istat_code") for r in items} != set(codes.values())
            or {r.get("municipality") for r in items} != set(codes)):
        raise ValueError("Municipal sheet coverage/provenance invalid")
    seen = set()
    for item in items:
        code = item["istat_code"]
        if (item["path"] != f"municipalities/{code}.pdf"
                or codes[item["municipality"]] != code or code in seen):
            raise ValueError("Municipal sheet code mismatch or duplicate")
        seen.add(code)
        f = _checked_file(sheets, item["path"])
        if item.get("sha256") != sha256_file(f) or item.get("bytes") != f.stat().st_size:
            raise ValueError("Municipal PDF SHA mismatch")
        pdf = PdfReader(str(f))
        if len(pdf.pages) != 1 or "NON PUBBLICARE" not in (pdf.pages[0].extract_text() or ""):
            raise ValueError("Municipal sheet must be one clearly unapproved page")
        all_files.append((f, "sheets/" + item["path"]))
    all_files.append((_checked_file(sheets, "sheets_index_v0_2.json"),
                      "sheets/sheets_index_v0_2.json"))

    # Source-traceable analytic comparison (PR #124).
    ma = _read_json(analysis / "analysis_manifest_v0_2.json")
    analytic_files = {"municipality_comparison_v0_2.csv",
                      "pairwise_overlap_v0_2.csv", "analysis_summary_v0_2.json"}
    if (ma.get("status") != SOURCE_STATUS or ma.get("no_composite_score") is not True
            or ma.get("source_manifest_sha256") != pilot_sha
            or ma.get("source_profiles_sha256") != sha256_file(bundle / "municipality_profile.csv")):
        raise ValueError("Analysis does not derive from the same verified pilot")
    _verify_hashes(analysis, ma.get("artifacts"), analytic_files)
    summary = _read_json(analysis / "analysis_summary_v0_2.json")
    if summary != expected_summary:
        raise ValueError("Analysis summary differs from independently recomputed data")
    with (analysis / "municipality_comparison_v0_2.csv").open(
        encoding="utf-8", newline=""
    ) as f:
        rows = list(csv.DictReader(f))
    if rows != expected_rows:
        raise ValueError("Analysis CSV differs from independently recomputed data")
    with (analysis / "pairwise_overlap_v0_2.csv").open(
        encoding="utf-8", newline=""
    ) as f:
        pairs = list(csv.DictReader(f))
    if pairs != [{k: str(v) for k, v in p.items()}
                 for p in expected_summary["pairwise_cooccurrences"]]:
        raise ValueError("Pairwise co-occurrence CSV is inconsistent")
    for name in sorted(analytic_files | {"analysis_manifest_v0_2.json"}):
        all_files.append((_checked_file(analysis, name), "analysis/" + name))

    # Offline-only dashboard (PR #125).
    md = _read_json(dashboard / "dashboard_manifest_v0_2.json")
    dashboard_files = {"index.html", "dashboard_data_v0_2.json"}
    if (md.get("status") != SOURCE_STATUS
            or md.get("offline_only") is not True
            or md.get("no_composite_score") is not True
            or md.get("municipalities") != 27
            or md.get("source_manifest_sha256") != pilot_sha
            or md.get("analysis_manifest_sha256") != sha256_file(
                analysis / "analysis_manifest_v0_2.json")):
        raise ValueError("Dashboard not tied to this 27-town analysis")
    _verify_hashes(dashboard, md.get("artifacts"), dashboard_files)
    payload = _read_json(dashboard / "dashboard_data_v0_2.json")
    if (payload.get("status") != SOURCE_STATUS or payload.get("no_composite_score") is not True
            or len(payload.get("municipalities", [])) != 27
            or {row.get("code") for row in payload["municipalities"]} != set(codes.values())):
        raise ValueError("Dashboard coverage/status inconsistent")
    html = (dashboard / "index.html").read_text(encoding="utf-8")
    if ("NON PUBBLICARE" not in html or "fetch(" in html
            or "<script src=" in html or "https://" in html):
        raise ValueError("Dashboard not offline-only and clearly labelled")
    for name in sorted(dashboard_files | {"dashboard_manifest_v0_2.json"}):
        all_files.append((_checked_file(dashboard, name), "dashboard/" + name))

    if len({rel for _, rel in all_files}) != len(all_files):
        raise ValueError("Duplicate output paths in technical review package")
    return all_files


def _zip(folder: Path, target: Path) -> None:
    """Fixed ordering/time/Unix modes; archives only the selected review files."""
    with zipfile.ZipFile(target, "w") as archive:
        for path in sorted(p for p in folder.rglob("*") if p.is_file()
                           and p != target):
            relative = path.relative_to(folder).as_posix()
            item = zipfile.ZipInfo("review/" + relative, (1980, 1, 1, 0, 0, 0))
            item.create_system = 3
            item.external_attr = 0o100644 << 16
            item.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(item, path.read_bytes())
    with zipfile.ZipFile(target) as archive:
        if archive.testzip() is not None:
            raise ValueError("Review ZIP failed CRC verification")


def build(bundle: Path, report: Path, sheets: Path, analysis: Path,
          dashboard: Path, destination: Path, registry: Path,
          release_config: Path) -> Path:
    destination = destination.resolve()
    if destination.exists():
        raise FileExistsError("Previous technical review pack exists; choose a new out-dir")
    roots = [p.resolve() for p in (bundle, report, sheets, analysis, dashboard)]
    if any(destination == root or destination.is_relative_to(root)
           for root in roots):
        raise ValueError("Review output must not be inside any input")
    files = inspect(bundle, report, sheets, analysis, dashboard, registry, release_config)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".epah-v02-review-", dir=destination.parent) as td:
        stage = Path(td) / "candidate"
        stage.mkdir()
        for source, relative in files:
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        checklist = {
            "schema_version": "1.0",
            "publication_authorized": False,
            "required_human_checks": {
                name: {"status": "pending", "reviewer": None, "evidence": None}
                for name in (
                    "source_provenance_and_licenses",
                    "scientific_methods_and_cross_year_comparability",
                    "municipal_pdf_visual_inspection",
                    "technical_report_visual_inspection",
                    "institutional_validation_and_signoff",
                    "EPAH_branding_and_communications_review",
                    "final_release_authorization",
                )
            },
        }
        (stage / "editorial_review_checklist.json").write_text(
            json.dumps(checklist, indent=2) + "\n", encoding="utf-8"
        )
        summary = {
            "status": STATUS,
            "publication_authorized": False,
            "source_bundle_manifest_sha256": sha256_file(bundle / "release_manifest.json"),
            "municipalities": 27, "core_indicators": 9,
            "cit_included": False, "household_attribution": False,
            "source_qa": "verified_hashed_pilot_artifacts_only",
            "technical_artifacts_verified": len(files),
            "human_signoff": "pending",
            "pdf_visual_review": "pending",
            "editorial_and_brand_checks": "pending",
        }
        (stage / "qa_summary_v0_2.json").write_text(
            json.dumps(summary, indent=2) + "\n", encoding="utf-8"
        )
        (stage / "README_REVIEW.md").write_text(
            "# EPAH v0.2 - Dossier tecnico per revisione interna\n\n"
            "**NON PUBBLICARE / NON DISTRIBUIRE COME RELEASE ISTITUZIONALE.**\n\n"
            "Pacchetto derivato dal bundle pilota v0.1 verificato: "
            "27 schede comunali, rapporto tecnico PDF, tabelle descrittive "
            "e dashboard HTML offline. Dati CIT in quarantena esclusi.\n\n"
            "Il passaggio delle verifiche automatiche non sostituisce "
            "la revisione scientifica, la verifica visuale dei PDF, "
            "la review delle licenze e l'autorizzazione istituzionale.\n\n"
            "Consultare editorial_review_checklist.json, interamente "
            "in stato pending. Aprire dashboard/index.html localmente.\n",
            encoding="utf-8",
        )
        names = [p.relative_to(stage).as_posix()
                 for p in sorted(stage.rglob("*")) if p.is_file()]
        pack_manifest = {
            "status": STATUS, "publication_authorized": False,
            "input_pilot_sha256": summary["source_bundle_manifest_sha256"],
            "artifacts": {name: sha256_file(stage / name) for name in names},
        }
        (stage / "review_package_manifest_v0_2.json").write_text(
            json.dumps(pack_manifest, indent=2) + "\n", encoding="utf-8"
        )
        _zip(stage, stage / "v0_2_technical_review_only.zip")
        if destination.exists():
            raise FileExistsError("Concurrent output appeared; no overwrite allowed")
        os.replace(stage, destination)
    return destination
