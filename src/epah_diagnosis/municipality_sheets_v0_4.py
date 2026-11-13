"""Two-page A4 municipal briefs generated from ONE checked v0.4 review snapshot.

A brief is a technical navigation aid: it never ranks municipalities, assigns
energy-poverty severity, imputes missing data or grants publication approval.
The same verified observations that feed HTML/CSV/PDF feed all 27 sheets.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import csv
from decimal import Decimal, InvalidOperation
from html import escape as html_escape
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from xml.sax.saxutils import escape as xml_escape

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, TextStringObject
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

from epah_diagnosis.review_pack_v0_4 import STATUS, _sha
from epah_diagnosis.editorial_catalog_v0_4 import snapshot
from epah_diagnosis.evidence_ledger_v0_4 import FILES

INK = colors.HexColor("#17354a")
MUTED = colors.HexColor("#536b7a")
ACCENT = colors.HexColor("#277b89")
RULE = colors.HexColor("#d9e4e8")
SURFACE = colors.HexColor("#f1f6f8")
WARNING = "BOZZA TECNICA - NON PUBBLICARE"
WIDTH, HEIGHT = A4


def _para(c: canvas.Canvas, text: str, x: float, y: float, width: float,
          *, size: float = 9, leading: float = 12,
          bold: bool = False, color: colors.Color = INK) -> float:
    style = ParagraphStyle(
        name="sheet", fontName="Helvetica-Bold" if bold else "Helvetica",
        fontSize=size, leading=leading, textColor=color, spaceAfter=0,
    )
    paragraph = Paragraph(xml_escape(str(text)), style)
    _, height = paragraph.wrap(width, 600)
    paragraph.drawOn(c, x, y - height)
    return y - height


def _frame(c: canvas.Canvas, name: str, code: str, page: int) -> float:
    c.setFillColor(INK)
    c.rect(0, HEIGHT - 12, WIDTH, 12, fill=1, stroke=0)
    c.setFillColor(ACCENT)
    c.rect(42, HEIGHT - 54, 43, 4, fill=1, stroke=0)
    c.setFont("Helvetica", 8.4)
    c.setFillColor(MUTED)
    c.drawString(42, HEIGHT - 43, "EPAH DIAGNOSIS  |  SINERGIE IN CANAVESE")
    c.drawRightString(WIDTH - 42, HEIGHT - 43, "PROFILO COMUNALE  v0.4")
    c.setStrokeColor(RULE)
    c.line(42, 55, WIDTH - 42, 55)
    c.setFont("Helvetica", 8.2)
    c.drawString(42, 42, "Uso tecnico interno  |  Analisi descrittiva non approvata")
    c.drawRightString(WIDTH - 42, 42, f"ISTAT {code}  |  {page}/2")
    return HEIGHT - 78


def _read(payload: dict, csv_path: Path) -> tuple[list[dict], list[dict], dict[str, list[dict]]]:
    metrics = payload.get("indicators")
    towns = payload.get("municipalities")
    if not isinstance(metrics, list) or not isinstance(towns, list):
        raise ValueError("Missing atlas indicators or municipality inventory")
    ids = [metric.get("id") for metric in metrics]
    if not ids or len(ids) > 16 or len(ids) != len(set(ids)):
        raise ValueError("The two-page layout supports between 1 and 16 unique indicators")
    if len(towns) != 27 or len({t.get("code") for t in towns}) != 27:
        raise ValueError("Expected 27 unique municipalities in the atlas")
    towns_by_code = {}
    for town in towns:
        code = town.get("code")
        if (not isinstance(code, str) or not re.fullmatch(r"[0-9]{6}", code)
                or not town.get("name") or not isinstance(town.get("values"), dict)):
            raise ValueError("Invalid municipal code, label or atlas observations")
        towns_by_code[code] = town
    with csv_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        required = {
            "indicator_id", "municipality", "municipality_code",
            "indicator_name", "family", "unit", "source", "reference_period",
            "value", "missing_reason", "numerator", "denominator",
            "universe", "publication_allowed",
        }
        if not required <= set(fields) or len(set(fields)) != len(fields):
            raise ValueError("Review CSV has missing or duplicate headers")
        observations = list(reader)
    if len(observations) != 27 * len(metrics) or any(None in row for row in observations):
        raise ValueError("Review CSV is incomplete or malformed")
    by_code: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in observations:
        code, mid = row["municipality_code"], row["indicator_id"]
        if (code not in towns_by_code or mid not in ids or mid in by_code[code]
                or row["municipality"] != towns_by_code[code]["name"]
                or row["publication_allowed"] != "false"):
            raise ValueError("Review CSV contains an unknown, duplicate or approved observation")
        metric = metrics[ids.index(mid)]
        if any(row[key] != metric.get(source_key, "") for key, source_key in (
            ("indicator_name", "name"), ("family", "family"),
            ("unit", "unit"), ("source", "source"),
        )):
            raise ValueError(f"Review and atlas indicator metadata differ for {mid}")
        original = towns_by_code[code]["values"].get(mid)
        if metric.get("available") is True:
            if (not isinstance(original, dict) or not row["value"]
                    or row["missing_reason"] or row["reference_period"] != original.get("year")):
                raise ValueError(f"Available observation mismatch for {code}/{mid}")
            if metric.get("unit") == "categoria":
                if row["value"] != original.get("value"):
                    raise ValueError(f"Categorical observation mismatch for {code}/{mid}")
            else:
                try:
                    read_value = Decimal(row["value"])
                    atlas_value = Decimal(str(original.get("value")))
                except (InvalidOperation, ValueError, TypeError) as exc:
                    raise ValueError(f"Invalid numeric observation for {code}/{mid}") from exc
                if not read_value.is_finite() or read_value != atlas_value:
                    raise ValueError(f"Numeric observation differs from atlas for {code}/{mid}")
        elif metric.get("available") is False:
            if (original is not None or row["value"] or row["reference_period"]
                    or row["missing_reason"] != "not_acquired"):
                raise ValueError(f"Missing observation falsely presented for {code}/{mid}")
        else:
            raise ValueError("Invalid indicator availability status")
        if bool(row["numerator"]) != bool(row["denominator"]):
            raise ValueError("Incomplete observation counts")
        by_code[code][mid] = row
    if any(set(data) != set(ids) for data in by_code.values()) or len(by_code) != 27:
        raise ValueError("Every municipality requires all indicator slots")
    for metric in metrics:
        if (metric.get("count") != (27 if metric.get("available") else 0)
                or metric.get("years") != sorted({by_code[code][metric["id"]]["reference_period"]
                                                   for code in by_code
                                                   if by_code[code][metric["id"]]["reference_period"]})):
            raise ValueError("Review coverage or reference-period inventory mismatch")
    return metrics, sorted(towns, key=lambda t: t["code"]), {
        code: [by_code[code][mid] for mid in ids] for code in towns_by_code
    }


def _shown_value(row: dict) -> str:
    if row["missing_reason"] == "not_acquired":
        return "Non acquisito"
    if row["missing_reason"]:
        return "Dato non disponibile"
    return row["value"] + (" " + row["unit"] if row["unit"] else "")


def _draw_page_one(c: canvas.Canvas, town: dict, metrics: list[dict],
                   records: list[dict]) -> None:
    name, code = town["name"], town["code"]
    top = _frame(c, name, code, 1)
    top = _para(c, name, 42, top, WIDTH - 84, size=19.5, leading=24, bold=True) - 5
    top = _para(c, f"Comune ISTAT {code}  |  Profilo descrittivo del territorio",
                42, top, WIDTH - 84, size=10.2, color=MUTED) - 20
    available = [r for r in records if not r["missing_reason"]]
    pending = len(records) - len(available)
    for idx, (number, label) in enumerate((
        (len(records), "Indicatori previsti"),
        (len(available), "Anteprime presenti"),
        (pending, "Serie non acquisite"),
    )):
        x = 42 + idx * 174
        c.setFillColor(SURFACE)
        c.roundRect(x, top - 68, 162, 68, 8, fill=1, stroke=0)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 22)
        c.drawString(x + 13, top - 34, str(number))
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 8.6)
        c.drawString(x + 13, top - 53, label)
    top -= 91
    top = _para(c, "Osservazioni disponibili", 42, top, WIDTH - 84,
                size=12, leading=16, bold=True) - 8
    top = _para(c, "Prime sei serie per ordine di catalogo, non una graduatoria.",
                42, top, WIDTH - 84, size=8.7, leading=11, color=MUTED) - 7
    if not available:
        top = _para(c, "Nessun valore comunale acquisito nello snapshot tecnico.",
                    42, top, WIDTH - 84, size=10, leading=14) - 20
    else:
        for row in available[:6]:
            start = top
            left = row["indicator_id"] + "  |  " + row["indicator_name"]
            bottom_left = _para(c, left, 49, start - 3, 326,
                                size=9.4, leading=12.5, bold=True)
            information = next((m.get("editorial") for m in metrics
                                if m["id"] == row["indicator_id"]), None)
            if information:
                bottom_left = _para(
                    c, "Universo: " + information["short_population_reference"],
                    49, bottom_left - 1, 326, size=7.4, leading=9.2, color=MUTED)
            bottom_right = _para(c, _shown_value(row), 391, start - 3, 160,
                                 size=10.3, leading=13, bold=True)
            bottom_right = _para(c, row["reference_period"], 391, bottom_right - 3,
                                 160, size=8.5, leading=10, color=MUTED)
            if min(bottom_left, bottom_right) < start - 41:
                raise ValueError(f"Label too long for page-one preview: {row['indicator_id']}")
            c.setStrokeColor(RULE)
            c.line(42, start - 46, WIDTH - 42, start - 46)
            top -= 49
    if top < 201:
        raise ValueError("Page-one observations exceed available A4 space")
    top -= 13
    top = _para(c, "Criteri di lettura", 42, top, WIDTH - 84,
                size=12, leading=16, bold=True) - 6
    for note in (
        "Fonti, periodi e universi statistici possono differire tra gli indicatori.",
        "Non acquisito non significa zero; nessun dato mancante viene stimato.",
        "Il profilo non misura famiglie in povertà energetica e non determina priorita di intervento.",
    ):
        top = _para(c, "• " + note, 42, top, WIDTH - 84,
                    size=9.0, leading=12.5) - 5
    if top < 80:
        raise ValueError("Page-one scientific notes exceed A4")
    c.setFillColor(MUTED)
    c.setFont("Helvetica-Bold", 8.7)
    c.drawString(42, 70, WARNING)
    c.showPage()


def _draw_page_two(c: canvas.Canvas, town: dict, metrics: list[dict],
                   records: list[dict], *, has_evidence: bool = False) -> None:
    name, code = town["name"], town["code"]
    top = _frame(c, name, code, 2)
    top = _para(c, "Indicatori, fonti e periodi", 42, top, WIDTH - 84,
                size=17.2, leading=22, bold=True) - 4
    top = _para(c, f"{name} ({code})  |  Tutti gli indicatori previsti",
                42, top, WIDTH - 84, size=9.5, leading=12, color=MUTED) - 16
    per_column = (len(records) + 1) // 2
    columns = 2
    width = (WIDTH - 98) / columns
    row_height = min(79, (top - 103) / per_column)
    if row_height < 65:
        raise ValueError("A4 layout cannot accommodate the indicator inventory")
    for i, row in enumerate(records):
        col, pos = divmod(i, per_column)
        x = 42 + col * (width + 14)
        y = top - pos * row_height
        bottom = _para(c, row["indicator_id"] + "  |  " + row["indicator_name"],
                       x + 2, y - 3, width - 11, size=8.6, leading=10.7, bold=True) - 3
        period = row["reference_period"] or "Periodo non acquisito"
        bottom = _para(c, _shown_value(row) + "  |  " + period, x + 2,
                       bottom, width - 11, size=8.2, leading=10.5) - 2
        if row["numerator"]:
            bottom = _para(c, "N / D: " + row["numerator"] + " / " + row["denominator"],
                           x + 2, bottom, width - 11, size=7.3, leading=9.4, color=MUTED) - 1
        bottom = _para(c, "Fonte: " + row["source"], x + 2, bottom,
                       width - 11, size=7.6, leading=9.4, color=MUTED)
        if bottom < y - row_height + 4:
            raise ValueError(f"Indicator exceeds two-page A4 layout: {row['indicator_id']}")
        c.setStrokeColor(RULE)
        c.line(x, y - row_height + 2, x + width - 7, y - row_height + 2)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 8)
    c.drawString(42, 86, "Universi, definizioni e limiti: catalogo_editoriale.json allegato.")
    c.drawString(42, 74, "N / D = numeratore / denominatore, solo se documentati nello snapshot.")
    if has_evidence:
        c.drawString(42, 97, "Provenienza, stato e assenze: evidence_ledger.html / .json allegati.")
        c.linkURL("../evidence_ledger.html", (42, 94, WIDTH - 42, 104), relative=0)
    c.setFont("Helvetica-Bold", 8.7)
    c.drawString(42, 61, WARNING)
    c.showPage()


def _one_pdf(path: Path, town: dict, metrics: list[dict],
             records: list[dict], *, has_evidence: bool = False) -> None:
    c = canvas.Canvas(str(path), pagesize=A4, pageCompression=1)
    c.setTitle(f"EPAH v0.4 - Profilo {town['name']} (non pubblicabile)")
    _draw_page_one(c, town, metrics, records)
    _draw_page_two(c, town, metrics, records, has_evidence=has_evidence)
    c.save()
    if len(PdfReader(str(path)).pages) != 2:
        raise ValueError("Municipal PDF must contain exactly 2 pages")


def _index(towns: list[dict], *, has_catalog: bool = False) -> str:
    links = "\n".join(
        '<li><a href="pdf/' + t["code"] + '.pdf">' +
        html_escape(t["name"], quote=True) + ' <small>ISTAT ' + t["code"] +
        '</small></a></li>' for t in sorted(towns, key=lambda t: t["name"].casefold())
    )
    return """<!doctype html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>EPAH v0.4 | Schede dei 27 Comuni</title>
