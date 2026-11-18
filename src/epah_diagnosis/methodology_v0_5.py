"""Validate proposal metadata, never calculate indicators or approve methodology."""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import tempfile

from .directory_publication import publish_directory

TEXT_FIELDS = ("id", "name", "change_type", "role", "unit", "statistical_unit", "universe",
               "numerator", "denominator", "reference_period", "geography", "source_ref",
               "source_locator", "dataset_code", "definition", "review_status", "local_use", "data_state")
LIST_FIELDS = ("local_requirements", "limitations", "related_inventory", "unresolved_decisions")

# Questions to document, not prescribed survey definitions or approved choices.
LOCAL_DECISIONS = {
    "diagnostic_question": "A quale domanda locale deve rispondere la raccolta?",
    "reviewer": "Chi revisiona il protocollo e con quale evidenza?",
    "statistical_unit": "Persone, famiglie o altra unità? Distinguere stakeholder e popolazione osservata.",
    "universe_and_eligibility": "Quale universo e quali criteri di eleggibilità?",
    "geography_and_registry": "Quale copertura, versione del registro e raccordo ISTAT?",
    "source_access_and_coverage": "Quale archivio già disponibile, prodotto/versione, accesso autorizzato e copertura effettiva?",
    "reference_and_recall_period": "Quali periodi del fenomeno, richiamo, reddito e raccolta?",
    "observation_or_extraction_specification": "Quale variabile/prodotto o domanda esatta, con versione e riferimento?",
    "spatial_temporal_processing": "Quali coordinate, griglia, maschera, calendario, soglie e aggregazioni? Motivare le non applicabilità.",
    "response_and_missingness_codes": "Quali risposte, non risposta, non applicabilità e soppressione?",
    "sampling_and_recruitment": "Quale campione, canale, copertura e limite di rappresentatività?",
    "counts_and_denominators": "Come distinguere eleggibili, contattati, rispondenti e risposte valide?",
    "calculation_unit_and_weights": "Quali eventuali calcoli, unità, pesi e denominatori richiedono decisione?",
    "provenance_and_replay": "Quali originali, versioni, licenze, hash e trasformazioni conserverà il responsabile?",
    "privacy_and_disclosure": "Quali aggregati sono autorizzati e come trattare piccoli numeri e accessi?",
    "stakeholder_validation": "Come registrare evidenze qualitative senza trasformarle in prevalenze comunali?",
    "comparability_and_limits": "Quali differenze dal benchmark, limiti e decisioni ancora aperte?",
}


def prepare_protocol(catalog: Path, indicator_id: str, out_dir: Path) -> Path:
    """Prepare an unfilled review dossier, preserving the national source contract."""
    raw = catalog.read_bytes()
    document = json.loads(raw.decode("utf-8"))
    check_catalog(document)
    selected = next((item for item in document["indicators"] if item["id"] == indicator_id), None)
    if selected is None:
        raise ValueError("Unknown proposal ID; select an existing V05 identifier")
    if out_dir.exists() or out_dir.is_symlink():
        raise FileExistsError("Choose a fresh protocol destination; no overwrite")
    record = {
        "schema_version": "0.5-local-protocol-draft-1",
        "status": "technical_draft_do_not_publish",
        "result": "protocol_template_prepared_not_ready_for_collection",
        "scientific_approval": False, "publication_allowed": False,
        "collection_authorized": False, "source_ingestion_performed": False,
        "municipal_series_added": 0,
        "proposal_id": indicator_id,
        "catalog_sha256": hashlib.sha256(raw).hexdigest(),
        "benchmark_contract": selected,
        "benchmark_source": document["sources"][selected["source_ref"]],
        "local_decisions": {key: {"question": question, "proposed_answer": None,
                                  "evidence_reference": None}
                            for key, question in LOCAL_DECISIONS.items()},
    }
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".epah-protocol-", dir=out_dir.parent) as temporary:
        stage = Path(temporary) / "protocol"
        stage.mkdir()
        (stage / "protocol.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        (stage / "README_REVIEW.md").write_text(
            "# Protocollo locale v0.5 da revisionare\n\n"
            "Stato: technical_draft_do_not_publish. Raccolta non autorizzata.\n\n"
            "1. Conservare questa cartella come baseline e lavorare su una copia esterna alla repo.\n"
            "2. In protocol.json leggere benchmark_contract e benchmark_source: sono la proposta\n"
            "   originaria, non una definizione o una stima comunale. Non modificarli.\n"
            "3. In local_decisions compilare proposed_answer ed evidence_reference per ogni voce,\n"
            "   dichiarando anche le non applicabilità con motivazione. Non inserire dati personali.\n"
            "4. Il revisore esamina le proposte e registra una decisione separata, riferita alla\n"
            "   copia esatta. Compilare il file non autorizza raccolta, calcolo o pubblicazione.\n"
            "5. Prima di acquisire o estrarre dati, concordare protocollo, campione se pertinente, accessi e aggregati\n"
            "   consentiti. Servono implementazione e controlli separati per nuove osservazioni.\n\n"
            "Le interviste stakeholder validano rilevanza e interpretazione; senza un disegno\n"
            "rappresentativo non stimano prevalenze dei residenti. Nessuna formula eseguita.\n"
            "Il comando methodology check verifica solo il catalogo delle proposte, non questa\n"
            "compilazione né l'approvazione scientifica. Nessun file è un piano eseguibile.\n",
            encoding="utf-8", newline="\n")
        publish_directory(stage, out_dir)
    return out_dir


