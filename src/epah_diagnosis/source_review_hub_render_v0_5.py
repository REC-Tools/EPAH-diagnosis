"""Offline presentation of the source hub snapshot; no source reads or formulas."""
from html import escape
import json

STYLE = """body{font-family:system-ui,sans-serif;color:#193641;background:#edf3f4;margin:0;line-height:1.6}header{background:#173f4e;color:white;padding:2rem}main{padding:1rem;max-width:1500px;margin:auto}section{background:white;border:1px solid #c7d5dc;border-radius:10px;padding:1.2rem;margin-bottom:1rem}a{color:#065987;text-underline-offset:3px}a:focus-visible,summary:focus-visible{outline:3px solid #ae5700;outline-offset:3px}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:.92rem}th,td{text-align:left;vertical-align:top;border-bottom:1px solid #d6e0e4;padding:.8rem}thead{background:#eaf1f3}caption{text-align:left;font-weight:600;padding:.5rem}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f1f5f6;padding:1rem}nav a{display:inline-block;margin-right:1rem}code{overflow-wrap:anywhere}.notice{border-left:4px solid #ad6400;padding-left:1rem}footer{padding:1rem 2rem}@media print{header{background:white;color:#193641}.scroll{overflow:visible}table{font-size:8pt}section{border-radius:0}}"""


def _text(value):
    return escape(str(value))


def _json(value):
    return escape(json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2))


