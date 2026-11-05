"""One-page municipal factsheets for the v0.2 technical diagnosis.

Uses an already verified 27x9 pilot profile; no new observations or ranks.
"""
from __future__ import annotations

import math
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from epah_diagnosis.report_v0_2 import FIELDS


def render_sheet(path: Path, profile: dict, facts: dict, istat_code: str) -> None:
    """Render a single page; source years and medians are never mixed or scored."""
    if len(istat_code) != 6 or not istat_code.isascii() or not istat_code.isdigit():
        raise ValueError("Six-digit ISTAT code required")
    if facts.get("municipalities") != 27 or len(facts.get("indicators", {})) != 8:
        raise ValueError("Complete municipal fact metadata required")
    name = str(profile["municipality"]).strip()
    if not name:
        raise ValueError("Missing municipality name")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="SheetTitle", parent=styles["Title"], fontSize=20, leading=25,
        textColor=colors.HexColor("#173B50"), spaceAfter=9,
    ))
    styles.add(ParagraphStyle(
        name="SheetBody", parent=styles["BodyText"], fontSize=9, leading=13,
        spaceAfter=9,
    ))
    styles.add(ParagraphStyle(
        name="SheetCell", parent=styles["BodyText"], fontSize=7.8, leading=10.3,
    ))
    styles.add(ParagraphStyle(
        name="SheetHead", parent=styles["SheetCell"], fontName="Helvetica-Bold",
        textColor=colors.white,
    ))
    rows = [[Paragraph(s, styles["SheetHead"]) for s in
             ("Indicatore", "Comune", "Mediana 27 Comuni", "Anno")]]
    for key, label, unit, year_key in FIELDS:
        val = float(profile[key])
        if not math.isfinite(val):
            raise ValueError("Non-finite municipal metric")
        median = facts["indicators"][key]["median"]
        rows.append([
            Paragraph(escape(label), styles["SheetCell"]),
            Paragraph(f"{val:.1f} {escape(unit)}", styles["SheetCell"]),
            Paragraph(f"{median:.1f} {escape(unit)}", styles["SheetCell"]),
            Paragraph(escape(str(profile[year_key])), styles["SheetCell"]),
        ])
    rows.append([
        Paragraph("Classificazione SNAI", styles["SheetCell"]),
        Paragraph(escape(str(profile["snai_class"])), styles["SheetCell"]),
        Paragraph("Non applicabile", styles["SheetCell"]),
        Paragraph(escape(str(profile["snai_year"])), styles["SheetCell"]),
    ])
    table = Table(rows, colWidths=[7.2*cm, 2.9*cm, 4.3*cm, 2.3*cm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#173B50")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F6F7")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LINEBELOW", (0, 0), (-1, -1), .2, colors.HexColor("#CBD6DC")),
    ]))
    story = [
        Paragraph("Profilo territoriale: " + escape(name), styles["SheetTitle"]),
        Paragraph(
            f"<b>ISTAT {istat_code}</b> | Green Community Sinergie in Canavese | "
            "EPAH TA 26-IT-Unione-TA26 | v0.2, bozza tecnica",
            styles["SheetBody"],
        ),
        Paragraph(
            "Scheda descrittiva comunale: otto variabili numeriche e una "
            "classificazione territoriale. I confronti con la mediana sono "
            "non ponderati e descrivono i 27 Comuni, non le famiglie.",
            styles["SheetBody"],
        ),
        Spacer(1, .25*cm), table, Spacer(1, .3*cm),
        Paragraph(
            "<b>Come leggere la scheda.</b> Anni, popolazioni di riferimento e "
            "denominatori degli indicatori sono diversi. Edifici pre-1981 "
            "non significa abitazioni inefficienti; redditi dei contribuenti "
            "non significa redditi delle famiglie; i tempi di viaggio "
            "sono proxy da punti comunali, non da abitazioni.",
            styles["SheetBody"],
        ),
        Paragraph(
            "La categoria SNAI non e un punteggio. I valori non vengono sommati "
            "in indici di poverta energetica; nessuna famiglia viene identificata.",
            styles["SheetBody"],
        ),
        Paragraph(
            "<b>NON PUBBLICARE</b> come scheda approvata: deriva dal pilota tecnico "
            "v0.1, in attesa di revisione scientifica e istituzionale indipendente. "
            "Fonti, licenze, qualita e limitazioni: bundle pilota e matrice "
            "delle evidenze.",
            styles["SheetBody"],
        ),
    ]
    doc = SimpleDocTemplate(
        str(path), pagesize=A4, leftMargin=1.8*cm, rightMargin=1.8*cm,
        topMargin=1.7*cm, bottomMargin=1.8*cm,
        title="EPAH v0.2 - " + name + " - bozza tecnica",
        author="EPAH Diagnosis - author and institutional approval pending",
    )
    doc.build(story)