def check_catalog(document: dict) -> dict:
    if (not isinstance(document, dict) or document.get("schema_version") != "0.5-methodology-proposals-1"
            or document.get("id_namespace") != "project_local_not_official_epah"
            or document.get("scientific_approval") is not False
            or document.get("publication_allowed") is not False):
        raise ValueError("Expected an explicitly unapproved v0.5 proposal catalogue")
    sources = document.get("sources")
    if not isinstance(sources, dict) or not sources:
        raise ValueError("Source registry is required")
    for source in sources.values():
        if (not isinstance(source, dict) or not source.get("url", "").startswith("https://")
                or not isinstance(source.get("title"), str) or not source["title"].strip()):
            raise ValueError("Every source requires a title and HTTPS URL")
        date.fromisoformat(source["checked_on"])
    indicators = document.get("indicators")
    if not isinstance(indicators, list) or not indicators:
        raise ValueError("Indicator proposals are required")
    identifiers = set()
    for item in indicators:
        if not isinstance(item, dict) or set(item) != set(TEXT_FIELDS + LIST_FIELDS):
            raise ValueError("Indicator contract fields are missing or unknown")
        if any(not isinstance(item[key], str) or not item[key].strip() for key in TEXT_FIELDS):
            raise ValueError("Units, period, universe, numerator, denominator and provenance must be explicit")
        if not re.fullmatch(r"V05-\d{2}", item["id"]) or item["id"] in identifiers:
            raise ValueError("Proposal IDs must be unique project-local V05 identifiers")
        identifiers.add(item["id"])
        if (item["review_status"] != "not_approved" or item["data_state"] != "source_identified_not_acquired"
                or item["local_use"] != "benchmark_only_until_local_protocol"
                or item["geography"] not in {"country", "grid_country_aggregate"}):
            raise ValueError("National proposals cannot be promoted to approved municipal observations")
        if item["source_ref"] not in sources:
            raise ValueError("Unknown source reference")
        if (item["unit"] not in {"percent", "days_per_year", "z_score"}
                or item["role"] not in {"health_context", "climate_exposure", "housing_context",
                    "socioeconomic_context", "mobility_context", "self_reported_affordability",
                    "expenditure_distribution"}):
            raise ValueError("Unknown unit or role; keep context, exposure and outcomes distinct")
        if item["change_type"] not in {"new_epah_2026", "updated_epah_2026", "existing_epah_priority"}:
            raise ValueError("Unknown change type")
        for key in LIST_FIELDS:
            if not isinstance(item[key], list) or any(not isinstance(v, str) or not v.strip() for v in item[key]):
                raise ValueError(f"{key} must contain explicit text items")
        if not item["local_requirements"] or not item["limitations"]:
            raise ValueError("Local evidence requirements and limitations are mandatory")
    return {"status": "proposal_metadata_checked_not_scientific_approval", "proposals": len(indicators),
            "scientific_approval": False, "publication_allowed": False,
            "municipal_series_added": 0, "ids": sorted(identifiers)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "prepare"))
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--indicator", help="Existing V05 proposal ID (prepare only)")
    parser.add_argument("--out-dir", type=Path, help="Fresh review dossier destination (prepare only)")
    args = parser.parse_args(argv)
    if args.action == "prepare" and (not args.indicator or args.out_dir is None):
        parser.error("prepare requires --indicator and --out-dir")
    if args.action == "check" and (args.indicator is not None or args.out_dir is not None):
        parser.error("--indicator and --out-dir are only supported by prepare")
    try:
        if args.action == "prepare":
            output = prepare_protocol(args.catalog, args.indicator, args.out_dir)
            print(f"PROTOCOLLO DA REVISIONARE - RACCOLTA NON AUTORIZZATA: {output}")
            return 0
        raw = args.catalog.read_bytes()
        result = check_catalog(json.loads(raw.decode("utf-8")))
        result["catalog_sha256"] = hashlib.sha256(raw).hexdigest()
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f"BLOCKED: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