def render(snapshot, comparison):
    changes = {} if comparison is None else {r["istat_code"]: r["changes"] for r in comparison["municipalities"]}
    rows = []
    for row in snapshot["municipalities"]:
        code, tenure, atc = row["istat_code"], row["tenure"], row["atc"]
        links = []
        if tenure is None:
            t = "Fonte non inclusa. Prossimo passo: includere una run ISTAT verificabile."
        else:
            t = "Anni: " + (", ".join(tenure["periods"]) or "non disponibili")
            t += "; scarto 2025: " + (", ".join(str(2025 - int(y)) for y in tenure["periods"]) or "non disponibile")
            for key in ("ALL", "RENT", "OWN", "OTH_OR"):
                t += "; " + key + ": " + (tenure["values"].get(key) if tenure["values"].get(key) is not None else "non disponibile")
            t += "; stato: " + tenure["state"] + "; residuo: " + str(tenure["partition_difference"])
            t += "; acquisita UTC: " + (tenure["acquired_at_utc"] or "non documentata")
            t += "; questioni: " + ", ".join(tenure["issues"])
            if not tenure["values"]:
                t += "; prossimo passo: completare lo snapshot della fonte."
            for key, title in (("raw_link", "ISTAT originale"), ("review_link", "ISTAT controllo"), ("request_receipt_link", "Ricevuta ISTAT")):
                if tenure[key]:
                    links.append("<a href='sources/tenure/" + tenure[key] + "'>" + title + "</a>")
        if atc is None:
            a = "Tabella non inclusa; stock sconosciuto. Prossimo passo: verificare disponibilità della fonte pubblica."
        else:
            report = atc["audit"]
            a = ("Righe della tabella: " + str(report["table_rows"]) + "; gruppi identici: " + str(len(report["identical_row_groups"]))
                 + "; data stock dichiarata: " + (atc["reference_date"] or "sconosciuta")
                 + "; acquisita il: " + (atc["acquired_on"] or "sconosciuto")
                 + "; selettore dichiarato: " + atc["source_selector"]
                 + "; identità ISTAT, stock ERP e data da verificare. Prossimo passo: chiarire perimetro, data e duplicati.")
            links.append("<a href='" + atc["original"] + "'>ATC originale come testo</a>")
        u = "Fonte UTCI inclusa; nessun valore comunale aggregato." if snapshot["utci"] else "Fonte UTCI non inclusa."
        d = "Primo pacchetto; confronto non richiesto." if comparison is None else ("Modificato" if changes[code] else "Invariato")
        rows.append("<tr data-code='" + code + "'><th scope='row'>" + _text(row["municipality"] + " · " + code)
                    + "</th><td>" + _text(t) + "</td><td>" + _text(a) + "</td><td>" + _text(u)
                    + "</td><td>" + " · ".join(links) + "</td><td>" + d + "</td></tr>")
    synthetic = "<p><strong>DATI SINTETICI · NON SONO DATI TERRITORIALI</strong></p>" if snapshot["input_kind"] == "synthetic_declared" else ""
    climate = ("<p>Fonte non inclusa. Prossimo passo: fornire l'originale e il campo esplicito.</p>"
               if snapshot["utci"] is None else "<p><a href='sources/utci.nc'>Originale NetCDF</a>. Campo, periodo decodificato, unità ricevute, copertura e questioni:</p><pre>" + _json(snapshot["utci"]) + "</pre>")
    delta = ("<p>Nessun confronto richiesto.</p>" if comparison is None else
             "<p>La versione precedente è conservata con gli originali sotto baseline/. Le differenze descrivono importazioni, non tendenze territoriali.</p><pre>" + _json(comparison) + "</pre>")
    extra = ""
    if snapshot["atc_provider"] is not None:
        extra += "<p>Un solo ente: " + _text(snapshot["atc_provider"]) + ". Nessuna somma tra gestori. Le righe non sono conteggi dello stock. Le associazioni sono dichiarazioni di raccolta, non identità ISTAT confermate dalla fonte.</p>"
    if snapshot["tenure_universe"] is not None:
        extra += "<p>Metadati ricevuti sull'universo:</p><pre>" + _json(snapshot["tenure_universe"]) + "</pre>"
        extra += "<p><a href='sources/tenure/inputs/review-notes.md'>Nota breve del revisore</a> · <a href='sources/tenure/inputs/metadata.xml'>Metadati ISTAT</a></p>"
    return f"""<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Fonti climatiche e abitative · 27 Comuni</title><style>{STYLE}</style></head><body>
<header><p>BOZZA TECNICA · technical_draft_do_not_publish</p><h1>Fonti climatiche e abitative</h1><p>27 Comuni · obiettivo 2025 · fonti, date e limiti per la revisione tecnica.</p>{synthetic}</header>
<main><section><h2>Come leggere il pacchetto</h2><p class="notice">Nessuna approvazione scientifica o istituzionale. Pubblicazione territoriale non autorizzata.</p><p>Affitto: contesto storico; l'universo ISTAT esclude le famiglie senza tetto. Conteggi decimali e residui conservati, senza tolleranza automatica. Nessun indicatore o peso temporale calcolato.</p><p>UTCI: la presenza del file non dimostra copertura comunale. Restano da verificare semantica del campo, contributi giornalieri e geometrie prima di aggregare.</p>{extra}<nav aria-label="Documenti"><a href="snapshot.json">Snapshot e controlli</a><a href="comparison.json">Differenze fra versioni</a><a href="manifest.json">Hash dei file</a><a href="inputs.json">Contratto degli input</a><a href="sources/registry.csv">Registro dei Comuni</a></nav></section>
<section><h2>I 27 Comuni</h2><p>Ordine del registro, senza graduatorie. Per cercare usare Trova nel browser; la tabella funziona senza JavaScript.</p><div class="scroll" tabindex="0" aria-label="Tabella scorribile"><table><caption>Fonti disponibili e passi necessari</caption><thead><tr><th scope="col">Comune e ISTAT</th><th scope="col">Titolo di godimento ISTAT</th><th scope="col">Tabella pubblica ATC</th><th scope="col">Clima UTCI</th><th scope="col">Originali e controlli</th><th scope="col">Versione</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></section>
<section><h2>Fonte climatica: controllo del file</h2>{climate}</section><section><h2>Confronto fra importazioni</h2>{delta}</section>
<section><h2>Altre lacune</h2><p>ISAC: manca l'aggregato comunale o il criterio documentato su dati congiunti. ERP e sfitto per manutenzione: le tabelle pubbliche non risolvono stock completo, assegnabilità e cause dello sfitto. Prezzi e reddito: verificare scala, unità e periodi compatibili. Nessun contatto con enti è stato effettuato dal comando.</p><p>I blocchi H03/H04 (unità e allineamento climatico) e H05 (perimetro APE) restano separati da questa revisione delle nuove fonti.</p></section></main><footer>Conservare e trasferire l'intera cartella. Consultazione offline, nessuna risorsa remota richiesta.</footer></body></html>"""
