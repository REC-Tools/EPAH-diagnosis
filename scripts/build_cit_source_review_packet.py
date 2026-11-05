"""Human-review dossier for CIT Pont Canavese, from a verified QA-only pipeline run.

No automatic source-row selection, summation, publication or approval.
"""
from __future__ import annotations

import argparse
import csv
import json
import tempfile
from pathlib import Path

from build_v0_2_cit_quarantine_comparison import (
    EXPECTED_SOURCE_HASHES, load_quarantine, registry_codes, sha256,
)

ROOT = Path(__file__).resolve().parents[1]
QA_ROOT = ROOT / "outputs/quality"
EXPECTED_STEPS = ("prepare_fuel", "prepare_age", "qa_compare")


def read_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def verify_conflict(record: dict, mode: str) -> None:
    rows = record.get("source_records", [])
    if (record.get("istat_code") != "001199"
            or record.get("status") != "conflicting_counts"
            or not record.get("differing_count_fields") or len(rows) < 2):
        raise ValueError(f"{mode}: unresolved conflict evidence incomplete")
    vectors = []
    lines = []
    for row in rows:
        counts = row.get("counts")
        if (type(row.get("line")) is not int or row["line"] < 2
                or not isinstance(counts, dict) or not counts
                or any(type(v) is not int or v < 0 for v in counts.values())
                or row.get("row_total") != sum(counts.values())):
            raise ValueError(f"{mode}: source line counts inconsistent")
        vectors.append(counts)
        lines.append(row["line"])
    if len(set(lines)) != len(lines) or all(v == vectors[0] for v in vectors[1:]):
        raise ValueError(f"{mode}: no distinct conflicting source rows")


def verify_comparison(path: Path, fuel: dict, age: dict, snapshot: str) -> None:
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if (len(rows) != 26 or {r.get("istat_code") for r in rows} != set(fuel)
            or set(fuel) != set(age)):
        raise ValueError("CIT comparison has inconsistent 26-town coverage")
    for row in rows:
        code = row["istat_code"]
        f, a = fuel[code], age[code]
        checks = {
            "fuel_gasolio_gpl_n": str(f["numerator"]),
            "fuel_classified_groups_n": str(f["denominator"]),
            "fuel_gasolio_gpl_share_pct": f"{f['share_pct']:.2f}",
            "age_certain_20plus_n": str(a["numerator"]),
            "age_dated_groups_n": str(a["denominator"]),
            "age_ambiguous_bin_n": str(a["ambiguous_groups"]),
            "age_minimum_20plus_pct": f"{a['share_pct']:.2f}",
            "age_maximum_20plus_pct": f"{a['upper_bound_pct']:.2f}",
            "observation_status": "technical_QA_only",
            "analysis_reference_date": snapshot,
        }
        if any(row.get(name) != value for name, value in checks.items()):
            raise ValueError(f"{code}: comparison CSV differs from checked source QA")


