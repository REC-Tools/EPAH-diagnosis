"""Create unsigned review packets from three QA-verified accessibility drafts.

Never mark a human check complete or modify the canonical matrix/catalog.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHA = re.compile(r"[0-9a-f]{64}")
SPECS = {
    "dea_accessibility": {
        "prefix": "dea", "qa": "dea_accessibility_qa.json",
        "outputs": {"data_csv_sha256": "dea_accessibility_minutes.csv",
                    "summary_csv_sha256": "dea_accessibility_summary.csv"},
        "sources": {"hospitals_csv_sha256": "hospitals"},
        "flags": ["source_authenticity_reviewed", "national_2025_dea_network_reviewed",
                  "cross_region_eligibility_reviewed", "historical_code_crosswalk_reviewed",
                  "license_reviewed", "independent_route_sample_reviewed"],
        "scope": "piemonte_dea_proxy_approved_with_limits",
    },
    "rail_accessibility": {
        "prefix": "rail", "qa": "rail_accessibility_qa.json",
        "outputs": {"data_csv_sha256": "rail_accessibility_minutes.csv",
                    "summary_csv_sha256": "rail_accessibility_summary.csv",
                    "destination_csv_sha256": "active_rail_gateways_review_snapshot.csv"},
        "sources": {"rail_snapshot_sha256": "rail_gateways"},
        "flags": ["road_2021_to_registry_2026_crosswalk_reviewed",
                  "source_authenticity_reviewed", "service_eligibility_reviewed",
                  "out_of_region_service_coverage_reviewed", "license_reviewed",
                  "independent_route_sample_reviewed"],
        "scope": "piemonte_curated_proxy_approved_with_limits",
    },
    "upper_secondary_accessibility": {
        "prefix": "school", "qa": "upper_secondary_accessibility_qa.json",
        "outputs": {"data_csv_sha256": "upper_secondary_accessibility_minutes.csv",
                    "summary_csv_sha256": "upper_secondary_accessibility_summary.csv",
                    "destination_csv_sha256": "upper_secondary_poles_2024_25.csv"},
        "sources": {"school_registry_sha256": "school_registry",
                    "school_pathways_sha256": "school_pathways"},
        "flags": ["road_2021_to_registry_2026_crosswalk_reviewed",
                  "source_authenticity_reviewed", "service_eligibility_reviewed",
                  "out_of_region_service_coverage_reviewed", "license_reviewed",
                  "independent_route_sample_reviewed"],
        "scope": "piemonte_curated_proxy_approved_with_limits",
    },
}
COMMON_HASHES = {
    "road_zip_sha256": "road_zip",
    "boundaries_zip_sha256": "boundaries_zip",
    "registry_csv_sha256": "registry",
}
CHECKS = {
    "dea_accessibility": [
        "Ministero Salute 2025: 30 DEA I/II, non PS, e 23 Comuni piemontesi.",
        "Possibili DEA piu vicini fuori Piemonte: Aosta, Lombardia e altre regioni.",
        "Confronto vecchia/nuova bozza (27/27 invariati) non dimostra completezza nazionale.",
    ],
    "rail_accessibility": [
        "Servizio ferroviario effettivamente attivo per tutti i 9 gateway RFI/SFM.",
        "Bus sostitutivo Rivarolo-Pont Canavese ed eventuali stazioni omesse.",
        "Motivazione del perimetro curato, distinto dalla classificazione SNAI.",
    ],
    "upper_secondary_accessibility": [
        "51 poli: liceo classico/scientifico E tecnico/professionale.",
        "Dati dei percorsi 2024/25 distinti da eventuale offerta attuale 2026/27.",
        "Coincidenza scuola-ferrovia per 27/27 Comuni e possibili poli fuori Piemonte.",
    ],
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_hash(value: object, path: Path, label: str) -> None:
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise ValueError(f"{label}: missing valid SHA-256 in QA")
    if not path.is_file() or sha256(path) != value:
        raise ValueError(f"{label}: source/output SHA mismatch: {path}")


def read_and_check(indicator: str, draft: Path, sources: dict[str, Path]) -> dict:
    spec = SPECS[indicator]
    qa = json.loads((draft / spec["qa"]).read_text(encoding="utf-8"))
    count = qa.get("eligible_dea_municipality_count") if indicator == "dea_accessibility" else qa.get("destination_municipality_count")
    routes = qa.get("route_pair_count", qa.get("complete_route_pairs"))
    if (qa.get("indicator_id") != indicator or qa.get("origin_count") != 27
        or qa.get("qa_status") != "technical_checks_only" or
        qa.get("validated_for_release") is not False or
        not isinstance(count, int) or count < 1 or
        routes != qa.get("expected_route_pairs") or routes != count * 27):
        raise ValueError(f"{indicator}: bad QA metadata or incomplete grid")
    for field, filename in spec["outputs"].items():
        check_hash(qa.get(field), draft / filename, f"{indicator}/{field}")
    for field, src in {**COMMON_HASHES, **spec["sources"]}.items():
        check_hash(qa.get(field), sources[src], f"{indicator}/{field}")
    with (draft / spec["outputs"]["data_csv_sha256"]).open(encoding="utf-8-sig", newline="") as handle:
        data = list(csv.DictReader(handle))
    with sources["registry"].open(encoding="utf-8-sig", newline="") as handle:
        registry = list(csv.DictReader(handle))
    canonical = {row["istat_code"] for row in registry}
    codes = {row["municipality_code"] for row in data}
    if (len(registry) != 27 or len(canonical) != 27 or
        len(data) != 27 or len(codes) != 27 or codes != canonical):
        raise ValueError(f"{indicator}: municipality coverage differs from 27 canonical codes")
    return qa


def pending_approval(indicator: str, qa: dict) -> dict:
    spec = SPECS[indicator]
    hashes = list(COMMON_HASHES) + list(spec["sources"]) + list(spec["outputs"])
    result = {
        "indicator_id": indicator,
        "road_graph_year": "2020",
        **({"reference_year": "2021"} if indicator == "dea_accessibility" else {
            "road_geography_year": "2021", "service_vintage": qa["service_vintage"]}),
        **{key: qa[key] for key in hashes},
        "decision": "pending",
        "reviewed_by": "",
        "reviewed_on": "",
        "review_evidence_url": "",
        "review_notes": "",
        "methodology_scope_decision": "pending",
    }
    result.update({key: False for key in spec["flags"]})
    return result


def pending_methodologies(catalog: dict, release: dict) -> dict:
    by_id = {x["id"]: x for x in catalog["indicators"]}
    ids = release["core_indicators"]
    if len(ids) != 9 or len(set(ids)) != 9 or set(ids) - set(by_id):
        raise ValueError("Release must specify exactly nine known core indicators")
    return {
        "schema_version": "1.0",
        "description": "UNSIGNED. Do not use as config/release_reviews_v0_1.json.",
        "methodology_approvals": [
            {"indicator_id": identifier, "decision": "pending",
             "reviewed_by": "", "reviewed_on": "", "evidence_url": ""}
            for identifier in ids
        ],
    }


def checklist(indicator: str, qa: dict) -> str:
    lines = [
        "# Human review: " + indicator,
        "",
        "PENDING: no verification or signature has been granted.",
        "",
        "QA identifier: " + indicator,
        "QA data SHA-256: " + qa["data_csv_sha256"],
        "Origins: 27; routes: " + str(qa.get("route_pair_count", qa.get("complete_route_pairs"))),
        "",
        "## Controls to perform and document",
        "",
    ]
    for task in CHECKS[indicator] + [
        "Confirm official originals, source vintage, licensing and attribution.",
        "Review 2021 road codes against 2026 municipality code registry.",
        "Independently verify 3 origin/destination pairs in raw ISTAT CSV (TEP_TOT and KM_TOT).",
        "Confirm eligibility and geographic completeness of all destination candidates.",
        "Accept and document centre-of-municipality proxy limitations.",
        "Identify actual reviewer, date, detailed notes, durable evidence URL, and independent GitHub reviewer.",
    ]:
        lines.append("- [ ] " + task)
    lines.extend([
        "",
        "## Three ISTAT route samples to fill",
        "",
        "| Origin code | Destination code | Minutes | Km | Evidence |",
        "| --- | --- | ---: | ---: | --- |",
        "| PENDING | PENDING | - | - | PENDING |",
        "| PENDING | PENDING | - | - | PENDING |",
        "| PENDING | PENDING | - | - | PENDING |",
        "",
        "## Human decision",
        "",
        "Decision: PENDING",
        "Reviewer and signature: PENDING",
        "Date and evidence URL: PENDING",
        "Methodology scope: PENDING; permitted after review: " + SPECS[indicator]["scope"],
        "",
    ])
    return "\n".join(lines)


def methodology_checklist(catalog: dict, release: dict) -> str:
    by_id = {x["id"]: x for x in catalog["indicators"]}
    lines = [
        "# Nine methodology reviews - UNSIGNED",
        "",
        "The six previously populated indicators also need independent methodology approval.",
        "No EXPERIMENTAL maturity is changed by packet generation.",
        "",
    ]
    for number, identifier in enumerate(release["core_indicators"], 1):
        item = by_id[identifier]
        lines.extend([
            f"## {number}. {item['name']} ({identifier})",
            "",
            "Definition: " + item["definition"],
            "Unit: " + item["unit"],
            "Documentation: " + item["documentation"],
            "Current maturity: " + item["methodological_maturity"],
            "Caveat: " + item["caveat"],
            "- [ ] Official source and vintage checked; 27/27 origin data verified.",
            "- [ ] Definition, sample calculations, source licences and caveats checked.",
            "- [ ] Scientific decision on OPERATIONAL vs VALIDATED maturity explained.",
            "- [ ] Independent real reviewer signed a durable evidence record.",
            "Decision: PENDING; reviewer/evidence URL: PENDING",
            "",
        ])
    return "\n".join(lines)


def build_packets(drafts: dict[str, Path], sources: dict[str, Path],
                  catalog_path: Path, release_path: Path, out_dir: Path) -> dict[str, str]:
    if out_dir.exists():
        raise FileExistsError("Review packet output already exists; choose a new --out-dir")
    qa = {indicator: read_and_check(indicator, drafts[indicator], sources)
          for indicator in SPECS}
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    release = json.loads(release_path.read_text(encoding="utf-8"))
    methods = pending_methodologies(catalog, release)
    files = {}
    for identifier, report in qa.items():
        prefix = SPECS[identifier]["prefix"]
        files[f"{prefix}_approval.pending.json"] = json.dumps(
            pending_approval(identifier, report), indent=2, ensure_ascii=False) + "\n"
        files[f"{prefix}_review_checklist.md"] = checklist(identifier, report)
    files["methodology_reviews.pending.json"] = json.dumps(
        methods, indent=2, ensure_ascii=False) + "\n"
    files["nine_methodology_checklists.md"] = methodology_checklist(catalog, release)
    return files


def main() -> None:
    p = argparse.ArgumentParser(description="Prepare exactly 8 unsigned v0.1 review files; no approvals")
    p.add_argument("--dea-draft", type=Path, default=ROOT / "outputs/quality/dea_accessibility_2025_v03")
    p.add_argument("--rail-draft", type=Path, default=ROOT / "outputs/quality/rail_accessibility_v01")
    p.add_argument("--school-draft", type=Path, default=ROOT / "outputs/quality/upper_secondary_accessibility_v01")
    p.add_argument("--road-zip", type=Path, default=ROOT / "data/downloads/Piemonte.zip")
    p.add_argument("--boundaries-zip", type=Path, default=ROOT / "data/downloads/Limiti01012026_g.zip")
    p.add_argument("--registry", type=Path, default=ROOT / "data/municipalities.csv")
    p.add_argument("--hospitals", type=Path, default=ROOT / "data/reference/piemonte_dea_hospitals.csv")
    p.add_argument("--rail-gateways", type=Path, default=ROOT / "data/reference/canavese_active_rail_gateways.csv")
    p.add_argument("--school-registry", type=Path, default=ROOT / "outputs/quality/access_inputs_mim_202425/raw/SCUANAGRAFESTAT20242520250831.csv")
    p.add_argument("--school-pathways", type=Path, default=ROOT / "outputs/quality/access_inputs_mim_202425/raw/ALUSECGRADOINDSTA20242520250831.csv")
    p.add_argument("--catalog", type=Path, default=ROOT / "config/indicators.json")
    p.add_argument("--release", type=Path, default=ROOT / "config/release_v0_1.json")
    p.add_argument("--out-dir", type=Path, default=ROOT / "outputs/quality/human_review_packets_v01")
    a = p.parse_args()
    drafts = {"dea_accessibility": a.dea_draft, "rail_accessibility": a.rail_draft,
              "upper_secondary_accessibility": a.school_draft}
    sources = {"road_zip": a.road_zip, "boundaries_zip": a.boundaries_zip,
               "registry": a.registry, "hospitals": a.hospitals,
               "rail_gateways": a.rail_gateways, "school_registry": a.school_registry,
               "school_pathways": a.school_pathways}
    files = build_packets(drafts, sources, a.catalog, a.release, a.out_dir)
    a.out_dir.mkdir(parents=True)
    for filename, contents in files.items():
        with (a.out_dir / filename).open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(contents)
    print(f"Created {len(files)} unsigned review files in {a.out_dir}")
    for filename in files:
        print("  " + filename)
    print("All decisions PENDING, all flags false; canonical matrix/catalog unchanged.")


if __name__ == "__main__":
    main()
