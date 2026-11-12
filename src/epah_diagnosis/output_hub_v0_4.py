"""Package an unchanged verified v0.4 atlas and review pack for offline readers.

The atlas is the primary interface; the portal also links to a short two-page
orientation PDF, full technical PDF, browsable observations and CSV/metadata.
Nothing here estimates energy poverty, validates source science or publishes data.
"""
from __future__ import annotations

import csv
import hashlib
from html import escape as html_escape
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
from xml.sax.saxutils import escape as xml_escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

from epah_diagnosis.review_pack_v0_4 import STATUS, _verified_atlas_files

COLOR_INK = colors.HexColor("#17354a")
COLOR_MUTED = colors.HexColor("#506577")
COLOR_ACCENT = colors.HexColor("#277b89")
COLOR_RULE = colors.HexColor("#d9e4e8")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def _safe_input_files(folder: Path, names: set[str]) -> None:
    files = set()
    for item in folder.rglob("*"):
        if item.is_symlink():
            raise ValueError("Source tree contains a symlink; refusing to package external files")
        if item.is_file():
            relative = item.relative_to(folder).as_posix()
            files.add(relative)
    if files != names:
        raise ValueError(f"Unexpected or missing source artifacts: {sorted(files ^ names)[:5]}")


def _verify_review(atlas: Path, review: Path, atlas_payload: dict) -> tuple[dict, dict]:
    atlas_sha = sha(atlas / "atlas_data.json")
    atlas_manifest_sha = sha(atlas / "atlas_manifest.json")
    receipt = _load(review / "manifest.json")
    if (receipt.get("status") != STATUS or receipt.get("publication_allowed") is not False
            or receipt.get("scientific_approval") is not False):
        raise ValueError("Review pack is not explicitly unpublished")
    bound = receipt.get("reference_atlas_sha256")
    if (not isinstance(bound, dict) or bound.get("atlas_data.json") != atlas_sha
            or bound.get("atlas_manifest.json") != atlas_manifest_sha):
        raise ValueError("Review pack was built from a different atlas")
    hashes = receipt.get("outputs_sha256")
    if not isinstance(hashes, dict) or not hashes:
        raise ValueError("Review pack is missing an integrity manifest")
    required = {
        "review.html", "review.pdf", "observations.csv", "metadata.json",
        "observations_manifest.json", "README_REVIEW.txt",
    }
    if not required <= set(hashes):
        raise ValueError("Required review artifacts are missing from manifest")
    for name, expected in hashes.items():
        parsed = PurePosixPath(name)
        if (not isinstance(name, str) or not name or "\\" in name
                or parsed.is_absolute() or len(parsed.parts) != 1
                or any(part in {".", ".."} for part in parsed.parts)):
            raise ValueError("Unsafe review manifest path")
        if (not re.fullmatch("[a-f0-9]{64}", str(expected))
                or not (review / name).is_file() or sha(review / name) != expected):
            raise ValueError(f"Review pack checksum mismatch: {name}")
    _safe_input_files(review, set(hashes) | {"manifest.json"})
    meta = _load(review / "metadata.json")
    if (meta.get("status") != STATUS or meta.get("publication_allowed") is not False
            or meta.get("scientific_approval") is not False or meta.get("municipalities") != 27):
        raise ValueError("Invalid review metadata")
    from_atlas = atlas_payload["indicators"]
    from_review = meta.get("indicators")
    if not isinstance(from_review, list) or len(from_review) != len(from_atlas):
        raise ValueError("Atlas and review indicator inventories differ")
    for a, r in zip(from_atlas, from_review):
        if (a.get("id") != r.get("indicator_id") or a.get("available") is not r.get("available")
                or a.get("count") != r.get("municipalities")
                or a.get("years") != r.get("reference_periods")):
            raise ValueError("Atlas and review indicator metadata differ")
    with (review / "observations.csv").open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        observations = list(reader)
    if (len(observations) != 27 * len(from_atlas)
            or meta.get("observations") != len(observations)
            or any(r.get("publication_allowed") != "false" for r in observations)):
        raise ValueError("Review observations have inconsistent coverage or status")
    return receipt, meta


