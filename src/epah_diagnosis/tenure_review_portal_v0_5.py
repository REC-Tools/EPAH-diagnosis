"""Build a portable offline portal from checked tenure source snapshots."""
from __future__ import annotations

import argparse
import hashlib
from html import escape
import json
from pathlib import Path
import tempfile

from .cli import read_municipality_codes
from .directory_publication import publish_directory
from .tenure_source_review_v0_5 import check_run_receipt, inspect_response, metadata_profile

REVIEWED = {"source_reviewed", "reused_source_reviewed"}
CATEGORY_LABELS = [("ALL", "Totale della tavola"), ("RENT", "Affitto"),
                   ("OWN", "Proprietà"), ("OTH_OR", "Altro titolo")]
GAPS = [
    ("Stress da freddo", "Export UTCI 2025 non incluso", "Verificare campo, unità e copertura dell'originale: prossima priorità."),
    ("Disagio di spazio (ISAC)", "Aggregato comunale non incluso", "Reperire l'aggregato o dati congiunti e criterio nazionale documentato."),
    ("Dotazione ERP", "Stock completo e datato non incluso", "Verificare le fonti pubbliche; mantenere la richiesta in bozza locale."),
    ("Sfitto ERP per manutenzione", "Conteggi per causa non inclusi", "Verificare cause dello sfitto, data e perimetro dello stock."),
    ("Prezzi e reddito", "Confronto non incluso", "Verificare fonte, scala territoriale, unità e periodi compatibili."),
]


def issue_label(issue):
    known = {"partition_not_exact_no_tolerance_applied": "Totale e categorie differiscono; nessuna tolleranza applicata.",
             "missing_tenure_categories": "Una o più categorie non sono disponibili.",
             "source_periods_missing_or_different": "Periodi della fonte assenti o diversi fra categorie.",
             "denominator_universe_note_absent": "Manca la nota sull'universo del totale.",
             "denominator_not_positive": "Totale non positivo: rapporto non calcolabile."}
    if issue.startswith("missing_or_invalid_value:"):
        return "Valore mancante o non valido: " + dict(CATEGORY_LABELS).get(issue.split(":", 1)[1], "categoria da verificare") + "."
    if issue.startswith("source_flag_requires_review:"):
        return "Flag della fonte da interpretare: " + issue.rsplit(":", 1)[-1] + "."
    return known.get(issue, "Controllo della fonte da revisionare.")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def assemble_snapshot(run_dir: Path, notes: Path):
    files = {name: (run_dir / name).read_bytes() for name in
             ["run.json", "inputs/metadata.xml", "inputs/registry.csv"]}
    profile = metadata_profile(files["inputs/metadata.xml"])
    mapping = read_municipality_codes(run_dir / "inputs/registry.csv")
    receipt = json.loads(files["run.json"].decode("utf-8"))
    records = check_run_receipt(receipt, profile["metadata_sha256"], digest(files["inputs/registry.csv"]), mapping.values())
    if (run_dir / "inputs/registry.csv").read_bytes() != files["inputs/registry.csv"]:
        raise ValueError("Registry changed during portal preparation")
    by_code = {record["istat_code"]: record for record in records}
    if "reused-run.json" in receipt["input_sha256"]:
        raw = (run_dir / "inputs/reused-run.json").read_bytes()
        if digest(raw) != receipt["input_sha256"]["reused-run.json"]:
            raise ValueError("Previous-run receipt checksum mismatch")
        files["inputs/reused-run.json"] = raw
    files["inputs/review-notes.md"] = notes.read_bytes()
    notes_text = files["inputs/review-notes.md"].decode("utf-8")
    rows = []
    for name, code in mapping.items():
        record = by_code[code]
        row = {"municipality": name, "istat_code": code, "state": record["state"],
               "error": record.get("error"), "periods": [], "values": {}, "issues": [],
               "partition_difference": None, "raw_link": None, "review_link": None,
               "request_receipt_link": None}
        if record.get("response_sha256") is not None:
            path = f"raw/{code}.xml"
            raw = (run_dir / path).read_bytes()
            if digest(raw) != record["response_sha256"]:
                raise ValueError(f"Original source checksum mismatch: {code}")
            files[path] = raw
            row["raw_link"] = path
        if record["state"] in REVIEWED:
            if row["raw_link"] is None:
                raise ValueError(f"Reviewed source lacks original bytes: {code}")
            review = inspect_response(files[row["raw_link"]], code, profile)
            path = f"reviews/{code}.json"
            raw_review = (run_dir / path).read_bytes()
            if json.loads(raw_review.decode("utf-8")) != review:
                raise ValueError(f"Saved review disagrees with original source: {code}")
            files[path] = raw_review
            row.update(periods=review["source_periods"],
                       values={o["source_key"]["TENURE_STATUS_HOU"]: o["value_as_received"] for o in review["observations"]},
                       issues=review["review_issues"], partition_difference=review["partition_difference_as_received"],
                       review_link=path)
        path = f"receipts/{code}.json"
        if (run_dir / path).is_file():
            raw_receipt = (run_dir / path).read_bytes()
            if json.loads(raw_receipt.decode("utf-8")) != record:
                raise ValueError(f"Request receipt disagrees with run receipt: {code}")
            files[path] = raw_receipt
            row["request_receipt_link"] = path
        rows.append(row)
    snapshot = {"schema_version": "0.5-tenure-review-portal-1", "status": "technical_draft_do_not_publish",
                "target_analysis_year": 2025, "source_run_phase": receipt["phase"], "municipalities": rows,
                "source_notes": profile["denominator_note"], "other_indicators_not_in_this_pack": GAPS,
                "review_notes_sha256": digest(files["inputs/review-notes.md"]), "weights_applied": False,
                "indicator_calculated": False, "municipal_series_added": 0,
                "scientific_approval": False, "publication_allowed": False}
    return snapshot, files, notes_text


