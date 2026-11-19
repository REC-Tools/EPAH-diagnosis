"""Prepare a fresh ERP aggregate-request packet; no network, data intake or sending."""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import tempfile

from .cli import read_municipality_codes
from .directory_publication import publish_directory

COUNT_FIELDS = ("erp_total", "erp_occupied", "erp_let", "erp_vacant_total",
                "erp_assignable", "erp_non_assignable", "erp_vacant_maintenance",
                "erp_vacant_other_reason", "erp_vacant_unknown_reason")
STATUSES = {
    "not_provided": "Nessuna risposta ricevuta, conteggi ignoti",
    "data_provided": "Aggregati forniti con data, perimetro e provenienza da revisionare",
    "verified_zero": "Zero esplicitamente attestato dalla fonte per il perimetro dichiarato",
    "not_managed": "Territorio non gestito dal rispondente, non equivale ad assenza di ERP",
    "unavailable": "Dato non disponibile presso il rispondente",
}


def build_packet(registry: Path, reference_date: str, out_dir: Path) -> Path:
    requested_date = date.fromisoformat(reference_date)
    if requested_date.isoformat() != reference_date:
        raise ValueError("Use an explicit YYYY-MM-DD requested reference date")
    raw = registry.read_bytes()
    mapping = read_municipality_codes(registry)
    if len(mapping) != 27:
        raise ValueError("This territorial request requires exactly 27 municipalities")
    if registry.read_bytes() != raw:
        raise ValueError("Registry changed while preparing the request")
    if out_dir.exists() or out_dir.is_symlink():
        raise FileExistsError("Choose a fresh request packet destination; no overwrite")
    records = []
    for name, code in mapping.items():
        records.append({"municipality": name, "istat_code": code, "response_status": "not_provided",
                        "actual_reference_date": None, "owner_manager_scope": None,
                        "coverage_note": None, "source_reference": None,
                        **{field: None for field in COUNT_FIELDS}})
    template = {"schema_version": "0.5-erp-response-template-draft-2",
                "status": "technical_draft_do_not_publish", "target_analysis_year": 2025,
                "requested_reference_date": reference_date, "request_sent": False,
                "scientific_approval": False, "publication_allowed": False,
                "response_status_vocabulary": STATUSES, "municipalities": records}
    letter = f"""# Bozza di richiesta di dati aggregati ERP

All'attenzione dell'ufficio competente per i dati patrimoniali ERP

Oggetto: dati comunali per la diagnosi territoriale EPAH — 27 Comuni di Sinergie in Canavese

Per preparare l'analisi territoriale EPAH si richiedono aggregati sul patrimonio
di edilizia residenziale pubblica nei Comuni elencati sotto, possibilmente con
riferimento al **{requested_date.strftime('%d/%m/%Y')}**. Se questa data non è disponibile,
si chiede di indicare la data effettiva dell'estrazione e del patrimonio descritto.
L'anno obiettivo dell'analisi è il 2025; anni diversi resteranno riconoscibili.

Per ciascun Comune occorrono il totale degli alloggi ERP, gli alloggi occupati,
gli alloggi locati, il totale degli sfitti e gli alloggi assegnabili e non assegnabili.
Gli sfitti vanno inoltre distinti per manutenzione, altre cause e causa non conosciuta.
Si chiede di precisare proprietari e gestori inclusi, copertura, definizioni e
data del patrimonio. Un totale gestito da ATC e uno di proprietà comunale non
devono essere sommati se descrivono gli stessi alloggi.
Occupazione, locazione, assegnabilità e cause di sfitto sono distinzioni diverse:
si chiede di indicare a quale insieme si riferisce ciascun conteggio e quali
categorie si sovrappongono. Se l'assegnabilità riguarda solo gli sfitti, occorre
dichiararlo; non va estesa implicitamente a tutto il patrimonio.

Per ogni Comune senza dato si chiede di distinguere zero verificato, territorio
non gestito dal rispondente e dato non disponibile. Non occorrono nominativi,
recapiti o informazioni personali degli assegnatari.

Nel portale pubblico sono state osservate due righe uguali per Castellamonte
negli otto campi pubblicati, dopo normalizzazione degli spazi. Si chiede di
chiarire se corrispondano alla stessa gestione o a oggetti distinti. È utile
un identificativo di gestione/edificio che consenta il controllo senza dati personali.
Non sono stati eliminati record o calcolati totali a partire da quelle righe.

È sufficiente un formato tabellare già disponibile presso l'ente, accompagnato
dal dizionario delle colonne, dalle inclusioni/esclusioni e dalle condizioni
di utilizzo e diffusione degli aggregati. Il modello JSON allegato è facoltativo
e costituisce una traccia da revisionare, non un obbligo di formato.

## Comuni interessati

| Comune | Codice ISTAT |
| --- | --- |
"""
    for name, code in mapping.items():
        safe_name = name.replace("|", "\\|").replace("\n", " ").replace("\r", " ")
        letter += f"| {safe_name} | {code} |\n"
    letter += "\nFirma e recapiti del tecnico incaricato: da completare prima dell'invio.\n"
    instructions = """# Pacchetto di richiesta ERP da revisionare

Questo pacchetto è una bozza non inviata. Non contiene una risposta ATC,
uno stock ERP verificato o una nuova osservazione comunale.

1. Revisionare request.md, data proposta, perimetro e destinatario competente.
2. Completare firma/recapiti e allegare l'elenco dei Comuni; conservare la baseline.
3. Se si usa response_template.json, compilare una copia esterna alla repository.
   Tutti i conteggi iniziali sono null, non zero. La data richiesta non è la data
   dello stock: actual_reference_date deve riferirsi alla risposta effettiva.
4. Richiedere provenienza e copertura anche per zero verificato o non gestito.
   Gli stati proposti non costituiscono una validazione automatica della risposta.
5. Alla ricezione conservare originale, versione, data, condizioni di uso e hash;
   revisionare poi definizioni, possibili doppi conteggi e identità dei 27 codici.

## Campi proposti per gli aggregati

- erp_total: totale alloggi ERP nel perimetro dichiarato.
- erp_occupied: alloggi ERP occupati secondo la definizione dichiarata dalla fonte.
- erp_let: alloggi ERP locati nello stesso perimetro e alla stessa data.
- erp_vacant_total: totale alloggi ERP sfitti secondo la definizione della fonte.
- erp_assignable: alloggi dichiarati assegnabili, con insieme di riferimento esplicito.
- erp_non_assignable: alloggi dichiarati non assegnabili, con lo stesso insieme dichiarato.
- erp_vacant_maintenance: sfitti per necessità di manutenzione.
- erp_vacant_other_reason: sfitti per altre cause.
- erp_vacant_unknown_reason: sfitti con causa non conosciuta.
- owner_manager_scope: enti e perimetro proprietà/gestione, con deduplicazione da documentare.
- actual_reference_date: data effettiva del patrimonio descritto, distinta dall'acquisizione.
- coverage_note/source_reference: copertura, definizioni e riferimento alla fonte ricevuta.

Occupati e locati non sono sinonimi: conservare entrambi senza copiarne i valori.
L'assegnabilità può riguardare solo gli sfitti: documentarne l'insieme di riferimento
in coverage_note e nel dizionario ricevuto. Nessun insieme o resto è inferito.
Non sommare automaticamente campi se la fonte non ne attesta la partizione.
Non sommare occupazione, locazione, assegnabilità e cause di sfitto fra loro;
non ricavare totali o residui per differenza da categorie incomplete.
Il modello è una proposta di scambio: non viene importato da un calcolatore,
non verifica conteggi ricevuti e non attiva formule o approvazioni. La dotazione
per 100 famiglie richiederà anche un denominatore di famiglie coerente.

manifest.json lega i file al registro esatto senza esporne il percorso locale.
Non certifica qualità scientifica o autorizzazione alla pubblicazione.
"""
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".epah-erp-request-", dir=out_dir.parent) as temp:
        stage = Path(temp) / "packet"
        stage.mkdir()
        (stage / "request.md").write_text(letter, encoding="utf-8", newline="\n")
        (stage / "README_REVIEW.md").write_text(instructions, encoding="utf-8", newline="\n")
        (stage / "response_template.json").write_text(
            json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        receipt = {"schema_version": "0.5-erp-request-packet-2",
                   "status": "technical_draft_do_not_publish", "result": "request_packet_prepared_not_sent",
                   "target_analysis_year": 2025, "requested_reference_date": reference_date,
                   "request_sent": False, "scientific_approval": False, "publication_allowed": False,
                   "municipal_series_added": 0, "municipalities": 27,
                   "registry_sha256": hashlib.sha256(raw).hexdigest(),
                   "files_sha256": {name: hashlib.sha256((stage / name).read_bytes()).hexdigest()
                                    for name in ["request.md", "README_REVIEW.md", "response_template.json"]}}
        (stage / "manifest.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        publish_directory(stage, out_dir)
    return out_dir


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--reference-date", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        out = build_packet(args.registry, args.reference_date, args.out_dir)
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(2, f"BLOCKED: {exc}\n")
    print(f"Bozza ERP preparata, non inviata: {out / 'request.md'}")
    return 0
