"""Offline, accessible, local-only dashboard for audited 27-town v0.2 results."""
from __future__ import annotations

import json


def document(data: dict) -> str:
    """Build a standalone document; escape JSON so data cannot close script tags."""
    if data.get("status") != "technical_draft_do_not_publish":
        raise ValueError("Cannot make a public-looking dashboard from unreviewed state")
    payload = json.dumps(data, ensure_ascii=True, separators=(",", ":"), allow_nan=False)
    payload = payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return TEMPLATE.replace("__PAYLOAD__", payload)


TEMPLATE = r"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<title>EPAH v0.2 | Diagnosi territoriale dei 27 Comuni | Bozza tecnica</title>
<style>
:root { color-scheme: light; --ink:#17364a; --muted:#4d626e; --border:#cad8dd;
  --pale:#f1f6f7; --accent:#27697b; --paper:#fff; }
* { box-sizing:border-box; }
body { font-family:Arial,Helvetica,sans-serif; line-height:1.5; color:var(--ink);
  background:#f7fafb; margin:0; }
header,main,footer { max-width:1100px; padding:22px; margin:auto; }
header { padding-top:40px; }
h1 { line-height:1.16; font-size:clamp(1.5rem,3vw,2.3rem); margin:4px 0 14px; }
h2 { font-size:1.17rem; }
.eyebrow { letter-spacing:.08em; text-transform:uppercase; font-size:.8rem; font-weight:bold; }
.note { color:var(--muted); font-size:.92rem; }
.warning { border-left:5px solid var(--ink); background:#e9f1f4; padding:15px 17px; }
.panel { background:var(--paper); border:1px solid var(--border); border-radius:9px;
  padding:20px; margin:20px 0; }
.controls { display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:15px; }
label { font-size:.9rem; display:block; margin-bottom:5px; font-weight:bold; }
input,select { width:100%; border:1px solid #718e9d; border-radius:5px;
  background:#fff; font:inherit; padding:9px; color:var(--ink); }
input:focus-visible,select:focus-visible { outline:3px solid var(--accent); outline-offset:2px; }
.data { overflow-x:auto; }
table { width:100%; border-collapse:collapse; text-align:left; font-size:.92rem; }
th,td { padding:11px 9px; border-bottom:1px solid var(--border); vertical-align:middle; }
th { background:var(--pale); }
.bar { display:inline-block; background:#a5c8d1; height:10px; min-width:2px;
  vertical-align:middle; border-radius:3px; }
.numeric { text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }
footer { color:var(--muted); font-size:.85rem; border-top:1px solid var(--border); }
.small { font-size:.82rem; color:var(--muted); }
.summary { font-size:1rem; margin:15px 0 5px; }
@media (max-width:560px){header,main,footer{padding:14px} .panel{padding:14px}
  th,td{padding:9px 5px} .hide-mobile{display:none} }
@media print { .controls {display:none} body{background:white} .panel{break-inside:avoid}
  header,main,footer{max-width:100%} }
</style>
</head>
<body>
<header>
<p class="eyebrow">Assistenza Tecnica EPAH 2026 | 26-IT-Unione-TA26</p>
<h1>Diagnosi territoriale - 27 Comuni</h1>
<p>Sinergie in Canavese | Dashboard esplorativa v0.2 | Dati comunali aggregati</p>
<div class="warning"><strong>BOZZA TECNICA - NON PUBBLICARE.</strong>
Non misura la povertà energetica delle famiglie, non è una graduatoria di rischio
e non costituisce un documento ufficiale della Commissione europea.
I valori sono proxy eterogenei per anno e denominatore.</div>
</header>
<main>
<section class="panel" aria-labelledby="title-data">
<h2 id="title-data">Esplora i singoli indicatori</h2>
<p class="note">Confronti rispetto alla mediana <em>non ponderata</em> dei 27 Comuni.
Sopra la mediana non significa automaticamente maggiore povertà energetica.
La barra indica una posizione relativa nell'intervallo osservato, non una classe di rischio.</p>
<div class="controls">
<div><label for="indicator">Indicatore</label><select id="indicator"></select></div>
<div><label for="search">Cerca Comune</label><input id="search" type="search"
  autocomplete="off" placeholder="Nome o codice ISTAT"></div>
<div><label for="snai">Classe SNAI</label><select id="snai">
<option value="">Tutte le classi</option><option>A</option><option>B</option>
<option>C</option><option>D</option><option>E</option><option>F</option></select></div>
<div><label for="sort">Ordinamento descrittivo</label><select id="sort">
<option value="name">Nome Comune</option><option value="asc">Valore crescente</option>
<option value="desc">Valore decrescente</option></select></div>
</div>
<p id="count" class="summary" aria-live="polite"></p>
<div class="data"><table><caption class="small">Valori e periodi originali del bundle pilota; nessun punteggio combinato.</caption>
<thead><tr><th>Comune</th><th class="hide-mobile">ISTAT</th><th class="numeric">Valore</th>
<th class="numeric">Mediana</th><th class="hide-mobile">Anno</th><th>Intervallo relativo</th></tr></thead>
<tbody id="municipalities"></tbody></table></div>
</section>
<section class="panel" aria-labelledby="title-pair">
<h2 id="title-pair">Lettura incrociata di due indicatori</h2>
<p class="note">Conteggio dei Comuni con valori superiori a entrambe le mediane.
È un'intersezione descrittiva, non un indice o un'associazione causale.</p>
<div class="controls">
<div><label for="indicator-a">Indicatore A</label><select id="indicator-a"></select></div>
<div><label for="indicator-b">Indicatore B</label><select id="indicator-b"></select></div>
</div>
<p id="pair-count" class="summary" aria-live="polite"></p>
</section>
<section class="panel">
<h2>Metodologia e limiti</h2>
<p>Otto indicatori quantitativi indipendenti e classificazione SNAI non numerica.
Le mediane sono calcolate su 27 Comuni senza pesatura per popolazione;
gli anni di riferimento sono riportati per ogni riga.
I dati CIT in quarantena non sono inclusi.</p>
<p>Il pacchetto originale contiene anni, fonti, licenze e QA dei nove indicatori.
Questo cruscotto non accede alla rete, non utilizza cookie, non
raccoglie dati personali e non effettua alcuna pubblicazione.</p>
</section>
</main>
<footer>EPAH Diagnosis v0.2 | Uso interno FERVORES e Unione Montana |
Da sottoporre a revisione scientifica, istituzionale ed editoriale prima della diffusione.</footer>
<script id="epah-data" type="application/json">__PAYLOAD__</script>
<script>
"use strict";
const data = JSON.parse(document.getElementById("epah-data").textContent);
const $ = id => document.getElementById(id);
const fmt = new Intl.NumberFormat("it-IT", {maximumFractionDigits:1});
function selectOptions(select) {
  for (const indicator of data.indicators) {
    const opt=document.createElement("option"); opt.value=indicator.key;
    opt.textContent=indicator.label + " (" + indicator.unit + ")";
    select.appendChild(opt);
  }
}
for (const id of ["indicator","indicator-a","indicator-b"]) selectOptions($(id));
$("indicator-b").selectedIndex=1;
function metric(key) { return data.indicators.find(x=>x.key===key); }
function cell(row, value, css) {
  const td=document.createElement("td"); td.textContent=String(value);
  if(css) td.className=css; row.appendChild(td); return td;
}
function renderRows() {
  const key=$("indicator").value, m=metric(key);
  const search=$("search").value.trim().toLocaleLowerCase("it-IT");
  const snai=$("snai").value;
  const subset=data.municipalities.filter(r=>
    (!snai || r.snai===snai) &&
    (r.name.toLocaleLowerCase("it-IT").includes(search) || r.code.includes(search)));
  const mode=$("sort").value;
  subset.sort((a,b)=>mode==="name"?a.name.localeCompare(b.name,"it"):
    mode==="asc"?a.values[key].value-b.values[key].value:
      b.values[key].value-a.values[key].value);
  const values=data.municipalities.map(r=>r.values[key].value);
  const low=Math.min(...values), high=Math.max(...values);
  const body=$("municipalities"); body.replaceChildren();
  for (const row of subset) {
    const tr=document.createElement("tr"), x=row.values[key];
    cell(tr,row.name); cell(tr,row.code,"hide-mobile");
    cell(tr,fmt.format(x.value)+" "+m.unit,"numeric");
    cell(tr,fmt.format(x.median)+" "+m.unit,"numeric");
    cell(tr,x.year,"hide-mobile");
    const td=cell(tr,"");
    const span=document.createElement("span"); span.className="bar";
    const width=high===low?50:Math.max(2,100*(x.value-low)/(high-low));
    span.style.width=width+"px";
    span.setAttribute("role","img");
    span.setAttribute("aria-label","Posizione relativa nell'intervallo dei 27 Comuni");
    td.appendChild(span);
    body.appendChild(tr);
  }
  $("count").textContent=subset.length+" Comuni visualizzati su 27";
}
function renderPair() {
  const a=$("indicator-a").value,b=$("indicator-b").value;
  const el=$("pair-count");
  if(a===b){el.textContent="Selezionare due indicatori diversi.";return;}
  const pair=data.pairs.find(x=>
    (x.a===a && x.b===b) || (x.a===b && x.b===a));
  el.textContent=pair ? pair.count+" Comuni su 27 sopra entrambe le mediane." :
    "Confronto non disponibile.";
}
for(const id of ["indicator","search","snai","sort"]) {
  $(id).addEventListener("input",renderRows);
}
for(const id of ["indicator-a","indicator-b"]) {
  $(id).addEventListener("change",renderPair);
}
renderRows();renderPair();
</script>
</body></html>
"""
