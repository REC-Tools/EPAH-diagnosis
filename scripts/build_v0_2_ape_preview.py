"""Build an APE-focused v0.2 preview: verified 27-town CSV, map and EPAH-TA PDF.

Only a technical preview. Does not approve residential EP certificates, promote
the canonical 243 records, or certify poverty among households.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import statistics
import tempfile
from collections import Counter
from datetime import date
from html import escape
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer,
    Table, TableStyle,
)

from epah_diagnosis.cartography import render_thematic_map
from epah_diagnosis.geography import parse_boundaries_zip, write_geojson

ROOT = Path(__file__).resolve().parents[1]
QA_DIR = ROOT / "outputs/quality/piemonte_ape_fg_v02"
OUT_DIR = ROOT / "outputs/v0.2.0-ape-preview"
COLS = ("ape_a4", "ape_a3", "ape_a2", "ape_a1", "ape_b",
        "ape_c", "ape_d", "ape_e", "ape_f", "ape_g")
LABELS = ("A4", "A3", "A2", "A1", "B", "C", "D", "E", "F", "G")
TA_CODE = "26-IT-Unione-TA26"
SOURCE_URL = (
    "https://www.dati.gov.it/node/view-dataset/dataset?"
    "id=63401619-1a9f-4382-8399-84c20c59dad0"
)
NAVY = colors.HexColor("#123948")
ORANGE = colors.HexColor("#E5A32E")
GREY = colors.HexColor("#526370")
LIGHT = colors.HexColor("#EAF0F2")


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def load_ape(csv_path: Path, qa_path: Path, registry_path: Path) -> tuple[list[dict], dict]:
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    with registry_path.open(encoding="utf-8-sig", newline="") as file:
        registry_rows = list(csv.DictReader(file))
    expected = {r["istat_code"]: r["municipality"] for r in registry_rows}
    if len(expected) != 27 or len(set(expected.values())) != 27:
        raise ValueError("The registry must have 27 unique municipalities")
    if (qa.get("indicator_id") != "ape_fg_share_all_uses"
            or qa.get("qa_status") != "technical_extraction_only"
            or qa.get("validated_as_residential_share") is not False
            or qa.get("municipalities_matched") != 27
            or qa.get("municipalities_expected") != 27
            or qa.get("source_license") != "CC BY 4.0"
            or qa.get("municipality_registry_sha256") != hash_file(registry_path)
            or qa.get("result_csv_sha256") != hash_file(csv_path)):
        raise ValueError("APE QA metadata, source hash or method scope does not match")
    with csv_path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames or not {"municipality", "istat_code",
                "ape_fg_share_pct", "ape_fg", "ape_total", "snapshot_date",
                "denominator", "scope", *COLS} <= set(reader.fieldnames):
            raise ValueError("APE 27-town CSV schema missing required fields")
        rows = list(reader)
    if len(rows) != 27 or len({r["istat_code"] for r in rows}) != 27:
        raise ValueError("APE CSV must have exactly 27 unique ISTAT codes")
    if {r["istat_code"] for r in rows} != set(expected):
        raise ValueError("APE coverage differs from the 27-town ISTAT registry")
    totals = Counter()
    snapshot = qa.get("snapshot_date")
    try:
        date.fromisoformat(snapshot)
    except (TypeError, ValueError) as exc:
        raise ValueError("Missing or invalid APE snapshot date") from exc
    clean = []
    for row in rows:
        code = row["istat_code"]
        if row["municipality"] != expected[code]:
            raise ValueError("APE municipality name differs from the registry")
        if (row["snapshot_date"] != snapshot or row["denominator"] != "all_ape"
                or row["scope"] != "all_building_uses_not_residential_only"):
            raise ValueError("Source snapshot or non-residential caveat altered")
        try:
            counts = [int(row[field]) for field in COLS]
            number, fg = int(row["ape_total"]), int(row["ape_fg"])
            pct = float(row["ape_fg_share_pct"])
        except (ValueError, TypeError) as exc:
            raise ValueError("Invalid APE numbers") from exc
        if any(k < 0 for k in counts) or number < 1:
            raise ValueError("Invalid/empty APE denominator")
        if number != sum(counts) or fg != counts[8] + counts[9]:
            raise ValueError("APE F/G numerator or denominator inconsistent")
        if not math.isfinite(pct) or abs(pct - (100 * fg / number)) > .011:
            raise ValueError("APE share differs from F/G divided by total certificates")
        for field, value in zip(COLS, counts):
            totals[field] += value
        clean.append({"municipality": row["municipality"], "istat_code": code,
                      "ape_total": number, "ape_fg": fg, "ape_fg_share_pct": pct,
                      "counts": dict(zip(COLS, counts))})
    total = sum(r["ape_total"] for r in clean)
    fg = sum(r["ape_fg"] for r in clean)
    if (total != qa.get("ape_count_27") or fg != qa.get("ape_fg_count_27")
            or abs(100 * fg / total - float(qa.get("pooled_fg_share_pct", -1))) > .011):
        raise ValueError("APE QA aggregation does not reproduce the 27 municipalities")
    return clean, {"snapshot_date": snapshot, "total": total, "fg": fg,
                   "pooled_pct": 100 * fg / total, "totals_by_class": totals,
                   "qa_sha256": hash_file(qa_path),
                   "csv_sha256": hash_file(csv_path),
                   "source_sha256": qa["source_csv_sha256"],
                   "registry_sha256": hash_file(registry_path)}


def enriched_geography(boundary_zip: Path, rows: list[dict]) -> dict:
    expected = {r["municipality"]: r for r in rows}
    geo = parse_boundaries_zip(boundary_zip.read_bytes(), set(expected))
    seen = set()
    for feat in geo["features"]:
        prop = feat["properties"]
        town = prop["municipality"]
        row = expected[town]
        if prop["municipality_code"] != row["istat_code"] or town in seen:
            raise ValueError("ISTAT code mismatch in official 2026 municipality shapes")
        prop["ape_fg_share_pct"] = row["ape_fg_share_pct"]
        prop["ape_total"] = row["ape_total"]
        prop["ape_fg"] = row["ape_fg"]
        # Actual source snapshot is populated by the caller after QA validation.
        prop["ape_denominator"] = "all_ape"
        seen.add(town)
    if len(seen) != 27:
        raise ValueError("Missing municipal geometry")
    return geo


def class_chart(stats: dict, output: Path) -> None:
    counts = [stats["totals_by_class"][k] for k in COLS]
    fig, ax = plt.subplots(figsize=(8.0, 3.0))
    try:
        bar_colors = ["#238785"] * 8 + ["#D48E31"] * 2
        ax.bar(LABELS, counts, color=bar_colors)
        ax.set_ylabel("Attestati registrati (n.)")
        ax.set_title("Distribuzione delle classi energetiche nei 27 Comuni")
        ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout()
        fig.savefig(output, dpi=160, facecolor="white")
    finally:
        plt.close(fig)


def img_fit(path: Path, width: float, max_height: float) -> Image:
    # Original pixel dimensions determine the aspect ratio, never stretch.
    from reportlab.lib.utils import ImageReader
    image = ImageReader(str(path))
    x, y = image.getSize()
    scale = min(width / x, max_height / y)
    return Image(str(path), width=x * scale, height=y * scale)


def build_report(pdf: Path, rows: list[dict], stats: dict, map_png: Path,
                 chart_png: Path, nametag: Path | None = None,
                 relative_map_png: Path | None = None) -> None:
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CoverTitleV2", parent=styles["Title"],
            fontName="Helvetica-Bold", fontSize=23, leading=29,
            textColor=NAVY, spaceAfter=16))
    styles.add(ParagraphStyle(name="HeadV2", parent=styles["Heading2"],
            fontSize=14, leading=18, spaceBefore=12, spaceAfter=8,
            textColor=NAVY))
    styles.add(ParagraphStyle(name="BodyV2", parent=styles["BodyText"],
            fontSize=10, leading=15, spaceAfter=10))
    styles.add(ParagraphStyle(name="SmallV2", parent=styles["BodyText"],
            fontSize=8.6, leading=12.5, spaceAfter=8))
    styles.add(ParagraphStyle(name="NoteV2", parent=styles["BodyText"],
            fontSize=9, leading=13, textColor=GREY, spaceAfter=8))
    styles.add(ParagraphStyle(name="CenterV2", parent=styles["BodyText"],
            fontSize=12, leading=17, alignment=TA_CENTER, textColor=NAVY))

    def para(value: str, style: str = "BodyV2") -> Paragraph:
        return Paragraph(value, styles[style])

    def frame(canvas, document):
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(0, A4[1] - 0.48 * cm, A4[0], 0.48 * cm, stroke=0, fill=1)
        canvas.setFillColor(GREY)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(1.7 * cm, 1.1 * cm, "EPAH Technical Assistance 2026 | " + TA_CODE)
        canvas.drawRightString(A4[0] - 1.7 * cm, 1.1 * cm, str(document.page))
        canvas.restoreState()

    doc = SimpleDocTemplate(str(pdf), pagesize=A4, leftMargin=1.7 * cm,
            rightMargin=1.7 * cm, topMargin=1.7 * cm, bottomMargin=1.8 * cm,
            title="EPAH Diagnosis v0.2 - APE F/G, 27 Comuni (anteprima)",
            author="EPAH Diagnosis - Assistenza Tecnica 26-IT-Unione-TA26")
    story = []
    if nametag is not None:
        if not nametag.is_file():
            raise FileNotFoundError(f"EPAH nametag not found: {nametag}")
        story.extend([img_fit(nametag, 5.7 * cm, 2.0 * cm), Spacer(1, 1.0 * cm)])
    else:
        story.extend([para("EU Energy Poverty Advisory Hub | Technical Assistance",
                           "SmallV2"), Spacer(1, 1.4 * cm)])
    story.extend([
        para("Diagnosi territoriale della vulnerabilita alla poverta energetica",
             "CoverTitleV2"),
        para("FOCUS | Prestazione energetica certificata degli immobili", "CenterV2"),
        Spacer(1, 0.65 * cm),
        para("Green Community Sinergie in Canavese - 27 Comuni", "HeadV2"),
        para("<b>Progetto:</b> " + TA_CODE + "<br/>"
             "<b>Versione:</b> v0.2.0 - anteprima tecnica APE<br/>"
             "<b>Fonte:</b> Regione Piemonte / CSI Piemonte<br/>"
             "<b>Snapshot:</b> " + stats["snapshot_date"], "BodyV2"),
        Spacer(1, 1.4 * cm),
        para("Sviluppato nell'ambito del programma di Assistenza Tecnica EPAH 2026.",
             "BodyV2"),
        para("Documento tecnico di lavoro per il confronto con FERVORES e "
             "l'Unione Montana. Non e una pubblicazione ufficiale della "
             "Commissione europea e non costituisce una validazione EPAH.",
             "NoteV2"),
        PageBreak(),
        para("1. Sintesi dei risultati", "HeadV2"),
        para("Lo screening include esattamente <b>27 Comuni</b>. Il dato descrive "
             "esclusivamente le classi degli attestati presenti nel registro "
             "regionale, senza distinguere la destinazione d'uso.", "BodyV2"),
    ])
    # Transparent pooled weighting: do not average 27 municipal percentages.
    kpi_data = [
        ["Comuni", "APE registrati", "APE F + G", "Quota F/G"],
        ["27", f"{stats['total']:,}".replace(",", "."),
         f"{stats['fg']:,}".replace(",", "."),
         f"{stats['pooled_pct']:.2f}%".replace(".", ",")],
    ]
    table = Table(kpi_data, colWidths=[2.5 * cm, 4.9 * cm, 4.6 * cm, 4.7 * cm],
                  rowHeights=[0.8 * cm, 1.1 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("TEXTCOLOR", (0, 1), (-1, 1), NAVY),
        ("BACKGROUND", (0, 1), (-1, 1), LIGHT),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, 1), 15),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.extend([
        table, Spacer(1, .45 * cm),
        para("Il <b>58,87%</b> non va letto come quota delle abitazioni inefficienti "
             "o famiglie in poverta energetica: il denominatore sono gli APE "
             "effettivamente registrati. La quota aggregata pesa ciascun "
             "Comune per il proprio numero di attestati.", "NoteV2"
             ) if abs(stats["pooled_pct"] - 58.87) < .01 else
        para("La quota aggregata pesa ciascun Comune per il proprio numero di "
             "attestati; non rappresenta le abitazioni o famiglie.", "NoteV2"),
        img_fit(chart_png, 16.5 * cm, 7.3 * cm),
        para("La classe energetica e una misura riferita agli APE disponibili; "
             "i certificati hanno copertura e rappresentativita variabili.",
             "SmallV2"),
        PageBreak(),
        para("2. Mappa: quota di attestati F/G", "HeadV2"),
        para("La geografia mostra soltanto i 27 Comuni, utilizzando confini "
             "ISTAT 2026 e una proiezione metrica (WGS84/UTM32N) per il disegno. "
             "Le percentuali sono per Comune sul totale dei propri APE.",
             "BodyV2"),
        img_fit(map_png, 16 * cm, 16.8 * cm),
        para("Fonte: Regione Piemonte / CSI Piemonte, elaborazione su dati "
             + stats["snapshot_date"] + ". Il valore mappato NON e "
             "la percentuale delle abitazioni comunali in classe F/G.",
             "NoteV2"),
        PageBreak(),
        para("3. Lettura critica e prossimi passi", "HeadV2"),
        para("<b>Definizione:</b> 100 x (APE classe F + classe G) / "
             "APE di tutte le classi A4-G, per ciascun Comune. "
             "Il valore complessivo e calcolato come rapporto fra la somma "
             "degli APE F+G e la somma di tutti gli APE registrati.", "BodyV2"),
        para("<b>Limiti fondamentali</b>", "HeadV2"),
        para("Il CSV non ha una colonna per distinguere uso residenziale e "
             "non residenziale. Gli attestati non coincidono con edifici "
             "unici, alloggi o nuclei familiari. La data di aggiornamento "
             "del dataset non corrisponde necessariamente alla data di "
             "emissione del singolo attestato. In piccoli Comuni i "
             "denominatori ridotti comportano percentuali instabili.",
             "BodyV2"),
    ])
    small = sorted(rows, key=lambda r: (r["ape_total"], r["municipality"]))[:5]
    samples = [["Comune (denominatore ridotto)", "APE (N)", "F/G (%)"]]
    for row in small:
        samples.append([escape(row["municipality"]), str(row["ape_total"]),
                        f"{row['ape_fg_share_pct']:.2f}".replace(".", ",")])
    caution = Table(samples, colWidths=[9.6 * cm, 3.5 * cm, 3.6 * cm], repeatRows=1)
    caution.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 1), (-1, -1), LIGHT),
    ]))
    story.extend([
        para("Esempi di piccoli denominatori (non una classifica di poverta)", "HeadV2"),
        caution, Spacer(1, .4 * cm),
        para("<b>Prossimo passaggio:</b> confrontare questo indicatore con "
             "il patrimonio edilizio storico, le tecnologie di riscaldamento "
             "e i dati socioeconomici. Non creare indici cumulativi o "
             "attribuzioni individuali prima del confronto con i partner.",
             "BodyV2"),
        para("<b>Provenienza e riuso:</b> Regione Piemonte / CSI Piemonte, "
             "dataset APE per classe e Comune, licenza CC BY 4.0. "
             "URL: " + escape(SOURCE_URL), "SmallV2"),
        para("Elaborazione nell'ambito del programma EPAH Technical Assistance "
             "2026 (" + TA_CODE + "). Analisi e interpretazioni degli autori "
             "non rappresentano necessariamente la posizione della "
             "Commissione europea o di EPAH.", "NoteV2"),
    ])
    if relative_map_png is not None:
        # This is a mean of 27 MUNICIPAL percentages, never weighted by APE N.
        town_mean = statistics.fmean(r["ape_fg_share_pct"] for r in rows)
        story.extend([
            PageBreak(),
            para("3. Confronto relativo tra i 27 Comuni", "HeadV2"),
            para("La scala divergente mostra lo scostamento in punti percentuali "
                 "dalla media aritmetica delle 27 quote comunali. "
                 f"<b>Riferimento (grigio): {town_mean:.2f}%</b>. "
                 "Inferiore = verde (situazione relativamente migliore); "
                 "superiore = rosso (situazione relativamente peggiore). "
                 "La media comunale non coincide con la quota aggregata "
                 "ponderata per numero di certificati.", "BodyV2"),
            img_fit(relative_map_png, 16 * cm, 16 * cm),
            para("Questo confronto non identifica famiglie vulnerabili. "
                 "Le differenze su pochi APE possono essere instabili.",
                 "NoteV2"),
        ])
    doc.build(story, onFirstPage=frame, onLaterPages=frame)


def build_preview(source: Path, qa: Path, registry: Path, boundary: Path,
                  destination: Path, nametag: Path | None = None,
                  map_mode: str = "both", relative_unit: str = "auto") -> Path:
    if destination.exists():
        raise FileExistsError("The v0.2 preview already exists; use a new --output-dir")
    rows, stats = load_ape(source, qa, registry)
    if map_mode not in {"absolute", "relative", "both"}:
        raise ValueError("Invalid map_mode: absolute, relative or both")
    if relative_unit not in {"auto", "difference", "percentage_points", "percent_change"}:
        raise ValueError("Invalid relative unit")
    if not boundary.is_file():
        raise FileNotFoundError(f"Official ISTAT municipality boundaries missing: {boundary}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ape_v02-", dir=destination.parent) as temp:
        stage = Path(temp) / "bundle"
        stage.mkdir()
        geojson = enriched_geography(boundary, rows)
        for feat in geojson["features"]:
            feat["properties"]["ape_snapshot_date"] = stats["snapshot_date"]
        write_geojson(geojson, stage / "ape_fg_27_municipalities.geojson")
        absolute_path = stage / "map_ape_fg_share_all_uses.png"
        relative_path = stage / "map_ape_fg_relative_27.png"
        footer = ("Regione Piemonte / CSI | " + stats["snapshot_date"] +
                  " | Tutti gli APE | TA EPAH 2026")
        if map_mode in {"absolute", "both"}:
            render_thematic_map(
                geojson, "ape_fg_share_pct", "APE F/G - scala assoluta",
                "%", absolute_path, mode="absolute", footer=footer,
            )
        if map_mode in {"relative", "both"}:
            render_thematic_map(
                geojson, "ape_fg_share_pct", "APE F/G - differenza dalla media dei 27 Comuni",
                "%", relative_path, mode="relative", direction="higher_is_worse",
                relative_unit=relative_unit, footer=footer,
            )
        chart_path = stage / "chart_ape_classes.png"
        class_chart(stats, chart_path)
        shutil.copyfile(source, stage / "ape_fg_27_municipalities.csv")
        pdf_path = stage / "diagnostic_report_v0_2_ape_preview.pdf"
        main_map = absolute_path if map_mode != "relative" else relative_path
        supplementary = relative_path if map_mode == "both" else None
        build_report(pdf_path, rows, stats, main_map, chart_path, nametag,
                     relative_map_png=supplementary)
        (stage / "README.md").write_text(
            "# Anteprima tecnica v0.2 - APE F/G\n\n"
            "27 Comuni, snapshot " + stats["snapshot_date"] + ".\n"
            "La quota F/G e calcolata su tutti gli APE (destinazioni d'uso "
            "non filtrabili), NON sul patrimonio abitativo.\n"
            "Documento preparatorio all'Assistenza Tecnica EPAH 2026, codice "
            + TA_CODE + ". Non sostituisce la release v0.1.\n",
            encoding="utf-8",
        )
        manifest = {
            "release_track": "v0.2.0_ape_technical_preview",
            "status": "technical_preview_not_institutionally_approved",
            "ta_code": TA_CODE,
            "indicator_id": "ape_fg_share_all_uses",
            "municipalities": 27,
            "snapshot_date": stats["snapshot_date"],
            "denominator": "all_ape_not_residential",
            "registered_apes": stats["total"], "fg_apes": stats["fg"],
            "fg_share_pct": round(stats["pooled_pct"], 2),
            "source_url": SOURCE_URL, "source_license": "CC BY 4.0",
            "original_source_sha256": stats["source_sha256"],
            "prepared_csv_sha256": stats["csv_sha256"],
            "prepared_qa_sha256": stats["qa_sha256"],
            "official_istat_boundaries_sha256": hash_file(boundary),
            "geometry_crs": "OGC:CRS84",
            "map_render_crs": "EPSG:32632",
            "map_mode": map_mode,
            "relative_reference": "unweighted_arithmetic_mean_of_27_municipal_shares",
            "relative_unit": relative_unit,
            "files_sha256": {p.name: hash_file(p) for p in stage.iterdir()
                             if p.is_file() and p.name != "ape_v0_2_manifest.json"},
        }
        (stage / "ape_v0_2_manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        stage.rename(destination)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description="Build APE F/G map + EPAH TA report preview for v0.2")
    parser.add_argument("--ape-csv", type=Path, default=QA_DIR / "ape_fg_27_municipalities.csv")
    parser.add_argument("--ape-qa", type=Path, default=QA_DIR / "ape_fg_qa.json")
    parser.add_argument("--registry", type=Path, default=ROOT / "data/municipalities.csv")
    parser.add_argument("--boundaries-zip", type=Path,
                        default=ROOT / "data/downloads/Limiti01012026_g.zip")
    parser.add_argument("--epah-nametag", type=Path,
                        help="Optional EPAH_Color.png, supplied by EPAH; aspect ratio preserved")
    parser.add_argument("--map-mode", choices=("absolute", "relative", "both"),
                        default="both")
    parser.add_argument("--relative-unit", choices=("auto", "difference",
                        "percentage_points", "percent_change"), default="auto")
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()
    target = build_preview(args.ape_csv, args.ape_qa, args.registry,
                           args.boundaries_zip, args.output_dir, args.epah_nametag,
                           map_mode=args.map_mode, relative_unit=args.relative_unit)
    print("EPAH v0.2 APE technical preview:", target)
    print("27 municipal values; map mode:", args.map_mode,
          "| metric EPSG:32632 | classes chart | EPAH report | SHA manifest")
    print("Scope: ALL registered APE, not residential-only; v0.1 remains unchanged.")


if __name__ == "__main__":
    main()