def inspect_run(run_dir: Path, registry_file: Path) -> dict:
    run = read_object(run_dir / "pipeline_run_report.json")
    if (run.get("profile") != "cit-quarantine"
            or run.get("run_status") != "technical_incomplete_do_not_publish"
            or run.get("publication_allowed") is not False
            or run.get("automatic_promotions") != 0
            or run.get("scientific_approval") != "not_assessed"
            or [(step.get("name"), step.get("return_code"))
                for step in run.get("steps", [])] != [(n, 0) for n in EXPECTED_STEPS]):
        raise ValueError("Not a completed CIT quarantine technical pipeline")
    inputs = {x.get("name"): x.get("sha256") for x in run.get("source_inputs", [])
              if isinstance(x, dict)}
    if any(inputs.get(mode) != EXPECTED_SOURCE_HASHES[mode]
           for mode in ("fuel", "age")):
        raise ValueError("Recorded original-source SHA-256 differs from CIT evidence")

    registry = registry_codes(registry_file)
    h = sha256(registry_file)
    fuel, fuel_qa, fuel_review = load_quarantine(
        run_dir / "cit_fuel", "fuel", registry, h)
    age, age_qa, age_review = load_quarantine(
        run_dir / "cit_age", "age", registry, h)
    fuel_conflict = fuel_review["conflicts"][0]
    age_conflict = age_review["conflicts"][0]
    verify_conflict(fuel_conflict, "fuel")
    verify_conflict(age_conflict, "age")
    review_dir = run_dir / "cit_review"
    summary_file = review_dir / "cit_26_qa_summary.json"
    conflict_file = review_dir / "cit_pont_canavese_source_review.json"
    csv_file = review_dir / "cit_26_municipality_technical_comparison.csv"
    summary = read_object(summary_file)
    conflict = read_object(conflict_file)
    snapshot = fuel_qa.get("snapshot_date_operator_reported")
    if (snapshot != age_qa.get("snapshot_date_operator_reported")
            or summary.get("reference_date_not_original_snapshot") != snapshot
            or summary.get("status") != "technical_QA_only_incomplete_do_not_publish"
            or summary.get("valid_municipalities") != 26
            or summary.get("municipalities_expected") != 27
            or summary.get("excluded") != [{
                "istat_code": "001199", "municipality": registry["001199"],
                "reason": "conflicting_official_source_rows"}]
            or summary.get("source_checksums") != EXPECTED_SOURCE_HASHES
            or summary.get("output_csv_sha256") != sha256(csv_file)
            or summary.get("age_uncertainty_groups") !=
                sum(x["ambiguous_groups"] for x in age.values())
            or conflict.get("status") != "human_source_review_required"
            or conflict.get("source_data_modified") is not False
            or conflict.get("excluded_istat_code") != "001199"
            or conflict.get("fuel") != fuel_review
            or conflict.get("age") != age_review):
        raise ValueError("Cross-source QA evidence and summaries disagree")
    verify_comparison(csv_file, fuel, age, snapshot)
    return {
        "status": "human_source_review_required_do_not_publish",
        "human_review": "pending_official_source_clarification",
        "approved_for_release": False,
        "publication_allowed": False,
        "decision": None,
        "municipality": registry["001199"], "istat_code": "001199",
        "analysis_date_not_official_snapshot": snapshot,
        "original_source_sha256": EXPECTED_SOURCE_HASHES,
        "evidence_sha256": {
            "fuel_csv": sha256(run_dir / "cit_fuel/cit_fuel_27.csv"),
            "age_csv": sha256(run_dir / "cit_age/cit_generator_age_27.csv"),
            "comparison_csv": sha256(csv_file),
            "summary_json": sha256(summary_file),
            "source_review_json": sha256(conflict_file),
        },
        "conflicts": {"fuel": fuel_conflict, "age": age_conflict},
        "valid_municipalities": 26,
        "ambiguous_age_groups_26_towns": summary["age_uncertainty_groups"],
    }


def cell(value: object) -> str:
    return str(value).replace("\r", " ").replace("\n", " ").replace("|", "\\|")


