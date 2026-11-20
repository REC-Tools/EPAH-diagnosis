"""Import one mapped ERP response locally; preserve raw counts and review gaps."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import tempfile

from .cli import read_municipality_codes
from .csv_cells import spreadsheet_safe_cell
from .directory_publication import publish_directory
from .erp_request_v0_5 import COUNT_FIELDS, STATUSES, build_packet
from .provenance import sha256_file

CONTEXT = ("actual_reference_date", "owner_manager_scope", "coverage_note", "source_reference")
ROOT_FIELDS = {"schema_version", "status", "target_analysis_year", "requested_reference_date", "request_sent",
               "scientific_approval", "publication_allowed", "response_status_vocabulary", "municipalities"}
ROW_FIELDS = {"municipality", "istat_code", "response_status", *CONTEXT, *COUNT_FIELDS}


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate response JSON member")
        result[key] = value
    return result


def _nonfinite(value):
    raise ValueError("Non-finite response JSON number")


def _date(value):
    if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
        raise ValueError("Use an explicit YYYY-MM-DD source date or null")
    return date.fromisoformat(value)


def review_response(raw: bytes, mapping: dict[str, str]) -> dict:
    """Validate only the exchange contract; never infer stock partitions or ratios."""
    document = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_unique, parse_constant=_nonfinite)
    if (not isinstance(document, dict) or set(document) != ROOT_FIELDS
            or document["schema_version"] != "0.5-erp-response-template-draft-2"
            or document["status"] != "technical_draft_do_not_publish"
            or document["scientific_approval"] is not False or document["publication_allowed"] is not False
            or type(document["target_analysis_year"]) is not int or document["target_analysis_year"] != 2025
            or type(document["request_sent"]) is not bool):
        raise ValueError("Require an unapproved v2 ERP response model; no automatic migration or approval")
    _date(document["requested_reference_date"])
    vocabulary = document["response_status_vocabulary"]
    if (not isinstance(vocabulary, dict) or set(vocabulary) != set(STATUSES)
            or any(not isinstance(v, str) or not v.strip() for v in vocabulary.values())):
        raise ValueError("Require the existing five response status codes")
    records = document["municipalities"]
    if len(mapping) != 27 or not isinstance(records, list) or len(records) != 27:
        raise ValueError("Account for all 27 registry municipalities, including missing responses")
    identities = {code: name for name, code in mapping.items()}
    reviewed = {}
    for row in records:
        if not isinstance(row, dict) or set(row) != ROW_FIELDS:
            raise ValueError("Response row fields must match the v2 exchange model")
        code = row["istat_code"]
        if not isinstance(code, str) or code not in identities or row["municipality"] != identities[code] or code in reviewed:
            raise ValueError("Require exact unique registry names and six-digit ISTAT identities")
        state = row["response_status"]
        if not isinstance(state, str) or state not in STATUSES:
            raise ValueError("Unknown ERP response status")
        for key in COUNT_FIELDS:
            value = row[key]
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(f"ERP counts require non-negative JSON integers or null: {key}")
        for key in CONTEXT[1:]:
            if row[key] is not None and not isinstance(row[key], str):
                raise ValueError(f"Context must be source text or null: {key}")
        actual = None if row["actual_reference_date"] is None else _date(row["actual_reference_date"])
        missing = [key for key in COUNT_FIELDS if row[key] is None]
        issues = []
        if state != "not_provided":
            issues.extend("missing_context:" + key for key in CONTEXT
                          if row[key] is None or (isinstance(row[key], str) and not row[key].strip()))
        if state in {"data_provided", "verified_zero"} and len(missing) == len(COUNT_FIELDS):
            issues.append("declared_data_without_counts")
        elif state in {"data_provided", "verified_zero"} and missing:
            issues.append("partial_count_fields")
        if state in {"not_provided", "not_managed", "unavailable"} and len(missing) != len(COUNT_FIELDS):
            issues.append("counts_conflict_with_response_status")
        if state == "verified_zero":
            if row["erp_total"] != 0:
                issues.append("zero_declaration_without_explicit_total_zero")
            if any(row[key] is not None and row[key] > 0 for key in COUNT_FIELDS):
                issues.append("positive_count_in_zero_declaration")
        reviewed[code] = {**row, "missing_count_fields": missing, "review_issues": issues,
                          "target_minus_actual_reference_year": None if actual is None else 2025 - actual.year}
    if set(reviewed) != set(identities):
        raise ValueError("Response identity coverage differs from the registry")
    ordered = [reviewed[code] for code in mapping.values()]
    return {"schema_version": "0.5-erp-response-review-1", "status": "technical_draft_do_not_publish",
            "result": "local_response_imported_for_review", "target_analysis_year": 2025,
            "requested_reference_date": document["requested_reference_date"],
            "request_sent_as_declared": document["request_sent"],
            "response_status_counts": {key: Counter(r["response_status"] for r in ordered)[key] for key in STATUSES},
            "municipalities_with_any_counts": sum(len(r["missing_count_fields"]) < len(COUNT_FIELDS) for r in ordered),
            "municipalities_with_review_issues": sum(bool(r["review_issues"]) for r in ordered),
            "municipalities": ordered, "weights_applied": False,
            "indicator_calculated": False, "municipal_series_added": 0,
            "scientific_approval": False, "publication_allowed": False,
            "messages_sent_by_tool": 0, "network_requests_made": 0}


def import_response(response: Path, registry: Path, out_dir: Path, *, synthetic: bool = False) -> Path:
    if out_dir.exists() or out_dir.is_symlink():
        raise FileExistsError("Preserve earlier products; choose a fresh ERP import directory")
    raw, registry_raw = response.read_bytes(), registry.read_bytes()
    mapping = read_municipality_codes(registry)
    report = review_response(raw, mapping)
    source_hash, registry_hash = hashlib.sha256(raw).hexdigest(), hashlib.sha256(registry_raw).hexdigest()
    report.update(source_sha256=source_hash, registry_sha256=registry_hash,
                  input_kind="synthetic_declared" if synthetic else "unclassified_local_response")
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".erp-response-", dir=out_dir.parent) as temporary:
        stage = Path(temporary) / "review"
        (stage / "inputs").mkdir(parents=True)
        (stage / "inputs/response.json").write_bytes(raw)
        (stage / "inputs/registry.csv").write_bytes(registry_raw)
        (stage / "review.json").write_text(json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2) + "\n",
                                          encoding="utf-8", newline="\n")
        columns = ["municipality", "istat_code", "response_status", *CONTEXT,
                   "target_minus_actual_reference_year", *COUNT_FIELDS, "missing_count_fields", "review_issues"]
        with (stage / "responses.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(columns)
            for row in report["municipalities"]:
                writer.writerow([spreadsheet_safe_cell(";".join(row[key]) if isinstance(row[key], list)
                                                     else "" if row[key] is None else row[key]) for key in columns])
        marker = "DATI SINTETICI - NON SONO DATI TERRITORIALI\n\n" if synthetic else "RISPOSTA LOCALE DA REVISIONARE\n\n"
        (stage / "README_REVIEW.txt").write_text(
            marker + "BOZZA TECNICA: technical_draft_do_not_publish\n"
            + f"Record comunali: 27. Con almeno un conteggio: {report['municipalities_with_any_counts']}.\n"
            + "Gli stati sono dichiarazioni della fonte, non approvazioni del software.\n"
            + "Conservare la cartella intera e gli originali ricevuti. Conteggi mancanti: celle vuote, non zero.\n"
            + "Non gestito/non disponibile/non ricevuto non significano assenza di ERP nel Comune.\n"
            + "Date effettive distinte dalla data richiesta; differenze di anno senza pesi.\n"
            + "Nessuna somma fra categorie, deduplicazione, rapporto o nuova osservazione.\n"
            + "CSV: testo a rischio formula reso letterale con apostrofo; originale e JSON conservano i valori.\n"
            + "Rivedere provenienza, copertura, insiemi di assegnabilita e proprietari/gestori.\n"
            + "La classificazione delle cause e il denominatore famiglie restano da verificare.\n"
            + "Nessuna rete, invio o autorizzazione alla pubblicazione.\n", encoding="utf-8", newline="\n")
        files = ("inputs/response.json", "inputs/registry.csv", "review.json", "responses.csv", "README_REVIEW.txt")
        manifest = {"schema_version": "0.5-erp-response-import-1", "status": "technical_draft_do_not_publish",
                    "input_kind": report["input_kind"], "source_sha256": source_hash, "registry_sha256": registry_hash,
                    "files_sha256": {name: sha256_file(stage / name) for name in files},
                    "scientific_approval": False, "publication_allowed": False, "indicator_calculated": False}
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
        if sha256_file(response) != source_hash or sha256_file(registry) != registry_hash:
            raise ValueError("Response or registry changed during import; discard the new review")
        return publish_directory(stage, out_dir)


def create_example(out_dir: Path) -> Path:
    """Exercise the same importer with 27 fictitious identities and mixed replies."""
    if out_dir.exists() or out_dir.is_symlink():
        raise FileExistsError("Preserve earlier products; choose a fresh example directory")
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".erp-example-", dir=out_dir.parent) as temporary:
        root = Path(temporary)
        registry = root / "registry.csv"
        with registry.open("w", encoding="utf-8", newline="") as handle:
            csv.writer(handle).writerows([["municipality", "istat_code"],
                                        *[(f"Comune sintetico ERP {i}", f"000{i:03d}") for i in range(1, 28)]])
        request = build_packet(registry, "2025-12-31", root / "request")
        document = json.loads((request / "response_template.json").read_text(encoding="utf-8"))
        for row, state in zip(document["municipalities"], ("data_provided", "verified_zero", "not_managed", "unavailable")):
            row.update(response_status=state, actual_reference_date="2024-12-31" if state == "data_provided" else "2025-12-31",
                       owner_manager_scope="Gestore fittizio ERP", coverage_note="Esempio: assegnabilita riferita ai soli sfitti; nessuna somma fra assi",
                       source_reference="SYNTHETIC SOFTWARE EXAMPLE")
        document["municipalities"][0].update(erp_total=10, erp_occupied=7, erp_let=6, erp_vacant_total=3,
                                              erp_assignable=2, erp_non_assignable=1, erp_vacant_maintenance=1)
        document["municipalities"][1].update({field: 0 for field in COUNT_FIELDS})
        response = root / "response.json"
        response.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
        return import_response(response, registry, out_dir, synthetic=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--response", type=Path, help="Mapped v2 JSON copy, preserving the received original separately")
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--synthetic", action="store_true", help="Label user-supplied fictitious data")
    parser.add_argument("--example", action="store_true", help="Generate fictitious input and run the same importer")
    args = parser.parse_args(argv)
    if args.example and (args.response is not None or args.registry is not None):
        parser.error("--example does not accept real input paths")
    if not args.example and (args.response is None or args.registry is None):
        parser.error("Require --response and --registry, or --example")
    try:
        out = create_example(args.out_dir) if args.example else import_response(
            args.response, args.registry, args.out_dir, synthetic=args.synthetic)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, f"BLOCKED: {exc}\n")
    print(f"Import ERP locale preparato: {out / 'responses.csv'}. Nessun indicatore calcolato o messaggio inviato.")
    return 0
