"""Create consistent technical-only CSV, HTML and PDF from one checked atlas.

The pack never creates observations, replaces denominators, ranks municipalities,
or treats test/technical snapshots as approved energy-poverty measurements.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from html import escape as html_escape
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
from xml.sax.saxutils import escape as pdf_escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)

from epah_diagnosis.atlas_observations_v0_4 import build as export_observations, _sha

STATUS = "technical_draft_do_not_publish"
NOTICE = "BOZZA TECNICA - NON PUBBLICARE. Nessuna misura di povertà energetica familiare."


def _verified_atlas_files(atlas: Path) -> dict:
    manifest = json.loads((atlas / "atlas_manifest.json").read_text(encoding="utf-8"))
    if (manifest.get("status") != STATUS or manifest.get("publication_allowed") is not False):
        raise ValueError("Atlas is not a technical-only reviewed snapshot")
    expected = manifest.get("output_sha256")
    if not isinstance(expected, dict) or not expected or "atlas_data.json" not in expected:
        raise ValueError("Atlas manifest lacks output checksums")
    for relative, digest in expected.items():
        if (not isinstance(relative, str) or not relative or "\\" in relative
                or PurePosixPath(relative).is_absolute()
                or any(part in (".", "..") for part in PurePosixPath(relative).parts)):
            raise ValueError("Unsafe path in atlas checksum manifest")
        path = atlas / relative
        if (not path.is_file() or not isinstance(digest, str) or _sha(path) != digest):
            raise ValueError(f"Atlas output integrity mismatch: {relative}")
    if "index.html" not in expected:
        raise ValueError("Atlas HTML is not bound to integrity manifest")
    return manifest


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("Invalid observation CSV")
        rows = list(reader)
    if not rows or any(None in r for r in rows):
        raise ValueError("Empty or malformed observations")
    if len({(r["municipality_code"], r["indicator_id"]) for r in rows}) != len(rows):
        raise ValueError("Duplicate observation in export")
    if any(r.get("publication_allowed") != "false" for r in rows):
        raise ValueError("Unapproved observation required")
    return rows


def _format_row(r: dict[str, str]) -> tuple[str, str, str, str, str]:
    value = r["value"]
    display_value = (
        "non acquisito" if r["missing_reason"] == "not_acquired"
        else "dato non disponibile" if r["missing_reason"] else value + (" " + r["unit"] if value else "")
    )
    if r["missing_reason"] == "not_acquired" and value:
        raise ValueError("Pending observation unexpectedly has a value")
    counts = (r["numerator"] + " / " + r["denominator"]
              if r["numerator"] and r["denominator"] else "—")
    return (r["municipality"], r["municipality_code"], r["reference_period"] or "—",
            display_value, counts)


def _html(rows: list[dict[str, str]], metrics: list[dict]) -> str:
    payload = {
        "status": STATUS, "publication_allowed": False, "indicators": metrics,
        "rows": [{**r, "display": _format_row(r)} for r in rows],
    }
    safe = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), allow_nan=False)
    safe = safe.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return """<!doctype html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>EPAH v0.4 | Fascicolo tecnico</title><style>
