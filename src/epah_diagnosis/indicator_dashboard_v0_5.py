"""Offline views of 23 proposals and supplied values; no acquisition or scientific promotion."""
from __future__ import annotations
import argparse
import csv
from decimal import Decimal, InvalidOperation
import hashlib
from html import escape
import json
import re
from pathlib import Path
import shutil
import tempfile
from urllib.parse import urlsplit
from .directory_publication import publish_directory
from .methodology_v0_5 import check_catalog
from .rent_decision_v0_5 import validate_decision, decision_panel, public_page

STATUS = "technical_draft_do_not_publish"
FIELDS = {"indicator_id", "geo_code", "geo_name", "scope", "period", "series", "unit", "value", "missing_reason", "source_url", "source_note"}
TITLES = ["Eccesso di mortalità estivo", "Giorni di stress da freddo", "Giorni di stress da caldo", "Persone in abitazioni migliorate negli ultimi cinque anni", "Rischio di povertà AROP", "Deprivazione materiale/sociale e possesso dell'auto", "Spesa di consumo destinata ai trasporti", "Impossibilità economica di possedere un'auto", "Frequenza d'uso del trasporto pubblico", "Eccesso di mortalità invernale", "Sistema di riscaldamento utilizzato", "Abitazione non confortevolmente calda in inverno", "Famiglie senza comfort estivo", "Spesa di consumo per finalità COICOP", "Incapacità economica di riscaldare adeguatamente", "Arretrati sulle utenze", "Elevato rapporto spesa energetica/reddito (2M)", "Spesa energetica molto bassa (M/2)", "Famiglie in affitto", "Superficie abitativa critica (ISAC)", "Alloggi ERP ogni 100 famiglie", "ERP sfitti per manutenzione", "Rapporto prezzo abitazioni/reddito"]
UNITS = {"percent": "%", "days_per_year": "giorni/anno", "z_score": "z-score", "dwellings_per_100_households": "alloggi/100 famiglie", "price_to_income_ratio": "rapporto prezzo/reddito"}


SCOPES = {"country": "Paese: benchmark", "grid_country_aggregate": "Griglia aggregata a scala nazionale", "municipality_target_not_verified": "Comune: candidato da revisionare", "nuts3_benchmark_only": "NUTS3: benchmark"}
ROLES = {"health_context": "Contesto sanitario", "climate_exposure": "Esposizione climatica", "housing_context": "Contesto abitativo", "socioeconomic_context": "Contesto socioeconomico", "mobility_context": "Mobilità", "self_reported_affordability": "Difficoltà economica dichiarata", "expenditure_distribution": "Distribuzione della spesa"}