def draft_request(evidence: dict) -> str:
    lines = [
        "# Richiesta di chiarimento CIT - bozza interna da revisionare",
        "",
        "Destinatario: responsabili del CIT presso Regione Piemonte / CSI Piemonte",
        "(verificare il recapito aggiornato nel catalogo prima dell'invio).",
        "",
        "Oggetto: righe comunali discordanti CIT, Pont Canavese, ISTAT 001199",
        "",
        "Buongiorno,",
        "",
        "nell'ambito della diagnosi territoriale EPAH per Sinergie in Canavese,",
        "abbiamo riscontrato conteggi differenti per Pont Canavese in due CSV",
        "aggregati del Catasto Impianti Termici. Non abbiamo selezionato,",
        "sommato o azzerato le righe; Pont resta escluso dai calcoli provvisori.",
        "",
        "| Dataset | Riga originale | Chiave | Nome | Somma gruppi |",
        "| --- | ---: | --- | --- | ---: |",
    ]
    for mode, label in (("fuel", "Combustibili"), ("age", "Età generatori")):
        record = evidence["conflicts"][mode]
        for row in record["source_records"]:
            lines.append("| " + " | ".join(
                cell(x) for x in (
                    label, row["line"], row.get("observed_key", ""),
                    row.get("observed_name", ""), row["row_total"]
                )) + " |")
    lines += [
        "",
        "Chiediamo di precisare:",
        "1. Se le righe rappresentino periodi, sottoinsiemi o stati diversi;",
        "2. Quali campi/filtro ufficiali permettano un aggregato comunale univoco;",
        "3. La data effettiva e la definizione dello snapshot di ciascun file;",
        "4. Se sia disponibile uno schema o un estratto corretto documentato.",
        "",
        "SHA-256 originali (per identificare senza ambiguità gli estratti):",
        "- Combustibili: " + evidence["original_source_sha256"]["fuel"],
        "- Età generatori: " + evidence["original_source_sha256"]["age"],
        "",
        "Restiamo in attesa di un chiarimento scritto. Grazie per il supporto.",
        "",
        "Cordiali saluti,",
        "[Referente e organizzazione, da completare]",
        "",
        "---",
        "BOZZA NON INVIATA, SOLO REVISIONE UMANA.",
        "Data " + evidence["analysis_date_not_official_snapshot"]
        + " = riferimento analitico locale, non aggiornamento ufficiale.",
        "I " + str(evidence["ambiguous_age_groups_26_towns"])
        + " gruppi nella classe di età incerta per i 26 Comuni non controversi",
        "sono un limite diverso dal conflitto di Pont.",
        "I gruppi generatori non sono famiglie o abitazioni.",
    ]
    return "\n".join(lines) + "\n"


def review_checklist() -> str:
    return (
        "# Checklist decisione umana - nessuna approvazione automatica\n\n"
        "- [ ] Verificare recapito e licenza delle fonti originali.\n"
        "- [ ] Verificare e inviare la richiesta; registrare data e protocollo.\n"
        "- [ ] Conservare risposta ufficiale e fonte/documento verificabile.\n"
        "- [ ] Documentare criterio ufficiale su duplicati e periodo di riferimento.\n"
        "- [ ] Rieseguire QA su 27 Comuni e verificare denominatori e soglia di età.\n"
        "- [ ] Ottenere review metodologica e approvazione pubblicazione separate.\n"
    )


def build_packet(run_dir: Path, out_dir: Path, registry_file: Path,
                 qa_root: Path = QA_ROOT) -> Path:
    output = out_dir.resolve()
    base = qa_root.resolve()
    if output == base or not output.is_relative_to(base):
        raise ValueError("Packet must be a NEW directory under outputs/quality/")
    if output.exists():
        raise FileExistsError("Review packet exists; choose a fresh --out-dir")
    evidence = inspect_run(run_dir.resolve(), registry_file)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".cit-review-packet-", dir=output.parent) as td:
        stage = Path(td) / "packet"
        stage.mkdir()
        (stage / "cit_pont_evidence.json").write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (stage / "request_to_region_draft.md").write_text(
            draft_request(evidence), encoding="utf-8")
        (stage / "human_review_checklist.md").write_text(
            review_checklist(), encoding="utf-8")
        if output.exists():
            raise FileExistsError("Review packet exists; refusing overwrite")
        stage.rename(output)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate internal Pont Canavese CIT review packet")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=ROOT / "data/municipalities.csv")
    args = parser.parse_args()
    try:
        result = build_packet(args.run_dir, args.out_dir, args.registry)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print("BLOCKED:", exc)
        return 1
    print("Review packet:", result)
    print("PENDING HUMAN SOURCE CLARIFICATION. NO PUBLICATION OR PROMOTION.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