:root{font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:#183448;background:#f2f6f7}
body{margin:0}header{background:#17364b;color:white;padding:28px max(20px,calc((100vw - 1150px)/2))}
main{max-width:1150px;margin:18px auto;padding:0 20px 50px}
header h1{font-size:clamp(1.6rem,3vw,2.5rem);margin:0 0 6px}
article{background:white;border:1px solid #d3e1e7;border-radius:10px;padding:20px;margin:18px 0}
.controls{display:grid;grid-template-columns:1fr 1fr;gap:14px}
label{display:block;font-weight:650;margin-bottom:4px}
select,input{font:inherit;width:100%;box-sizing:border-box;padding:10px;border:1px solid #93aeba;border-radius:5px}
table{border-collapse:collapse;width:100%;font-size:.89rem}th,td{padding:9px 7px;text-align:left;border-bottom:1px solid #e0e9ed}
th{position:sticky;top:0;background:#eaf1f4}td:last-child{text-align:right}
.wrapper{max-height:660px;overflow:auto}small,.note{color:#526a77}.notice{border-left:4px solid #866c41;padding:9px 12px;background:#f8f4ed}
@media(max-width:700px){.controls{grid-template-columns:1fr}.wrapper{overflow:auto}table{min-width:680px}}
@media print{header{background:white;color:#183448}.controls{display:none}.wrapper{max-height:none;overflow:visible}}
</style></head><body>
<header><h1>Fascicolo territoriale v0.4</h1><p>27 Comuni | confronto descrittivo | revisione tecnica</p></header>
<main><article><p class="notice"><strong>BOZZA TECNICA - NON PUBBLICARE.</strong>
 Non misura la povertà energetica domestica, non determina priorità sociali e non autorizza la diffusione.
 Fonti, universi e anni possono essere eterogenei.</p><p class="note">I dati sono riportati senza
 ranghi o punteggi. Conteggi assenti non significano zero. Per mappe e grafici usare l'atlante
 originale, verificando il manifest di provenienza.</p></article>
<article><div class="controls"><div><label for="metric">Indicatore</label><select id="metric"></select></div>
<div><label for="query">Cerca Comune o codice ISTAT</label><input id="query" type="search"></div></div>
<p id="source" class="note"></p><p id="count" aria-live="polite"></p></article>
<article><div class="wrapper"><table><thead><tr><th>Comune</th><th>ISTAT</th><th>Periodo</th>
<th>Valore</th><th>Numeratore / denominatore</th></tr></thead><tbody id="rows"></tbody></table></div></article>
<p class="note">Metadati e SHA-256: metadata.json e manifest.json. Dati: observations.csv.
 Nessuna inferenza individuale o misura EPAH certificata.</p></main>
<script type="application/json" id="payload">__DATA__</script><script>
"use strict";const data=JSON.parse(document.getElementById("payload").textContent);
const metric=document.getElementById("metric"),query=document.getElementById("query");
for(const m of data.indicators){const option=document.createElement("option");
 option.value=m.indicator_id;option.textContent=m.indicator_id+" | "+m.name;
 metric.append(option)}
function redraw(){const m=data.indicators.find(x=>x.indicator_id===metric.value);
 const source=document.getElementById("source");source.textContent=m.source+
 " | "+(m.available?"serie disponibile":"DATI ASSENTI")+
 " | periodi: "+(m.reference_periods.join(", ")||"non acquisiti");
 const q=query.value.trim().toLocaleLowerCase("it-IT");
 const target=document.getElementById("rows");target.replaceChildren();
 let count=0;for(const r of data.rows){if(r.indicator_id!==m.indicator_id)continue;
 if(q&&!r.municipality.toLocaleLowerCase("it-IT").includes(q)&&!r.municipality_code.includes(q))continue;
 const tr=document.createElement("tr");for(const v of r.display){
 const td=document.createElement("td");td.textContent=v;tr.append(td)}
 target.append(tr);count++}document.getElementById("count").textContent=count+" / 27 Comuni"}
metric.addEventListener("change",redraw);query.addEventListener("input",redraw);redraw();
</script></body></html>""".replace("__DATA__", safe)


def _pdf(path: Path, rows: list[dict[str, str]], metrics: list[dict]) -> None:
    document = SimpleDocTemplate(str(path), pagesize=landscape(A4),
                                 leftMargin=32, rightMargin=32, topMargin=38, bottomMargin=35,
                                 title="EPAH v0.4 - Fascicolo tecnico non pubblicabile")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="EPAHNote", parent=styles["Normal"], fontSize=8.4, leading=12))
    styles.add(ParagraphStyle(name="EPAHCell", parent=styles["Normal"], fontSize=7, leading=8.5))
    story = [
        Paragraph("Fascicolo territoriale v0.4", styles["Title"]),
        Spacer(1, 10),
        Paragraph(pdf_escape(NOTICE), styles["Heading3"]),
        Spacer(1, 8),
        Paragraph("27 Comuni. Confronti descrittivi senza punteggi, soglie di rischio "
                  "o graduatorie di povertà energetica.", styles["Normal"]),
        Spacer(1, 14),
        Paragraph("Lo stesso CSV verificato alimenta questa stampa e la vista HTML. "
                  "I valori mancanti non vengono sostituiti con zero. "
                  "Gli universi statistici e i periodi dei diversi indicatori "
                  "non sono necessariamente confrontabili.", styles["Normal"]),
        Spacer(1, 12),
        Paragraph("Provenienza: atlas_data.json, atlas_manifest.json, "
                  "observations.csv e manifest.json. "
                  "Le verifiche automatiche non sostituiscono la revisione scientifica.", styles["EPAHNote"]),
    ]
    for metric in metrics:
        selected = [r for r in rows if r["indicator_id"] == metric["indicator_id"]]
        if len(selected) != 27:
            raise ValueError(f"Incomplete indicator table: {metric['indicator_id']}")
        story.append(PageBreak())
        story.append(Paragraph(pdf_escape(metric["indicator_id"] + " | " + metric["name"]), styles["Heading2"]))
        story.append(Paragraph(pdf_escape("Fonte: " + metric["source"]), styles["EPAHNote"]))
        story.append(Paragraph(pdf_escape(
            "Unità: " + metric["unit"] + " | Periodo: " +
            (", ".join(metric["reference_periods"]) if metric["reference_periods"] else "non acquisito")
            + " | Stato: " + ("anteprima tecnica" if metric["available"] else "DATI ASSENTI")),
            styles["EPAHNote"]))
        story.append(Spacer(1, 9))
        header = ["Comune", "ISTAT", "Periodo", "Valore", "N / D"]
        entries = [[Paragraph(pdf_escape(v), styles["EPAHCell"]) for v in header]]
        for row in selected:
            entries.append([Paragraph(pdf_escape(str(v)), styles["EPAHCell"])
                            for v in _format_row(row)])
        table = Table(entries, repeatRows=1, colWidths=[230, 72, 74, 160, 230], hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#DDE9EF")),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ("TOPPADDING", (0,0), (-1,-1), 3),
            ("LINEBELOW", (0,0), (-1,-1), .25, colors.HexColor("#CDDCE2")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F6F8FA")]),
        ]))
        story.append(table)
        story.append(Spacer(1, 8))
        story.append(Paragraph(pdf_escape(NOTICE), styles["EPAHNote"]))
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.drawString(32, 18, "EPAH Diagnosis | Uso interno | Dati tecnici, non pubblicabili")
        canvas.drawRightString(landscape(A4)[0] - 32, 18, str(doc.page))
        canvas.restoreState()
    document.build(story, onFirstPage=footer, onLaterPages=footer)


def build(atlas_dir: Path, registry: Path, out_dir: Path) -> Path:
    if out_dir.exists():
        raise FileExistsError("Choose a fresh v0.4 review-pack destination")
    if out_dir.resolve().is_relative_to(atlas_dir.resolve()):
        raise ValueError("Review pack cannot overwrite or nest into original atlas")
    _verified_atlas_files(atlas_dir)
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".epah-v04-review-", dir=out_dir.parent) as temporary:
        work = Path(temporary)
        raw_dir = work / "observations"
        export_observations(atlas_dir, registry, raw_dir)
        metadata = json.loads((raw_dir / "metadata.json").read_text(encoding="utf-8"))
        rows = _read_rows(raw_dir / "observations.csv")
        if (len(rows) != len(metadata["indicators"]) * 27
                or metadata.get("publication_allowed") is not False):
            raise ValueError("Observation export and metadata disagree")
        # Preserve metric order from the verified original atlas, not lexical rank.
        by_id = {r["indicator_id"]: r for r in rows}
        metrics = []
        for metric in metadata["indicators"]:
            id_ = metric["indicator_id"]
            obs = by_id[id_]
            metrics.append({**metric, "name": obs["indicator_name"],
                            "source": obs["source"], "unit": obs["unit"]})
        stage = work / "review"
        stage.mkdir()
        shutil.copy2(raw_dir / "observations.csv", stage / "observations.csv")
        shutil.copy2(raw_dir / "metadata.json", stage / "metadata.json")
        shutil.copy2(raw_dir / "manifest.json", stage / "observations_manifest.json")
        (stage / "review.html").write_text(_html(rows, metrics), encoding="utf-8")
        _pdf(stage / "review.pdf", rows, metrics)
        (stage / "README_REVIEW.txt").write_text(
            "EPAH v0.4 TECHNICAL REPORT - NOT FOR PUBLICATION\n"
            "review.html, observations.csv and review.pdf are generated from the same validated observations.\n"
            "For the territorial maps open the original atlas index.html. Review sources and geometry first.\n"
            "Missing data is never zero; no poverty prevalence, rankings or scientific approval.\n",
            encoding="utf-8")
        receipt = {
            "schema_version": "0.4-technical-review-pack", "status": STATUS,
            "publication_allowed": False, "scientific_approval": False,
            "municipalities": 27, "indicator_slots": len(metrics),
            "reference_atlas_sha256": {
                "atlas_data.json": _sha(atlas_dir / "atlas_data.json"),
                "atlas_manifest.json": _sha(atlas_dir / "atlas_manifest.json"),
                "municipalities.csv": _sha(registry),
            },
            "outputs_sha256": {p.name: _sha(p) for p in stage.iterdir() if p.is_file()},
        }
        (stage / "manifest.json").write_text(
            json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if out_dir.exists():
            raise FileExistsError("Concurrent review pack output exists")
        os.replace(stage, out_dir)
    return out_dir