def encode(obj):
    return (json.dumps(obj, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode("utf-8")


def load_json(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError("Duplicate JSON key")
            out[key] = value
        return out
    def invalid(value):
        raise ValueError("Non-finite JSON number")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=invalid)


def load_catalogs(paths):
    indicators, hashes = {}, {}
    for path in paths:
        raw = path.read_bytes()
        doc = load_json(raw)
        check_catalog(doc)
        hashes[path.name] = hashlib.sha256(raw).hexdigest()
        for item in doc["indicators"]:
            if item["id"] in indicators:
                raise ValueError("Duplicate proposal across catalogues")
            indicators[item["id"]] = {**item, "display_name": TITLES[int(item["id"][-2:]) - 1], "source": doc["sources"][item["source_ref"]]}
    if set(indicators) != {f"V05-{i:02}" for i in range(1, 24)}:
        raise ValueError("Dashboard requires the exact 23 existing proposals")
    return indicators, hashes


def validate_observations(document, indicators):
    expected = {"schema_version", "input_kind", "scientific_approval", "publication_allowed", "observations"}
    if (not isinstance(document, dict) or set(document) != expected
            or document["schema_version"] != "0.5-dashboard-observations-1"
            or document["input_kind"] not in {"synthetic_declared", "precomputed_technical_review"}
            or document["scientific_approval"] is not False or document["publication_allowed"] is not False
            or not isinstance(document["observations"], list)):
        raise ValueError("Expected explicitly unapproved, precomputed observations or declared synthetic data")
    seen, result = set(), []
    for row in document["observations"]:
        if not isinstance(row, dict) or set(row) != FIELDS:
            raise ValueError("Missing or unknown observation fields")
        item = indicators.get(row["indicator_id"])
        if item is None or row["unit"] != item["unit"] or row["scope"] != item["geography"]:
            raise ValueError("Unknown indicator, unit or geography differs from the existing contract")
        for key in FIELDS - {"value", "missing_reason"}:
            if not isinstance(row[key], str) or not row[key].strip() or len(row[key]) > 3000:
                raise ValueError("Observation labels, series and provenance must be explicit bounded text")
        if document['input_kind'] != 'synthetic_declared':
            scope = item['geography']
            pattern = r'(?:[A-Z]{2}|EU27_2020)' if scope in {'country', 'grid_country_aggregate'} else r'[0-9]{6}' if scope == 'municipality_target_not_verified' else r'[A-Z]{2}[A-Z0-9]{3}'
            if not re.fullmatch(pattern, row['geo_code']):
                raise ValueError('Geographic code does not match the declared scale; municipal codes cannot label national benchmarks')
        url = urlsplit(row["source_url"])
        if url.scheme != "https" or not url.hostname or url.username or url.password or "\\" in row["source_url"]:
            raise ValueError("Observation source must be a public HTTPS URL without credentials")
        identity = tuple(row[k] for k in ("indicator_id", "scope", "geo_code", "period", "series"))
        if identity in seen:
            raise ValueError("Duplicate observation identity")
        seen.add(identity)
        value = row["value"]
        if value is None:
            if row["missing_reason"] not in {"not_acquired", "suppressed", "not_applicable", "not_responded"}:
                raise ValueError("Missing values require an explicit missingness reason")
        else:
            if not isinstance(value, str) or row["missing_reason"] is not None:
                raise ValueError("Values must be decimal strings; missingness must be null for present values")
            try:
                number = Decimal(value)
            except InvalidOperation as exc:
                raise ValueError("Invalid decimal value") from exc
            if not number.is_finite() or abs(number) > Decimal("1e12"):
                raise ValueError("Non-finite or out-of-range value")
            if item["unit"] == "percent" and not 0 <= number <= 100:
                raise ValueError("Percent outside 0..100")
            if item["unit"] == "days_per_year" and not 0 <= number <= 366:
                raise ValueError("Annual days outside 0..366")
            if item["unit"] in {"dwellings_per_100_households", "price_to_income_ratio"} and number < 0:
                raise ValueError("Negative housing count or ratio")
        result.append(dict(row))
    return result


def example(indicators):
    rows = []
    for index, item in enumerate(indicators.values(), 1):
        for geo in range(1, 4):
            value = str(-1 + geo * 1.25) if item["unit"] == "z_score" else str(30 * geo + index) if item["unit"] == "days_per_year" else str(index + geo / 10)
            rows.append(dict(indicator_id=item["id"], geo_code=f"SYN-{geo}", geo_name=f"Territorio fittizio {geo}", scope=item["geography"], period="2025", series="Serie dimostrativa", unit=item["unit"], value=value, missing_reason=None, source_url=item["source"]["url"], source_note="Valore inventato per collaudare la visualizzazione; non proviene dalla fonte collegata."))
    return {"schema_version": "0.5-dashboard-observations-1", "input_kind": "synthetic_declared", "scientific_approval": False, "publication_allowed": False, "observations": rows}


def chart(rows, title, subtitle, synthetic, preview=False, approved=False):
    values = [Decimal(r["value"]) for r in rows if r["value"] is not None]
    if not values:
        return "<p>Nessun valore numerico: le assenze non sono zero.</p>"
    low, high = min([Decimal(0), *values]), max([Decimal(0), *values])
    if high == low:
        high = low + 1
    def x(value):
        return 330 + float((value - low) / (high - low)) * 320
    zero = x(Decimal(0))
    height = 100 + 30 * len(rows)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 {height}" role="img" aria-label="{escape(title, quote=True)}">', f'<title>{escape(title)}</title>', f'<text x="18" y="23" font-size="14" font-weight="bold">{escape("DATI SINTETICI | " if synthetic else "CALCOLO APPROVATO CON RISERVE | " if approved else "BOZZA TECNICA | ")}{escape(subtitle)}</text>', f'<line x1="{zero}" x2="{zero}" y1="38" y2="{height-30}" stroke="#8eaaa7"/>']
    for i, row in enumerate(rows):
        y = 60 + 30 * i
        label = f'{row["geo_code"]} · {row["geo_name"]}'
        parts.append(f'<text x="18" y="{y}" font-size="13">{escape(label[:43])}</text>')
        if row["value"] is None:
            parts.append(f'<text x="355" y="{y}" font-size="12">ASSENTE: {escape(row["missing_reason"])}</text>')
        else:
            point = x(Decimal(row["value"]))
            parts.extend([f'<line x1="{zero}" x2="{point}" y1="{y-4}" y2="{y-4}" stroke="#92b9af" stroke-width="3"/>', f'<circle cx="{point}" cy="{y-4}" r="5" fill="#087c75"/>', f'<text x="684" y="{y}" font-size="13">{escape(format(Decimal(row['value']), '.2f') if preview else row['value'])}</text>'])
    parts.append('</svg>')
    return ''.join(parts)



def rent_preview_panel(preview, decision=None):
    parts = ['<section class="notice"><h3>Anteprima storica 2021 · 27 Comuni</h3><p><strong>100 × RENT / ALL</strong>, usando i conteggi originali, senza correggere il denominatore. Universo ISTAT: famiglie senza tetto escluse. Il 2021 non sostituisce l’anno obiettivo 2025. Non misura la povertà energetica.</p><p>I conteggi decimali della fonte richiedono ancora chiarimento. Sei residui conservati: ALL − (OWN + RENT + OTH_OR); nessuna tolleranza o correzione applicata. Ordine per codice ISTAT, senza graduatoria.</p><p>Grafico arrotondato a 2 decimali; calcolo a 50 cifre significative (ROUND_HALF_EVEN), valori e input riproducibili nel <a href="rent_preview.csv">CSV della quota affitto</a>. Validazione statistica della fonte ancora da completare; stato di approvazione e pubblicazione indicato nella decisione, se presente.</p><div class="table"><table><caption>Sei residui originali, visibili anche nel CSV di tutti i 27 Comuni</caption><thead><tr><th>Comune</th><th>Residuo originale</th></tr></thead><tbody>']
    for row in preview['rows']:
        if row['has_residual']:
            parts.append(f"<tr><td>{escape(row['geo_code'])} · {escape(row['geo_name'])}</td><td>{escape(row['residual'])}</td></tr>")
    parts.append('</tbody></table></div></section>')
    parts.append(decision_panel(decision))
    return ''.join(parts)


def render(snapshot):
    synthetic = snapshot["input_kind"] == "synthetic_declared"
    css = """*{box-sizing:border-box}body{margin:0;font:17px/1.5 Segoe UI,Arial,sans-serif;background:#eef4f2;color:#193d48}header{background:#153e48;color:white;padding:32px max(20px,calc((100vw - 1160px)/2))}h1{font-size:38px;line-height:1.2}main{max-width:1200px;margin:auto;padding:22px}.notice{background:#fff2d7;padding:18px;border-left:4px solid #ad7b27;margin-bottom:22px}.stats,.filters{display:flex;gap:18px;flex-wrap:wrap}.stats>div{background:#fff;padding:15px;border-radius:8px}.stats b{display:block;font-size:28px}.filters{background:white;padding:18px;margin:22px 0}input,select{font:inherit;padding:9px;width:100%;max-width:430px}label{display:block}article{background:white;padding:24px;border:1px solid #d1e0dc;border-radius:10px;margin:18px 0}article h2{font-size:24px;line-height:1.3}dt{font-weight:bold;margin-top:10px}dd{margin-left:0}small,.meta{font-size:14px}a{color:#006d70}header a{color:#bbebdd}.chart{overflow:auto}.chart svg{display:block;min-width:650px;width:100%;font-family:Segoe UI,Arial,sans-serif}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:9px;border-bottom:1px solid #dae5e2;text-align:left;overflow-wrap:anywhere}.table{overflow:auto}th{background:#eef5f2}details{margin:14px 0}summary{cursor:pointer}a:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible{outline:3px solid #c08424;outline-offset:3px}[hidden]{display:none!important}@media(max-width:650px){main{padding:12px}article{padding:16px}h1{font-size:30px}.filters>label{width:100%}}@media print{.filters,nav{display:none}body{background:white}article{break-before:page;border:0}.chart svg{min-width:0}header{color:#193d48;background:white}}"""
    n = snapshot["numeric_indicator_count"]
    decision = snapshot.get('rent_decision')
    approval_notice = ('Quota affitto 2021: definizione e calcolo approvati con riserve. Pubblicazione della sola quota ' + ('autorizzata' if decision['publication_allowed'] else 'non autorizzata') + '. Gli altri indicatori restano in revisione.' if decision else 'Nessuna approvazione scientifica o autorizzazione alla pubblicazione.')
    html = ['<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>23 indicatori v0.5 | EPAH</title><style>', css, '</style></head><body><header><p>EPAH Diagnosis · v0.5 · revisione tecnica</p><h1>23 indicatori: dati, grafici e prossimi passi</h1><p>Benchmark, esposizione e contesto restano distinti. Nessun indice composito o graduatoria.</p></header><main>']
    html += [f'<div class="notice"><strong>{"DATI SINTETICI: nessun risultato territoriale reale." if synthetic else "BOZZA TECNICA: valori eventualmente forniti da revisionare."}</strong><br>Stato complessivo: {STATUS}. {escape(approval_notice)}</div>', f'<section class="stats"><div><b>23</b>indicatori consultabili</div><div><b>{n}</b>con valori {"sintetici" if synthetic else "tecnici"}</div><div><b>{23-n}</b>senza valori numerici</div><div><b>{len(snapshot["source_notes"])}</b>indicatori con diagnostiche locali</div></section>', '<nav><p><a href="observations.csv">Esporta osservazioni CSV</a> · <a href="snapshot.json">Snapshot JSON</a> · <a href="readiness.csv">Stato dei 23 indicatori</a> · <a href="observations_template.json">Tracciato per valori precalcolati</a></p></nav>', '<section class="filters" id="filters" hidden><label>Cerca indicatore<input id="search" type="search" placeholder="ID, nome o tema"></label><label>Mostra<select id="availability"><option value="">Tutti</option><option value="present">Con valori</option><option value="absent">Senza valori</option></select></label><p id="results" role="status" aria-live="polite"></p></section>']
    if decision and decision['publication_allowed']:
        html.append('<section class="notice"><strong>Pagina della sola quota autorizzata alla pubblicazione</strong><p><a href="rent_publication/index.html">Apri quota affitto 2021 con grafico, limiti e decisione</a>. La dashboard completa e gli archivi di revisione non sono autorizzati alla pubblicazione da questa decisione.</p></section>')
    if snapshot["source_notes"]:
        html += ['<section><h2>Evidenze locali e stato dei calcoli</h2><p>La presenza della fonte non rende completo l’indicatore. <a href="source_review/index.html">Apri il portale delle fonti verificato</a>.</p>']
        for identifier, note in snapshot["source_notes"].items():
            html.append(f'<p><strong>{identifier}</strong>: {escape(note)}</p>')
        if snapshot["source_rows"]:
            html.append('<details><summary>Grafico dei conteggi in affitto nella fonte ISTAT</summary><p>Conteggi originali, inclusi i decimali; non è la quota V05-19. I periodi sono quelli della fonte, non l’anno obiettivo. Il totale della tavola esclude le famiglie senza tetto.</p>')
            for period in sorted({r['period'] for r in snapshot['source_rows']}):
                html.append('<div class="chart">')
                html.append(chart([r for r in snapshot['source_rows'] if r['period'] == period], 'Fonte ISTAT: conteggi affitto', f'Fonte in revisione · famiglie · {period}', False))
                html.append('</div>')
            html.append('<p>I conteggi e le anomalie sono consultabili nel portale fonti collegato.</p></details>')
        html.append('</section>')
    for item in snapshot["indicators"]:
        rows = [r for r in snapshot["observations"] if r["indicator_id"] == item["id"]]
        present = any(r['value'] is not None for r in rows)
        html += [f'<article id="{item["id"]}" data-present="{str(present).lower()}"><p class="meta">{item["id"]} · {escape(ROLES[item["role"]])} · {escape(SCOPES[item["geography"]])}</p><h2>{escape(item["display_name"])}</h2>', f'<p><strong>{"VALORI SINTETICI" if synthetic and present else "CALCOLO APPROVATO CON RISERVE · 2021" if decision and item["id"] == "V05-19" else "ANTEPRIMA TECNICA CALCOLATA · 2021" if snapshot.get("rent_preview") and item["id"] == "V05-19" else "VALORI FORNITI DA REVISIONARE" if present else "DATI NON DISPONIBILI"}</strong> · {escape(UNITS[item["unit"]])}</p><p>{escape(item["definition"])}</p>']
        is_preview = bool(snapshot.get('rent_preview')) and item['id'] == 'V05-19'
        if is_preview:
            html.append(rent_preview_panel(snapshot['rent_preview'], decision))
        groups = {}
        for row in rows:
            groups.setdefault((row['scope'], row['period'], row['series']), []).append(row)
        for (scope, period, series), subset in groups.items():
            subtitle = f'{period} · {UNITS[item["unit"]]} · {series}'
            html.extend([f'<h3>{escape(subtitle)}</h3><p class="meta">Scala: {escape(SCOPES[scope])}</p><div class="chart">', chart(subset, item['display_name'], subtitle, synthetic, is_preview, bool(decision) and is_preview), '</div>'])
        if is_preview:
            html.append('<div class="table"><table><caption>2021 · quota visualizzata a 2 decimali; conteggi e residui originali. Precisione di calcolo nel CSV.</caption><thead><tr><th>Comune</th><th>Quota %</th><th>RENT</th><th>ALL</th><th>Residuo</th></tr></thead><tbody>')
            for row in snapshot['rent_preview']['rows']:
                html.append(f"<tr><td>{escape(row['geo_code'])} · {escape(row['geo_name'])}</td><td>{Decimal(row['value']):.2f}</td><td>{escape(row['rent'])}</td><td>{escape(row['all'])}</td><td>{escape(row['residual'])}</td></tr>")
            html.append('</tbody></table></div>')
        elif rows:
            html.append('<div class="table"><table><caption>Valori forniti o calcolati con la precisione dichiarata; assenze distinte dagli zeri</caption><thead><tr><th>Territorio</th><th>Periodo</th><th>Serie</th><th>Valore</th><th>Fonte / nota</th></tr></thead><tbody>')
            for row in rows:
                value = row['value'] if row['value'] is not None else 'ASSENTE: ' + row['missing_reason']
                html.append(f'<tr><td>{escape(row["geo_code"])} · {escape(row["geo_name"])}</td><td>{escape(row["period"])}</td><td>{escape(row["series"])}</td><td>{escape(value)}</td><td><a href="{escape(row["source_url"], quote=True)}">Fonte dichiarata</a> · {escape(row["source_note"])}</td></tr>')
            html.append('</tbody></table></div>')
        else:
            html.append('<p>Nessun grafico numerico: manca una serie precalcolata con fonte, unità, periodo e scala coerenti.</p>')
        html.extend(['<details><summary>Definizione, denominatori e soluzione per completarlo</summary><dl>'])
        for label, key in [('Unità statistica', 'statistical_unit'), ('Universo', 'universe'), ('Numeratore', 'numerator'), ('Denominatore', 'denominator'), ('Periodo del contratto', 'reference_period')]:
            html.append(f'<dt>{label}</dt><dd>{escape(item[key])}</dd>')
        html.append('</dl><h3>Prossimi passi necessari</h3><ul>')
        for text in item['local_requirements'] + item['unresolved_decisions']:
            html.append('<li>' + escape(text) + '</li>')
        html.append('</ul><h3>Limiti</h3><ul>')
        html.extend('<li>' + escape(text) + '</li>' for text in item['limitations'])
        html.append(f'</ul><p><a href="{escape(item["source"]["url"], quote=True)}">{escape(item["source"]["title"])}</a> · {escape(item["source_locator"])}</p></details></article>')
    html.append('''<p id="empty" hidden>Nessun indicatore corrisponde ai filtri.</p><footer><p>Il comando visualizza contratti e valori tecnici. Solo --rent-preview calcola la quota affitto 2021; le altre 22 formule non sono calcolate automaticamente. Non acquisisce dati, non verifica l’autenticità degli input e non promuove osservazioni canoniche. Le fonti collegate richiedono rete; dashboard e grafici funzionano offline.</p></footer></main><script>
const cards=[...document.querySelectorAll('article')];const q=document.getElementById('search'),state=document.getElementById('availability');const norm=s=>s.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase();function filter(){let n=0;for(const c of cards){c.hidden=!(norm(c.textContent).includes(norm(q.value))&&(!state.value||(state.value==='present')===(c.dataset.present==='true')));if(!c.hidden)n++;}document.getElementById('results').textContent=n+' indicatori visualizzati su 23';document.getElementById('empty').hidden=n!==0;}document.getElementById('filters').hidden=false;q.addEventListener('input',filter);state.addEventListener('change',filter);filter();</script></body></html>''')
    return ''.join(html)


def build(catalogs, out_dir, *, observations=None, source_pack=None, synthetic=False, rent_preview=False, decision=None):
    indicators, hashes = load_catalogs(catalogs)
    if out_dir.exists() or out_dir.is_symlink():
        raise FileExistsError("Choose a new destination; no overwrite")
    for input_path in [*catalogs, *([observations] if observations else []), *([decision] if decision else []), *([source_pack] if source_pack else [])]:
        source, target = input_path.resolve(), out_dir.resolve()
        if source == target or source.is_relative_to(target) or target.is_relative_to(source):
            raise ValueError("Output must not overlap an input")
    if any(out_dir.resolve().is_relative_to(path.parent.resolve()) for path in catalogs):
        raise ValueError("Output must be outside catalogue/documentation directories")
    if synthetic and (observations or source_pack):
        raise ValueError("--example cannot be mixed with real or supplied inputs")
    if decision and not rent_preview:
        raise ValueError('--decision requires --rent-preview and a real source pack')
    if rent_preview and (not source_pack or synthetic):
        raise ValueError('--rent-preview requires a real --source-pack')
    raw = observations.read_bytes() if observations else None
    doc = example(indicators) if synthetic else load_json(raw) if raw else {"schema_version": "0.5-dashboard-observations-1", "input_kind": "precomputed_technical_review", "scientific_approval": False, "publication_allowed": False, "observations": []}
    rows = validate_observations(doc, indicators)
    if source_pack and doc['input_kind'] == 'synthetic_declared':
        raise ValueError("Synthetic observations cannot be mixed with a real source pack")
    if rent_preview and any(r['indicator_id'] == 'V05-19' for r in rows):
        raise ValueError('Do not mix supplied V05-19 values with the calculated preview')
    notes, source_rows, preview = {}, [], None
    if source_pack:
        from .source_review_hub_audit_v0_5 import audit_hub
        audit_hub(source_pack)
        src = load_json((source_pack / 'snapshot.json').read_bytes())
        if src['input_kind'] == 'synthetic_declared':
            raise ValueError("Use --example for synthetic data; source pack must be real")
        tenure = [m for m in src['municipalities'] if m['tenure'] is not None]
        atc = [m for m in src['municipalities'] if m['atc'] is not None]
        if tenure:
            notes['V05-19'] = f'Fonte affitto presente per {len(tenure)}/27 Comuni; conteggi e residui in revisione. Quota non calcolata.'
            for m in tenure:
                values = m['tenure'].get('values') or {}
                value = values.get('RENT')
                if value is not None:
                    number = Decimal(value)
                    if not number.is_finite() or number < 0:
                        raise ValueError('Invalid tenure source count')
                    periods = m['tenure'].get('periods', [])
                    if len(periods) == 1 and isinstance(periods[0], str):
                        source_rows.append({'geo_code': m['istat_code'], 'geo_name': m['municipality'], 'value': str(value), 'missing_reason': None, 'period': periods[0]})
        if src['utci'] is not None:
            notes['V05-02'] = 'Originale UTCI presente; unità, tempo e aggregazione comunale da revisionare. Nessun valore comunale calcolato.'
        if atc:
            notes['V05-21'] = f'{len(atc)}/27 risposte ATC incluse; non uno stock ERP completo datato.'
            notes['V05-22'] = 'Le risposte incluse non risolvono il conteggio ERP sfitto per manutenzione; aggregato specifico necessario.'
    if rent_preview:
        from .rent_preview_v0_5 import derive
        derived, preview = derive(source_pack, src, indicators['V05-19']['source']['url'])
        rows = validate_observations({**doc, 'observations': rows + derived}, indicators)
        notes['V05-19'] = 'Anteprima tecnica 2021: 27 quote calcolate come 100 × RENT / ALL; sei residui conservati. Nessuna approvazione scientifica.'
    decision_raw = decision.read_bytes() if decision else None
    approved = validate_decision(load_json(decision_raw), preview, indicators['V05-19']) if decision else None
    if approved:
        preview = {**preview, 'authorization_scope': 'Definizione e calcolo V05-19 2021 approvati con riserve da ' + approved['approved_by'] + '; autorizzazione alla pubblicazione limitata alla quota secondo rent_decision.json.'}
        notes['V05-19'] = 'Quota 2021: definizione e calcolo approvati con riserve da ' + approved['approved_by'] + '; pubblicazione della sola quota ' + ('autorizzata' if approved['publication_allowed'] else 'non autorizzata') + '. Restano i sei residui e i limiti statistici della fonte.'
    snapshot = {'rent_decision': approved, 'decision_sha256': hashlib.sha256(decision_raw).hexdigest() if decision_raw else None, 'publication_subset_allowed': bool(approved and approved['publication_allowed']), 'rent_preview': preview, 'technical_preview_observations_added': 27 if preview else 0, 'calculated_indicator_ids': ['V05-19'] if preview else [], 'schema_version': '0.5-indicator-dashboard-1', 'status': STATUS, 'scientific_approval': False, 'publication_allowed': False, 'municipal_series_added': 0, 'calculation_performed': bool(preview), 'source_authenticity_verified': False, 'input_kind': doc['input_kind'], 'catalog_sha256': hashes, 'observations_sha256': hashlib.sha256(raw).hexdigest() if raw else None, 'indicators': list(indicators.values()), 'observations': rows, 'source_notes': notes, 'source_rows': source_rows, 'numeric_indicator_count': len({r['indicator_id'] for r in rows if r['value'] is not None})}
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.v05-dashboard-', dir=out_dir.parent) as temporary:
        stage = Path(temporary) / 'dashboard'
        stage.mkdir()
        if source_pack:
            shutil.copytree(source_pack, stage / 'source_review', symlinks=True)
            audit_hub(stage / 'source_review')
        if approved:
            (stage / 'rent_decision.json').write_bytes(decision_raw)
        if preview:
            with (stage / 'rent_preview.csv').open('w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=list(preview['rows'][0]))
                writer.writeheader()
                writer.writerows(preview['rows'])
        (stage / 'snapshot.json').write_bytes(encode(snapshot))
        (stage / 'index.html').write_text(render(snapshot), encoding='utf-8', newline='\n')
        if raw:
            (stage / 'supplied_observations.json').write_bytes(raw)
        template = {**doc, 'input_kind': 'precomputed_technical_review', 'observations': []}
        (stage / 'observations_template.json').write_bytes(encode(template))
        with (stage / 'observations.csv').open('w', encoding='utf-8-sig', newline='') as f:
            fields = sorted(FIELDS)
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                safe = {k: ("'" + v if k != 'value' and isinstance(v, str) and v.startswith(('=', '+', '-', '@')) else v) for k, v in row.items()}
                writer.writerow(safe)
        with (stage / 'readiness.csv').open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['indicator_id', 'name', 'rendering_supported', 'calculation_implemented', 'numeric_values_supplied', 'source_note', 'definition_and_calculation_approved', 'full_statistical_validation', 'publication_allowed'])
            for item in indicators.values():
                writer.writerow([item['id'], item['display_name'], True, item['id'] == 'V05-19', sum(r['indicator_id'] == item['id'] and r['value'] is not None for r in rows), notes.get(item['id'], 'Nessuna evidenza locale fornita a questa esecuzione'), bool(approved) and item['id'] == 'V05-19', False, bool(approved and approved['publication_allowed']) and item['id'] == 'V05-19'])
        if approved and approved['publication_allowed']:
            subset = stage / 'rent_publication'
            subset.mkdir()
            (subset / 'index.html').write_text(public_page(snapshot), encoding='utf-8', newline='\n')
            (subset / 'rent_decision.json').write_bytes(decision_raw)
            shutil.copyfile(stage / 'rent_preview.csv', subset / 'rent_preview.csv')
            (subset / 'snapshot.json').write_bytes(encode({'status': 'approved_with_reservations', 'scientific_approval_scope': 'definition_and_calculation_only', 'full_statistical_validation': False, 'publication_allowed': True, 'decision': approved, 'rent_preview': preview}))
            (subset / 'manifest.json').write_bytes(encode({'status': 'approved_with_reservations', 'files_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in subset.iterdir() if p.is_file()}}))
        manifest = {p.relative_to(stage).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in stage.rglob('*') if p.is_file()}
        (stage / 'manifest.json').write_bytes(encode({'status': STATUS, 'files_sha256': manifest}))
        publish_directory(stage, out_dir)
    return snapshot


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[2]
    parser.add_argument('--catalog', type=Path, default=root / 'docs/v0_5_indicator_contracts.json')
    parser.add_argument('--housing-catalog', type=Path, default=root / 'docs/v0_5_housing_contracts.json')
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--observations', type=Path, help='Explicit precomputed observation JSON; no automatic acquisition')
    parser.add_argument('--source-pack', type=Path, help='Existing source-review pack; verified and copied; calculation requires --rent-preview')
    parser.add_argument('--rent-preview', action='store_true', help='Explicit historical 2021 RENT/ALL preview, preserving the six reviewed residuals')
    parser.add_argument('--decision', type=Path, help='Explicit evidence-bound human rental decision JSON; no approval of other indicators')
    parser.add_argument('--example', action='store_true', help='Invented data for all 23 charts, visibly marked synthetic')
    args = parser.parse_args(argv)
    try:
        result = build([args.catalog, args.housing_catalog], args.out_dir, observations=args.observations, source_pack=args.source_pack, synthetic=args.example, rent_preview=args.rent_preview, decision=args.decision)
    except (ValueError, OSError, TypeError, KeyError, InvalidOperation) as exc:
        parser.exit(2, f'BLOCKED: {exc}\n')
    print(f'Dashboard: {args.out_dir / "index.html"}; 23 schede, {result["numeric_indicator_count"]} con valori; input={result["input_kind"]}. Decisione quota affitto: {bool(result["rent_decision"])}; pubblicazione della sola quota: {result["publication_subset_allowed"]}.')
    return 0