def render(snapshot, notes_text):
    rows = snapshot["municipalities"]
    present = sum(any(value is not None for value in row["values"].values()) for row in rows)
    issues = sum(bool(row["issues"]) for row in rows)
    body = []
    for row in rows:
        code = row["istat_code"]
        available = any(value is not None for value in row["values"].values())
        state = "Fonte disponibile" if available else "Fonte da completare"
        if row["issues"]:
            state += " · questioni da revisionare"
        label = "Scarto obiettivo − fonte: " + ", ".join(str(2025 - int(year)) + " anni" for year in row["periods"]) if row["periods"] else "Anno non disponibile"
        values = "".join("<td class='number'>" + escape(row["values"].get(key) if row["values"].get(key) is not None else "Non disponibile") + "</td>" for key, _ in CATEGORY_LABELS)
        links = []
        for key, title in [("raw_link", "Originale"), ("review_link", "Controllo"), ("request_receipt_link", "Richiesta")]:
            if row[key]:
                links.append(f"<a href='{escape(row[key], quote=True)}'>{title}</a>")
        links.append("<a href='run.json'>Ricevuta run</a>")
        detail = ""
        if row["issues"]:
            detail = "<details><summary>Dettagli del controllo</summary><p>Residuo ricevuto: " + escape(str(row["partition_difference"]) if row["partition_difference"] is not None else "non valutabile") + "</p><ul>" + "".join("<li>" + escape(issue_label(issue)) + "</li>" for issue in row["issues"]) + "</ul></details>"
        elif not available:
            reasons = {"not_requested": "Codice non richiesto nel run.", "request_started": "Richiesta non conclusa nel run.",
                       "request_failed": "Richiesta non riuscita.", "source_review_failed": "Tracciato o identità da verificare."}
            detail = "<p>" + escape(reasons.get(row["state"], row["state"])) + " " + escape(row["error"] or "") + "</p>"
        body.append(f"<tr data-search='{escape((row['municipality'] + ' ' + code).lower(), quote=True)}' data-issues='{1 if row['issues'] else 0}' data-kind='{'missing' if not available else 'present'}'><th scope='row'>{escape(row['municipality'])}<small>{code}</small></th><td>{escape(', '.join(row['periods']) or 'Non disponibile')}<small>{escape(label)}</small></td>{values}<td>{escape(state)}<small>Residuo: {escape(str(row['partition_difference']) if row['partition_difference'] is not None else 'non valutabile')}</small>{detail}</td><td class='links'>{' '.join(links)}</td></tr>")
    notes_text = notes_text.replace("\r\n", "\n").replace("\r", "\n")
    notes = "".join("<h3>" + escape(p.lstrip("# ").strip()) + "</h3>" if p.startswith("# ") else "<p>" + escape(" ".join(p.splitlines())) + "</p>" for p in notes_text.strip().split("\n\n") if p.strip())
    gaps = "".join("<tr><th scope='row'>" + escape(name) + "</th><td>" + escape(reason) + "</td><td>" + escape(next_step) + "</td></tr>" for name, reason, next_step in GAPS)
    headers = "".join("<th scope='col'>" + escape(title) + "</th>" for _, title in CATEGORY_LABELS)
    return f"""<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Affitto · revisione delle fonti dei 27 Comuni</title>
<style>
:root{{color-scheme:light;font-family:system-ui,sans-serif;color:#172b38;background:#eef3f5}}*{{box-sizing:border-box}}body{{margin:0}}a{{color:#065987;text-underline-offset:3px}}a:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible{{outline:3px solid #ae5700;outline-offset:3px}}header{{background:#173f4e;color:white;padding:2rem max(1.25rem,calc((100vw - 1380px)/2))}}header p{{max-width:75ch;line-height:1.6}}h1{{font-size:clamp(1.6rem,3vw,2.5rem);margin:.5rem 0}}main{{max-width:1420px;padding:1.25rem;margin:auto}}section{{background:white;padding:1.4rem;margin-bottom:1.25rem;border:1px solid #c7d5dc;border-radius:12px}}h2{{font-size:1.35rem;margin-top:0}}p,li{{line-height:1.6}}.draft{{font-size:.85rem;letter-spacing:.04em}}.metrics{{display:flex;gap:1rem;flex-wrap:wrap;margin:1.5rem 0 0}}.metrics div{{border-left:3px solid #a6d6d6;padding-left:.8rem;min-width:180px}}.metrics strong{{display:block;font-size:1.7rem}}.notice{{padding:.8rem 1rem;border-left:4px solid #ad6400;background:#fff4df}}.controls{{display:flex;gap:1rem;flex-wrap:wrap;align-items:end}}label{{display:block;font-weight:650}}input,select{{font:inherit;padding:.65rem;border:1px solid #63818e;border-radius:6px;max-width:100%}}input{{width:290px}}.scroll{{overflow:auto}}table{{width:100%;border-collapse:collapse;font-size:.94rem}}.source-table{{min-width:1160px}}th,td{{text-align:left;vertical-align:top;padding:.85rem .65rem;border-bottom:1px solid #d6e0e4}}thead{{background:#eaf1f3}}tbody th{{font-weight:650}}small{{display:block;font-weight:400;color:#435b68;margin-top:.35rem;line-height:1.45}}.number{{font-variant-numeric:tabular-nums;white-space:nowrap}}.links a{{display:block;margin-bottom:.45rem}}details{{margin-top:.6rem;max-width:245px}}details ul{{padding-left:1rem;overflow-wrap:anywhere}}caption{{text-align:left;font-weight:600;padding:1rem 0}}.provenance{{display:flex;gap:1rem;flex-wrap:wrap}}footer{{padding:0 1.25rem 2rem;max-width:1420px;margin:auto;color:#435b68}}@media print{{header{{background:white;color:#172b38}}.controls{{display:none}}.scroll{{overflow:visible}}.source-table{{min-width:0}}table{{font-size:8pt}}section{{break-inside:auto}}}}
</style></head><body><header><div class="draft">BOZZA TECNICA · technical_draft_do_not_publish</div><h1>Affitto: fonti dei 27 Comuni</h1><p>Revisione del contesto storico. Anno obiettivo della diagnosi: <strong>2025</strong>. Gli anni delle fonti restano espliciti; nessun valore è stato rietichettato o trasformato in percentuale.</p><div class="metrics"><div><strong>{present}/27</strong>Comuni con valori della fonte</div><div><strong>{issues}</strong>Comuni con questioni da revisionare</div><div><strong>2025</strong>anno obiettivo, distinto dalla fonte</div></div></header>
<main><section aria-labelledby="scope"><h2 id="scope">Come leggere i dati</h2><p>La tavola ISTAT del titolo di godimento esclude le famiglie senza tetto dal totale. Mantenere questo universo esplicito: non sostituire il totale con quello generale delle famiglie.</p><p>I valori sono conteggi della fonte, anche decimali, conservati con il separatore originale (punto). Il residuo è la differenza fra totale e somma delle categorie, senza tolleranza o redistribuzione. Nessun peso temporale è applicato.</p><p class="notice">Il portale è una base di revisione. Revisione scientifica dei risultati: da completare. Pubblicazione: non autorizzata. La disponibilità di un originale non approva un indicatore o la pubblicazione.</p><nav class="provenance" aria-label="Documenti del pacchetto"><a href="inputs/metadata.xml">Metadati ISTAT</a><a href="inputs/registry.csv">Registro dei Comuni</a><a href="inputs/review-notes.md">Nota breve del revisore</a><a href="snapshot.json">Dati del portale</a><a href="manifest.json">Hash dei file</a></nav></section>
<section aria-labelledby="data"><h2 id="data">Valori originali e copertura</h2><div class="controls"><div><label for="search">Cerca Comune o codice ISTAT</label><input id="search" type="search" placeholder="Es. Alpette o 001007"></div><div><label for="kind">Mostra</label><select id="kind"><option value="all">Tutti i Comuni</option><option value="issues">Questioni da revisionare</option><option value="missing">Fonti da completare</option></select></div><p id="count" role="status" aria-live="polite">27 Comuni visibili</p></div><noscript><p>La tabella completa resta disponibile. Per cercare usare la funzione Trova del browser.</p></noscript><div class="scroll" tabindex="0" aria-label="Tabella delle fonti, scorribile orizzontalmente"><table class="source-table"><caption>Conteggi della fonte · ordine del registro, senza graduatorie</caption><thead><tr><th scope="col">Comune</th><th scope="col">Anno fonte e scarto</th>{headers}<th scope="col">Stato e limiti</th><th scope="col">Fonti e controlli</th></tr></thead><tbody id="municipalities">{''.join(body)}</tbody></table></div></section>
<section aria-labelledby="notes"><h2 id="notes">Metodo e decisioni leggere</h2>{notes}</section><section aria-labelledby="gaps"><h2 id="gaps">Altri indicatori da completare</h2><p>Questi dati non sono inclusi in questo pacchetto della fonte affitto. Per ciascuno restano visibili la lacuna e il prossimo passo.</p><div class="scroll"><table><thead><tr><th scope="col">Tema</th><th scope="col">Lacuna nel pacchetto</th><th scope="col">Prossimo passo</th></tr></thead><tbody>{gaps}</tbody></table></div></section></main><footer>Conservare e trasferire l'intera cartella. Le copie degli originali, i controlli e le note sono collegati localmente. Nessun servizio remoto è richiesto per consultare il portale.</footer>
<script>const rows=[...document.querySelectorAll('#municipalities tr')],search=document.querySelector('#search'),kind=document.querySelector('#kind');function filter(){{let visible=0;for(const row of rows){{row.hidden=!(row.dataset.search.includes(search.value.trim().toLocaleLowerCase())&&(kind.value==='all'||(kind.value==='issues'&&row.dataset.issues==='1')||(kind.value==='missing'&&row.dataset.kind==='missing')));if(!row.hidden)visible++;}}document.querySelector('#count').textContent=visible+' Comuni visibili';}}search.addEventListener('input',filter);kind.addEventListener('change',filter);</script></body></html>"""