def _validate_inputs(atlas: Path, review: Path) -> tuple[dict, dict]:
    manifest = _verified_atlas_files(atlas)
    payload = _load(atlas / "atlas_data.json")
    if (payload.get("status") != STATUS or payload.get("publication_allowed") is not False
            or payload.get("no_composite_score") is not True
            or payload.get("municipality_count") != 27
            or manifest.get("no_composite_score") is not True
            or manifest.get("municipalities") != 27):
        raise ValueError("Atlas cannot be represented as an unpublished 27-municipality snapshot")
    metrics = payload.get("indicators")
    if not isinstance(metrics, list) or not metrics:
        raise ValueError("Missing atlas indicator inventory")
    available = [m["id"] for m in metrics if m.get("available") is True]
    pending = [m["id"] for m in metrics if m.get("available") is False]
    if (len(available) + len(pending) != len(metrics)
            or manifest.get("indicator_slots") != len(metrics)
            or manifest.get("indicators_available") != available
            or manifest.get("indicators_pending") != pending
            or len({m["id"] for m in metrics}) != len(metrics)):
        raise ValueError("Atlas available and pending inventory inconsistent")
    hashes = manifest["output_sha256"]
    _safe_input_files(atlas, set(hashes) | {"atlas_manifest.json", "README_REVIEW.txt"})
    _, review_meta = _verify_review(atlas, review, payload)
    return payload, review_meta


def _paragraph(text: str, *, size: float = 10, leading: float = 15,
               color: colors.Color = COLOR_INK, bold: bool = False) -> Paragraph:
    return Paragraph(
        xml_escape(text),
        ParagraphStyle(
            name="Brief",
            fontName="Helvetica-Bold" if bold else "Helvetica",
            fontSize=size, leading=leading, textColor=color,
        ),
    )


def _draw_paragraph(c: canvas.Canvas, text: str, x: float, top: float,
                    width: float, **kwargs) -> float:
    paragraph = _paragraph(text, **kwargs)
    _, height = paragraph.wrap(width, 900)
    paragraph.drawOn(c, x, top - height)
    return top - height


def _brief(path: Path, metrics: list[dict]) -> None:
    """Two-page A4 decision-navigation brief, with no municipal value or ranking."""
    width, height = A4
    c = canvas.Canvas(str(path), pagesize=A4, pageCompression=1)
    c.setTitle("EPAH v0.4 - Sintesi tecnica per amministratori (non pubblicabile)")
    available = [m for m in metrics if m["available"]]
    pending = [m for m in metrics if not m["available"]]
    def frame(page: int):
        c.setStrokeColor(COLOR_RULE)
        c.line(43, 43, width - 43, 43)
        c.setFillColor(COLOR_MUTED)
        c.setFont("Helvetica", 8.5)
        c.drawString(43, 29, "EPAH Diagnosis  |  Uso interno, revisione tecnica")
        c.drawRightString(width - 43, 29, f"{page} / 2")
        c.setFillColor(COLOR_ACCENT)
        c.rect(43, height - 52, 45, 5, fill=1, stroke=0)

    frame(1)
    top = height - 90
    top = _draw_paragraph(c, "EPAH Diagnosis | Atlante territoriale v0.4", 43, top,
                          width - 86, size=20, leading=25, bold=True) - 13
    top = _draw_paragraph(c, "Sintesi di orientamento per tecnici e amministratori locali",
                          43, top, width - 86, size=12, leading=17, color=COLOR_MUTED) - 24
    for label, value, x in (
        ("Comuni", "27", 43),
        ("Indicatori previsti", str(len(metrics)), 215),
        ("Anteprime disponibili", str(len(available)), 393),
    ):
        c.setFillColor(COLOR_RULE)
        c.roundRect(x, top - 77, 153, 77, 9, fill=1, stroke=0)
        c.setFillColor(COLOR_INK)
        c.setFont("Helvetica-Bold", 25)
        c.drawString(x + 13, top - 38, value)
        c.setFont("Helvetica", 8.6)
        c.drawString(x + 13, top - 58, label)
    top -= 112
    for heading, body in [
        ("A cosa serve", "Esplorare caratteristiche del territorio, consultare le serie disponibili e identificare i dati da approfondire. Non stima il numero di famiglie in povertà energetica."),
        ("Come usare i risultati", "1. Aprire l'atlante HTML. 2. Controllare anno, unità, fonte e significato di ogni indicatore. 3. Consultare le tabelle e il rapporto tecnico prima di formulare ipotesi operative."),
        ("Quali dati non ci sono", f"{len(pending)} indicatori sono assenti dallo snapshot. Un dato non acquisito non vale zero. Le anteprime disponibili non costituiscono approvazione scientifica."),
        ("Limite della diagnosi", "Il confronto fra proxy territoriali non misura automaticamente disagio energetico, spesa familiare o effetti causali. Non utilizzare il fascicolo per graduatorie o assegnazioni automatiche."),
    ]:
        top = _draw_paragraph(c, heading, 43, top, width - 86, size=12, bold=True) - 5
        top = _draw_paragraph(c, body, 43, top, width - 86, size=9.8, leading=14) - 18
    if top < 68:
        raise ValueError("Brief introduction is too dense for one A4 page")
    c.setFillColor(COLOR_MUTED)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(43, 72, "BOZZA TECNICA - NON PUBBLICARE")
    c.showPage()

    frame(2)
    top = height - 92
    top = _draw_paragraph(c, "Inventario delle evidenze", 43, top, width - 86,
                          size=18, leading=23, bold=True) - 10
    top = _draw_paragraph(c,
        "Disponibile significa visualizzato nell'atlante tecnico, non validato per la pubblicazione.",
        43, top, width - 86, size=9.5, color=COLOR_MUTED) - 18
    rows_per_column = math.ceil(len(metrics) / 2)
    if rows_per_column > 10:
        raise ValueError("Too many indicators for a two-page brief")
    col_width = (width - 101) / 2
    row_height = min(61, (top - 112) / rows_per_column)
    for i, metric in enumerate(metrics):
        col, row = divmod(i, rows_per_column)
        x = 43 + col * (col_width + 15)
        y = top - row * row_height
        if not isinstance(metric.get("id"), str) or not isinstance(metric.get("name"), str):
            raise ValueError("Malformed atlas indicator label")
        title = metric["id"] + " - " + metric["name"]
        bottom = _draw_paragraph(c, title, x, y, col_width - 6,
                                 size=8.4, leading=10.8, bold=True) - 4
        period = ", ".join(metric.get("years", [])) if metric["available"] else ""
        status = ("Anteprima tecnica  |  " + period if metric["available"]
                  else "Non acquisito")
        bottom = _draw_paragraph(c, status, x, bottom, col_width - 6,
                                 size=8, leading=10, color=COLOR_MUTED)
        if bottom < y - row_height + 3:
            raise ValueError("Indicator title does not fit the two-page brief")
        c.setStrokeColor(COLOR_RULE)
        c.line(x, y - row_height + 2, x + col_width - 8, y - row_height + 2)
    c.setFont("Helvetica-Bold", 9.2)
    c.setFillColor(COLOR_INK)
    c.drawString(43, 76, "Consultare i manifest e gli originali prima di qualsiasi uso istituzionale.")
    c.setFont("Helvetica-Bold", 9)
    c.drawString(43, 60, "BOZZA TECNICA - NON PUBBLICARE")
    c.showPage()
    c.save()