<style>
:root{font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:#17354a;background:#f4f7f8}
body{margin:0}header{background:#17354a;color:white;padding:28px 5%}
main{max-width:960px;margin:auto;padding:18px}h1{margin:0 0 7px}
p{line-height:1.55}ul{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:10px;padding:0;list-style:none}
li{background:white;border:1px solid #d9e4e8;padding:13px;border-radius:6px}
a{color:#115a70;text-decoration-thickness:1.5px;text-underline-offset:3px}
a:focus-visible{outline:3px solid #bc7035;outline-offset:4px}
small{display:block;color:#526879;margin-top:4px}
.warning{border-left:4px solid #bd854b;background:#fff8eb;padding:14px}
</style></head><body><header><h1>Le 27 schede comunali</h1>
<p>Profili A4 di due pagine · Revisione tecnica v0.4</p></header>
<main><p class="warning"><strong>BOZZA TECNICA - NON PUBBLICARE.</strong>
Questi profili non misurano direttamente la povertà energetica delle famiglie.
Gli indicatori mancanti non equivalgono a zero.</p>
<p><a href="schede_27_comuni.pdf">Scarica il fascicolo unico: 54 pagine</a></p>
<p>Per fonte, metodo e provenienza consultare anche il rapporto tecnico, i CSV
e i manifest del pacchetto integrato.</p>__CATALOG__<ul>__LIST__</ul></main></body></html>""".replace(
    "__LIST__", links).replace(
    "__CATALOG__", '<p><a href="catalogo_editoriale.json">Catalogo editoriale: universi e limiti</a></p>'
    if has_catalog else "")


def render_verified(atlas_payload: dict, review_csv: Path, out_dir: Path,
                    *, atlas_sha256: str, observations_sha256: str,
                    evidence_dir: Path | None = None) -> Path:
    """Render from a validated atlas/review pair into a new staging directory."""
    if out_dir.exists():
        raise FileExistsError("Municipal sheets cannot overwrite an existing directory")
    metrics, towns, per_code = _read(atlas_payload, review_csv)
    catalog = snapshot(metrics)
    out_dir.mkdir(parents=True)
    pdf_dir = out_dir / "pdf"
    pdf_dir.mkdir()
    combined = PdfWriter()
    for town in towns:
        sheet = pdf_dir / (town["code"] + ".pdf")
        _one_pdf(sheet, town, metrics, per_code[town["code"]], has_evidence=evidence_dir is not None)
        combined.append(str(sheet))
        if evidence_dir is not None:
            for annotation in combined.pages[-1].get("/Annots", []):
                action = annotation.get_object().get("/A")
                if action and action.get("/URI") == "../evidence_ledger.html":
                    action[NameObject("/URI")] = TextStringObject("evidence_ledger.html")
    if len(combined.pages) != 54:
        raise ValueError("The combined book must have 54 A4 pages")
    with (out_dir / "schede_27_comuni.pdf").open("wb") as handle:
        combined.write(handle)
    combined.close()
    (out_dir / "catalogo_editoriale.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / "index.html").write_text(
        _index(towns, has_catalog=bool(catalog["indicators"])), encoding="utf-8")
    metadata = {
        "schema_version": "0.4-two-page-sheets",
        "status": STATUS, "scientific_approval": False, "publication_allowed": False,
        "municipalities": 27, "indicator_slots": len(metrics),
        "pages_per_municipality": 2, "combined_book_pages": 54,
        "reference_atlas_data_sha256": atlas_sha256,
        "reference_observations_csv_sha256": observations_sha256,
        "municipality_codes": [t["code"] for t in towns],
        "limitations": [
            "Technical descriptions, not measured household energy-poverty prevalence.",
            "Only the first six available metrics are previewed on page one, in catalog order.",
            "No rank, score, missing value imputation, or source approval.",
            "Visual layout must be reviewed on original territorial inputs before sharing.",
        ],
    }
    if evidence_dir is not None:
        for name in FILES:
            shutil.copy2(evidence_dir / name, out_dir / name)
        metadata["evidence_ledger"] = FILES[0]
        index = out_dir / "index.html"
        index.write_text(index.read_text(encoding="utf-8").replace(
            "</main>", '<p><a href="evidence_ledger.html">Registro delle evidenze</a></p></main>'), encoding="utf-8")
    (out_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    hashes = {p.relative_to(out_dir).as_posix(): _sha(p)
              for p in sorted(out_dir.rglob("*")) if p.is_file()}
    (out_dir / "manifest.json").write_text(
        json.dumps({
            "status": STATUS, "publication_allowed": False,
            "scientific_approval": False, "outputs_sha256": hashes,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out_dir


def build(atlas_dir: Path, review_dir: Path, out_dir: Path) -> Path:
    """Standalone entry point: check the source pair before rendering sheets."""
    if out_dir.exists():
        raise FileExistsError("Choose a new output directory")
    if any(out_dir.resolve().is_relative_to(p.resolve()) or
           p.resolve().is_relative_to(out_dir.resolve())
           for p in (atlas_dir, review_dir)):
        raise ValueError("Outputs must be separate from atlas and review inputs")
    # Local import avoids a cycle with the integrated output hub.
    from epah_diagnosis.output_hub_v0_4 import _validate_inputs
    atlas_payload, _ = _validate_inputs(atlas_dir, review_dir)
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".epah-v04-municipal-", dir=out_dir.parent) as temp:
        stage = Path(temp) / "sheets"
        render_verified(
            atlas_payload, review_dir / "observations.csv", stage,
            atlas_sha256=_sha(atlas_dir / "atlas_data.json"),
            observations_sha256=_sha(review_dir / "observations.csv"),
            evidence_dir=review_dir if (review_dir / FILES[0]).is_file() else None,
        )
        if out_dir.exists():
            raise FileExistsError("Destination appeared concurrently")
        os.replace(stage, out_dir)
    return out_dir