def build_portal(run_dir: Path, notes: Path, out_dir: Path):
    source, target = run_dir.resolve(), out_dir.resolve()
    if source == target or target.is_relative_to(source) or source.is_relative_to(target):
        raise ValueError("Portal and original run must be separate, non-nested destinations")
    if out_dir.exists() or out_dir.is_symlink():
        raise FileExistsError("Choose a fresh portal destination; no overwrite")
    snapshot, files, notes_text = assemble_snapshot(run_dir, notes)
    files["snapshot.json"] = (json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    files["index.html"] = render(snapshot, notes_text).encode("utf-8")
    manifest = {"schema_version": "0.5-tenure-review-portal-manifest-1", "status": "technical_draft_do_not_publish",
                "files_sha256": {name: digest(raw) for name, raw in sorted(files.items())},
                "source_run_sha256": digest(files["run.json"]), "review_notes_sha256": snapshot["review_notes_sha256"],
                "scientific_approval": False, "publication_allowed": False}
    files["manifest.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".tenure-portal-", dir=out_dir.parent) as temporary:
        stage = Path(temporary) / "portal"
        stage.mkdir()
        for name, raw in files.items():
            path = stage / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        publish_directory(stage, out_dir)
    return out_dir


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--notes", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        out = build_portal(args.run_dir, args.notes, args.out_dir)
    except (ValueError, OSError, TypeError, KeyError) as exc:
        parser.exit(2, f"BLOCKED: {exc}\n")
    print(f"Portale di revisione pronto: {out / 'index.html'}")
    return 0