def _portal(metrics: list[dict]) -> str:
    available = sum(m["available"] for m in metrics)
    pending = len(metrics) - available
    return """<!doctype html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>EPAH Diagnosis | Output integrati v0.4</title>
<style>
:root{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;color:#17354a;background:#f3f7f8}
*{box-sizing:border-box}body{margin:0;line-height:1.55}
.skip{position:absolute;left:-9999px;top:6px;background:white;padding:9px}
.skip:focus{left:12px}header{background:#17354a;color:white;padding:38px max(20px,calc((100vw - 1000px)/2))}
header h1{font-size:clamp(1.65rem,3vw,2.45rem);margin:0 0 8px}header p{max-width:780px}
main{max-width:1040px;margin:auto;padding:20px}
.note{border-left:4px solid #ae8050;background:#fff9ee;padding:15px 18px;border-radius:3px}
.summary{display:flex;gap:15px;flex-wrap:wrap;margin:25px 0}
.summary div{background:white;border:1px solid #d9e4e8;border-radius:8px;padding:12px 20px}
.summary strong{display:block;font-size:1.8rem}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:15px}
article{background:white;border:1px solid #d9e4e8;border-radius:10px;padding:20px}
article h2{font-size:1.2rem;margin:0 0 8px}article p{margin:0 0 12px}
a{color:#0f5a6f;text-decoration-thickness:1.5px;text-underline-offset:3px}
a:focus-visible{outline:3px solid #c77d32;outline-offset:4px}
ul{margin:8px 0 0;padding-left:21px}li{margin-bottom:7px}
footer{color:#546978;padding:20px 0;font-size:.88rem}
@media print{header{color:#17354a;background:white}.cards{display:block}article{break-inside:avoid;margin-bottom:12px}}
</style></head><body>
<a class="skip" href="#contenuti">Vai ai contenuti</a>
<header><h1>EPAH Diagnosis · Sinergie in Canavese</h1>
<p>Atlante e documentazione tecnica v0.4 · 27 Comuni · Uso interno</p></header>
<main id="contenuti">
<p class="note"><strong>BOZZA TECNICA - NON PUBBLICARE.</strong> Indicatori territoriali descrittivi, non
misure certificate della povertà energetica delle famiglie. Dati mancanti non equivalgono a zero.</p>
<div class="summary" aria-label="Stato degli indicatori">
<div><strong>27</strong>Comuni</div>
<div><strong>__AVAILABLE__</strong>Serie disponibili come anteprima</div>
<div><strong>__PENDING__</strong>Serie non acquisite</div></div>
<section class="cards" aria-label="Apri gli output">
<article><h2>1 · Atlante interattivo</h2>
<p>Mappe, indicatori e grafici per esplorare il territorio. Verificare sempre fonte, anno, universo e limiti.</p>
<p><a href="atlas/index.html">Apri l'atlante HTML</a></p></article>
<article><h2>2 · Rapporto e sintesi</h2>
<p>Per amministratori: breve guida di due pagine e fascicolo tecnico con tutte le serie e i Comuni.</p>
<ul><li><a href="sintesi.pdf">Leggi la sintesi PDF (2 pagine)</a></li>
<li><a href="review/review.pdf">Apri il rapporto tecnico PDF</a></li>
<li><a href="review/review.html">Consulta le tabelle HTML</a></li></ul></article>
<article><h2>3 · Dati, provenienza e audit</h2>
<p>CSV, indicatori, periodi e metadati esattamente collegati allo snapshot originale.</p>
<ul><li><a href="review/observations.csv">Osservazioni CSV</a></li>
<li><a href="review/metadata.json">Metadati delle osservazioni</a></li>
<li><a href="manifest.json">Manifest SHA-256 del pacchetto</a></li></ul></article>
</section>
<footer><p>I file dell'atlante e del fascicolo sono copie integre di input tecnici verificati.
La sintesi non aggiunge valori, punteggi o approvazioni. Per la pubblicazione è necessaria
una revisione scientifica e istituzionale separata.</p></footer></main></body></html>""".replace(
        "__AVAILABLE__", str(available)).replace("__PENDING__", str(pending))


