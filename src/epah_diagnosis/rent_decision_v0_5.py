"""Apply an explicit, evidence-bound human decision to the rental subset only."""
from datetime import date
import hashlib
from html import escape
import json
import re

RESERVATIONS = ["historical_2021_not_2025", "homeless_households_excluded", "source_decimals_nonresponse_precision_unresolved", "six_residuals_preserved_without_adjustment", "not_energy_poverty_prevalence"]
KEYS = {"schema_version", "indicator_id", "period", "decision", "approved_by", "role", "decided_on", "publication_allowed", "publication_scope", "full_statistical_validation", "evidence_sha256", "review_dossier_manifest_sha256", "reservations", "user_statement", "authorization_provenance"}


def fingerprint(preview, contract):
    fields = ['formula', 'period', 'target_analysis_year', 'decimal_precision', 'rounding', 'residual_definition', 'universe', 'source_sha256', 'rows']
    body = {'preview': {k: preview[k] for k in fields}, 'contract': contract}
    return hashlib.sha256(json.dumps(body, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()


def validate_decision(record, preview, contract):
    if (not isinstance(record, dict) or set(record) != KEYS
            or record['schema_version'] != '0.5-rent-decision-1'
            or record['indicator_id'] != 'V05-19' or record['period'] != '2021'
            or record['decision'] != 'definition_and_calculation_approved_with_reservations'
            or type(record['publication_allowed']) is not bool
            or record['publication_scope'] != 'V05-19_2021_only_with_limitations'
            or record['full_statistical_validation'] is not False
            or record['reservations'] != RESERVATIONS
            or record['authorization_provenance'] != 'explicit_user_statement_in_chat'):
        raise ValueError('Expected explicit rental-only decision retaining all reservations')
    for key in ['approved_by', 'role', 'decided_on', 'user_statement']:
        if not isinstance(record[key], str) or not record[key].strip() or len(record[key]) > 4000:
            raise ValueError('Explicit bounded human decision details required')
    if date.fromisoformat(record['decided_on']).isoformat() != record['decided_on']:
        raise ValueError('Decision date must be ISO YYYY-MM-DD')
    for key in ['evidence_sha256', 'review_dossier_manifest_sha256']:
        if not isinstance(record[key], str) or not re.fullmatch('[0-9a-f]{64}', record[key]):
            raise ValueError('Decision requires explicit evidence and dossier hashes')
    if record['evidence_sha256'] != fingerprint(preview, contract):
        raise ValueError('Decision does not cover these values, source bytes or indicator contract')
    return dict(record)


def decision_panel(decision):
    if not decision:
        return '<p>Definizione e calcolo non ancora approvati; pubblicazione non autorizzata.</p>'
    permission = 'autorizzata per questa quota con i limiti visibili' if decision['publication_allowed'] else 'non autorizzata'
    return (f'<section class="notice" id="rent-decision"><h3>Definizione e calcolo approvati con riserve</h3>'
            f'<p><strong>{escape(decision["approved_by"])}</strong> · {escape(decision["role"])} · {escape(decision["decided_on"])}. '
            f'Pubblicazione: <strong>{permission}</strong>.</p>'
            '<p>Validazione statistica completa della fonte: ancora da completare. Restano aperti origine dei decimali, trattamento delle non risposte/imputazioni e precisione locale. '
            'La decisione riguarda esclusivamente la quota affitto 2021 e la versione delle evidenze identificata dagli hash; non è una certificazione EPAH e non approva gli altri indicatori.</p>'
            '<p><a href="rent_decision.json">Decisione registrata e riferimenti alle evidenze</a>. '
            'Registrazione della dichiarazione esplicita in chat, senza firma digitale o attestazione esterna.</p></section>')


def public_page(snapshot):
    from .indicator_dashboard_v0_5 import chart, rent_preview_panel
    decision = snapshot['rent_decision']
    if not decision or not decision['publication_allowed']:
        raise ValueError('Rental publication requires explicit subset authorization')
    preview = snapshot['rent_preview']
    rows = [r for r in snapshot['observations'] if r['indicator_id'] == 'V05-19']
    parts = ['<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Quota affitto 2021 · approvazione con riserve</title><style>body{font:17px/1.5 Segoe UI,Arial,sans-serif;color:#193d48;background:#eef4f2;margin:0}main{max-width:1100px;margin:auto;padding:24px}.notice{background:#fff2d7;padding:20px;margin:20px 0;border-left:4px solid #ad7b27}.chart,.table{overflow:auto}.chart svg{display:block;width:100%;min-width:650px}table{width:100%;border-collapse:collapse;font-size:14px}td,th{padding:9px;text-align:left;border-bottom:1px solid #bccfc8;overflow-wrap:anywhere}a{color:#00696b}h1{line-height:1.2}@media(max-width:600px){main{padding:14px}}@media print{.chart svg{min-width:0}}</style></head><body><main><p>EPAH Diagnosis · V05-19 · contesto abitativo</p><h1>Famiglie in affitto · 2021</h1>', rent_preview_panel(preview, decision), '<div class="chart">', chart(rows, 'Quota di famiglie in affitto 2021', '2021 · % · 100 × RENT / ALL', False, True, True), '</div>', '<h2>Valori e input originali</h2><p>Quote visualizzate a due decimali. Precisione di calcolo e tutti gli input nel <a href="rent_preview.csv">CSV</a>; <a href="snapshot.json">snapshot</a> e <a href="manifest.json">hash del pacchetto</a>.</p><div class="table"><table><thead><tr><th>Comune</th><th>Quota %</th><th>RENT</th><th>ALL</th><th>Residuo</th></tr></thead><tbody>']
    from decimal import Decimal
    for row in preview['rows']:
        parts.append(f"<tr><td>{escape(row['geo_code'])} · {escape(row['geo_name'])}</td><td>{Decimal(row['value']):.2f}</td><td>{escape(row['rent'])}</td><td>{escape(row['all'])}</td><td>{escape(row['residual'])}</td></tr>")
    url = next(i for i in snapshot['indicators'] if i['id'] == 'V05-19')['source']['url']
    parts.append(f'</tbody></table></div><p>Fonte: ISTAT, flusso IT1,DF_DCSS_HUDW_1_COM,1.0; NPHH_AV. <a href="{escape(url, quote=True)}">Rapporto di riferimento</a>. Metadati e hash degli originali nello snapshot. Nessun indice composito o graduatoria di priorità.</p></main></body></html>')
    return ''.join(parts)
