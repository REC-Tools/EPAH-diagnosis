"""Step 7: additive keyboard/mobile accessibility improvements for the v0.4 atlas.

Only transforms v0.4 HTML after the stable v0.3 template was rendered.
Fails closed when template anchors change; never transforms or embeds new data.
"""
from __future__ import annotations


def _one(html: str, original: str, replacement: str) -> str:
    if html.count(original) != 1:
        raise ValueError("v0.4 accessibility template anchor missing or ambiguous: "
                         + original[:72])
    return html.replace(original, replacement, 1)


def enhance_atlas_html(html: str) -> str:
    """Add native focus/search semantics without altering the data payload."""
    if "BOZZA TECNICA" not in html or 'id="data"' not in html:
        raise ValueError("Only the unpublished technical atlas template is supported")

    # A visible-on-focus skip link, consistent landmarks and focus styles.
    html = _one(html, "</style></head><body>", """\
.skip-link{position:absolute;top:6px;left:-100vw;z-index:100;background:#fff;
color:#13374e;padding:10px 16px;border:2px solid #13374e;border-radius:6px}
.skip-link:focus{left:12px}
:focus-visible{outline:3px solid #af611d!important;outline-offset:3px}
.controls{grid-template-columns:minmax(0,1.25fr) minmax(0,1fr) minmax(0,1fr)}
.controls>div{min-width:0}
.search-actions{display:flex;justify-content:flex-end;margin-top:6px}
button{font:inherit;padding:8px 12px;border:1px solid #597b8b;
color:#17354a;background:#fff;border-radius:6px;cursor:pointer}
button:hover{background:#eaf3f6}
.tablewrap{overflow:auto;max-width:100%;border:1px solid var(--line);
border-radius:7px}
.tablewrap table{min-width:590px}
.tablewrap thead th{position:sticky;top:0;z-index:1;background:#edf4f6}
.tablewrap tbody tr:focus{outline:3px solid #af611d;outline-offset:-3px}
.sr-only{position:absolute!important;width:1px;height:1px;padding:0;
margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
#result-count{margin:10px 0;color:var(--muted);font-weight:600}
@media(max-width:880px){.controls{grid-template-columns:1fr}}
@media(max-width:500px){main{padding:0 12px 36px}
.panel,.intro{padding:15px}
.tablewrap table{min-width:590px}
.media figure{max-width:100%}
}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{scroll-behavior:auto!important}}
</style></head><body><a class="skip-link" href="#indicator">Salta ai filtri dell'atlante</a>""")
    html = _one(html, '<main><section class="intro">',
                '<main id="contenuto-principale"><section class="intro">')

    # All controls retain native keyboard support and discoverable labels.
    html = _one(
        html,
        '<label for="search">Cerca Comune</label><input id="search" type="search" placeholder="Nome o codice ISTAT">',
        '<label for="search">Cerca Comune</label>'
        '<input id="search" type="search" placeholder="Nome o codice ISTAT" '
        'autocomplete="off" aria-controls="rows" aria-describedby="search-help">'
        '<p id="search-help" class="note">Ricerca per nome, anche senza accenti, '
        'oppure per codice ISTAT.</p>',
    )
    html = _one(
        html,
        '</div></div>\n<p id="indicator-status" aria-live="polite">',
        '</div><div><label for="municipality-choice">Vai direttamente a un Comune</label>'
        '<select id="municipality-choice" aria-controls="rows">'
        '<option value="">Seleziona un Comune</option></select>'
        '<div class="search-actions"><button id="reset-search" type="button">'
        'Mostra tutti i Comuni</button></div></div></div>\n'
        '<p id="indicator-status" role="status" aria-live="polite" aria-atomic="true">',
    )
    html = _one(
        html,
        '<section class="panel"><h2>Valori comunali</h2>',
        '<section class="panel" id="valori-comunali" aria-labelledby="titolo-valori">'
        '<h2 id="titolo-valori">Valori comunali</h2>',
    )
    html = _one(
        html,
        '<div class="tablewrap"><table><thead><tr><th>Comune</th><th>Codice ISTAT</th><th>Anno</th><th>Valore</th></tr></thead>',
        '<p id="result-count" role="status" aria-live="polite" aria-atomic="true">'
        '27 Comuni su 27</p>'
        '<div class="tablewrap" role="region" aria-label="Tabella dei 27 Comuni: '
        'scorri orizzontalmente su schermi piccoli" tabindex="0">'
        '<table id="municipal-table"><caption class="sr-only">'
        'Valori comunali dell’indicatore selezionato, compresi quelli non acquisiti'
        '</caption><thead><tr><th scope="col">Comune</th>'
        '<th scope="col">Codice ISTAT</th><th scope="col">Anno</th>'
        '<th scope="col">Valore</th></tr></thead>',
    )

    # Keep a textual alternative for every visual and avoid overpromising
    # that a PNG map alone conveys the underlying data.
    html = _one(
        html,
        "img.alt=(kind==='map'?'Mappa tematica di ':'Distribuzione comunale di ')+item.name;fig.append(img);",
        "img.alt=(kind==='map'?'Mappa descrittiva di ':'Grafico descrittivo di ')"
        "+item.name+'. Tutti i valori comunali sono disponibili nella tabella seguente.';"
        "img.loading='lazy';img.decoding='async';fig.append(img);",
    )
    html = _one(
        html,
        "function draw(){const item=data.indicators.find(i=>i.id===select.value);",
        "function normaliseSearch(s){return String(s).normalize('NFD')"
        ".replace(/[\\u0300-\\u036f]/g,'').toLocaleLowerCase('it-IT').trim()}"
        "function draw(){const item=data.indicators.find(i=>i.id===select.value);",
    )
    html = _one(
        html,
        "const q=$('search').value.toLocaleLowerCase('it-IT').trim();const body=$('rows');body.replaceChildren();for(const r of data.municipalities){if(q&&!r.name.toLocaleLowerCase('it-IT').includes(q)&&!r.code.includes(q))continue;",
        "const q=normaliseSearch($('search').value);const body=$('rows');"
        "body.replaceChildren();let matches=0;"
        "for(const r of data.municipalities){"
        "if(q&&!normaliseSearch(r.name).includes(q)&&!r.code.includes(q))continue;",
    )
    html = _one(
        html,
        "const tr=document.createElement('tr');const v=r.values[item.id];",
        "const tr=document.createElement('tr');tr.id='comune-'+r.code;"
        "tr.tabIndex=-1;const v=r.values[item.id];",
    )
    html = _one(
        html,
        ":'n.d.');body.append(tr)}}",
        ":'Non acquisito');body.append(tr);matches++}"
        "if(matches===0){const tr=document.createElement('tr');"
        "const td=document.createElement('td');td.colSpan=4;"
        "td.textContent='Nessun Comune corrisponde alla ricerca. "
        "Cancella il filtro per visualizzare tutti i 27 Comuni.';"
        "tr.append(td);body.append(tr)}"
        "$('result-count').textContent=matches+' Comuni su 27 visibili "
        "per l’indicatore selezionato.';}",
    )
    html = _one(
        html,
        "select.addEventListener('change',draw);$('search').addEventListener('input',draw);draw();",
        "const choice=$('municipality-choice');"
        "for(const town of [...data.municipalities].sort((a,b)=>"
        "a.name.localeCompare(b.name,'it-IT'))){"
        "const option=document.createElement('option');option.value=town.code;"
        "option.textContent=town.name+' ('+town.code+')';choice.append(option)}"
        "choice.addEventListener('change',()=>{if(!choice.value)return;"
        "$('search').value=choice.value;draw();"
        "const found=$('comune-'+choice.value);if(found){found.focus();"
        "found.scrollIntoView({block:'nearest'})}});"
        "$('reset-search').addEventListener('click',()=>{"
        "$('search').value='';choice.value='';draw();$('search').focus()});"
        "select.addEventListener('change',draw);"
        "$('search').addEventListener('input',()=>{choice.value='';draw()});draw();",
    )
    return html