def build(atlas_dir: Path, review_dir: Path, out_dir: Path) -> Path:
    if out_dir.exists():
        raise FileExistsError("Choose a new output directory; no overwrite allowed")
    for source in (atlas_dir, review_dir):
        if (out_dir.resolve().is_relative_to(source.resolve())
                or source.resolve().is_relative_to(out_dir.resolve())):
            raise ValueError("Output must be separate from atlas and review input directories")
    payload, _ = _validate_inputs(atlas_dir, review_dir)
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".epah-v04-hub-", dir=out_dir.parent) as temp:
        stage = Path(temp) / "portal"
        stage.mkdir()
        shutil.copytree(atlas_dir, stage / "atlas")
        shutil.copytree(review_dir, stage / "review")
        for dirname, original in (("atlas", atlas_dir), ("review", review_dir)):
            for source in original.rglob("*"):
                if source.is_file():
                    relative = source.relative_to(original)
                    if sha(stage / dirname / relative) != sha(source):
                        raise ValueError("Source changed during output packaging")
        (stage / "index.html").write_text(_portal(payload["indicators"]), encoding="utf-8")
        _brief(stage / "sintesi.pdf", payload["indicators"])
        (stage / "README_REVIEW.txt").write_text(
            "EPAH v0.4 | OUTPUT INTEGRATI | BOZZA TECNICA - NON PUBBLICARE\n"
            "Aprire index.html; atlante in atlas/, rapporto e dati in review/.\n"
            "sintesi.pdf e un documento orientativo di due pagine, senza misure comunali.\n"
            "La CI verifica il software e l'integrita dei file, non approva le fonti territoriali.\n",
            encoding="utf-8",
        )
        files = {p.relative_to(stage).as_posix(): sha(p)
                 for p in sorted(stage.rglob("*")) if p.is_file()}
        receipt = {
            "schema_version": "0.4-technical-output-hub",
            "status": STATUS,
            "publication_allowed": False, "scientific_approval": False,
            "no_composite_score": True, "municipalities": 27,
            "indicator_slots": len(payload["indicators"]),
            "indicators_available": [m["id"] for m in payload["indicators"] if m["available"]],
            "indicators_pending": [m["id"] for m in payload["indicators"] if not m["available"]],
            "atlas_data_sha256": sha(atlas_dir / "atlas_data.json"),
            "atlas_manifest_sha256": sha(atlas_dir / "atlas_manifest.json"),
            "review_manifest_sha256": sha(review_dir / "manifest.json"),
            "outputs_sha256": files,
        }
        (stage / "manifest.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
        if out_dir.exists():
            raise FileExistsError("Concurrent output already exists")
        os.replace(stage, out_dir)
    return out_dir
