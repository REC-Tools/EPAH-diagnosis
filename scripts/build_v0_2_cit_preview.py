"""Build v0.2 CIT technical maps and EPAH-TA PDF from two real, QA-staged CSVs.

No original CIT sources bundled. No modification to v0.1, protected data, or
the canonical indicator matrix. Values are generator GROUPS, not homes.
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
from datetime import date
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)
from reportlab.lib.utils import ImageReader

from epah_diagnosis.cartography import render_thematic_map
from epah_diagnosis.geography import parse_boundaries_zip, write_geojson

ROOT = Path(__file__).resolve().parents[1]
TA_CODE = "26-IT-Unione-TA26"
FUELS_CSV = "cit_fuel_27.csv"
AGE_CSV = "cit_generator_age_27.csv"
FUEL_INDICATOR = "cit_diesel_lpg_generator_share"
AGE_INDICATOR = "cit_older_generator_share"
FUEL_SOURCE = "https://www.dati.gov.it/node/view-dataset/dataset?id=80540d5b-72af-4c45-901b-eb4a4f7ae9cf"
AGE_SOURCE = "https://www.dati.gov.it/node/view-dataset/dataset?id=d34fb6c0-6ae3-4ff6-9915-387d21606807"
NAVY = colors.HexColor("#123948")
GREY = colors.HexColor("#526370")
LIGHT = colors.HexColor("#EDF3F4")


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def load_registry(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    indexed = {r["istat_code"]: r["municipality"] for r in rows}
    if len(rows) != 27 or len(indexed) != 27 or len(set(indexed.values())) != 27:
        raise ValueError("Exactly 27 distinct municipality codes required")
    return indexed


def _int(row: dict, field: str) -> int:
    value = str(row.get(field, "")).strip()
    if not value.isdigit():
        raise ValueError(f"Noninteger or missing count in {field}")
    return int(value)


def _share(row: dict, name: str, numerator: int, denominator: int) -> float:
    if denominator <= 0 or numerator > denominator:
        raise ValueError(f"Invalid or empty denominator for {name}")
    try:
        value = float(row[name])
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError(f"Missing or nonnumeric {name}") from exc
    if not math.isfinite(value) or abs(value - 100 * numerator / denominator) > .011:
        raise ValueError(f"{name} does not equal numerator/denominator")
    return value


def load_output(folder: Path, registry: dict[str, str], registry_sha: str,
                mode: str) -> tuple[dict[str, dict], dict]:
    if mode not in {"fuel", "age"}:
        raise ValueError("Unsupported CIT mode")
    name, indicator, source = (
        (FUELS_CSV, FUEL_INDICATOR, FUEL_SOURCE) if mode == "fuel"
        else (AGE_CSV, AGE_INDICATOR, AGE_SOURCE)
    )
    source_csv = folder / name
    qa_file = folder / "cit_qa.json"
    qa = json.loads(qa_file.read_text(encoding="utf-8"))
    if (qa.get("qa_status") != "technical_extraction_only"
            or qa.get("validated_for_release") is not False
            or qa.get("indicator_id") != indicator
            or qa.get("source_url") != source
            or qa.get("registry_csv_sha256") != registry_sha
            or qa.get("output_csv_sha256") != hash_file(source_csv)
            or qa.get("municipalities_expected") != 27
            or qa.get("municipalities_with_generator_data") != 27
            or qa.get("missing") != []
            or (mode == "fuel" and qa.get("unclassified_fuel_labels") != {})
            or (mode == "age" and qa.get("older_years_threshold") != 20)):
        raise ValueError(f"{mode}: wrong QA, missing towns, source or modified output")
    snapshot = qa.get("snapshot_date_operator_reported")
    try:
        date.fromisoformat(snapshot)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{mode}: incorrect operator-reported snapshot") from exc
    with source_csv.open(encoding="utf-8-sig", newline="") as f:
        records = list(csv.DictReader(f))
    if len(records) != 27 or len({r["istat_code"] for r in records}) != 27:
        raise ValueError(f"{mode}: expected 27 unique municipality observations")
    clean = {}
    for r in records:
        code = r["istat_code"]
        if (code not in registry or r["municipality"] != registry[code]
                or r.get("snapshot_date") != snapshot):
            raise ValueError(f"{mode}: registry or snapshot mismatch")
        total = _int(r, "generator_groups_total")
        if mode == "fuel":
            classified = _int(r, "classified_groups")
            unclassified = _int(r, "unclassified_groups")
            numerator = _int(r, "diesel_groups") + _int(r, "lpg_groups")
            terms = ("natural_gas_groups", "diesel_groups", "lpg_groups",
                     "solid_fuels_groups", "electricity_groups", "other_groups")
            if (total != classified + unclassified
                    or classified != sum(_int(r, term) for term in terms)
                    or r.get("denominator") != "classified_generator_groups"):
                raise ValueError("Inconsistent CIT fuel group totals")
            value = _share(r, "diesel_lpg_share_pct", numerator, classified)
        else:
            classified = _int(r, "groups_with_known_year")
            unclassified = _int(r, "groups_with_unknown_year")
            numerator = _int(r, "groups_aged_20_or_more")
            if (total != classified + unclassified
                    or r.get("denominator") != "generator_groups_with_known_installation_year"):
                raise ValueError("Inconsistent CIT age group totals")
            value = _share(r, "older_generator_share_pct", numerator, classified)
        clean[code] = {"municipality": r["municipality"], "istat_code": code,
                       "group_total": total, "denominator": classified,
                       "unknown": unclassified, "numerator": numerator,
                       "value": value}
    if set(clean) != set(registry):
        raise ValueError(f"{mode}: incomplete municipality coverage")
    return clean, {
        "indicator_id": indicator, "source_url": source, "snapshot": snapshot,
        "source_sha256": qa["source_csv_sha256"],
        "prepared_sha256": hash_file(source_csv), "qa_sha256": hash_file(qa_file),
        "sum_numerator": sum(x["numerator"] for x in clean.values()),
        "sum_denominator": sum(x["denominator"] for x in clean.values()),
        "sum_unknown": sum(x["unknown"] for x in clean.values()),
        "municipal_mean": statistics.fmean(x["value"] for x in clean.values()),
    }


def join_geo(boundaries: Path, fuel: dict, age: dict) -> dict:
    names = {x["municipality"] for x in fuel.values()}
    geo = parse_boundaries_zip(boundaries.read_bytes(), names)
    for feature in geo["features"]:
        props = feature["properties"]
        code = props["municipality_code"]
        if (code not in fuel or code not in age or
                props["municipality"] != fuel[code]["municipality"] or
                props["municipality"] != age[code]["municipality"]):
            raise ValueError("Official ISTAT boundary names/codes do not match CIT")
        props["cit_diesel_lpg_share_pct"] = fuel[code]["value"]
        props["cit_older_generator_share_pct"] = age[code]["value"]
        props["cit_fuel_denominator"] = fuel[code]["denominator"]
        props["cit_age_denominator"] = age[code]["denominator"]
    if len(geo["features"]) != 27:
        raise ValueError("Expected 27 georeferenced CIT municipalities")
    return geo


def image_fit(path: Path, max_width: float, max_height: float) -> Image:
    width, height = ImageReader(str(path)).getSize()
    scale = min(max_width / width, max_height / height)
    return Image(str(path), width=width * scale, height=height * scale)


def write_pdf(path: Path, stats: dict, pngs: dict[str, Path],
              nametag: Path | None = None) -> None:
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CITTitle", parent=styles["Title"],
                              fontName="Helvetica-Bold", fontSize=21, leading=27,
                              textColor=NAVY, spaceAfter=14))
    styles.add(ParagraphStyle(name="CITText", parent=styles["BodyText"],
                              fontSize=10, leading=15, spaceAfter=10))
    styles.add(ParagraphStyle(name="CITSmall", parent=styles["BodyText"],
                              fontSize=8, leading=12, spaceAfter=7))
    heading, body, small = styles["CITTitle"], styles["CITText"], styles["CITSmall"]

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(GREY)
        canvas.drawString(1.6 * cm, 1 * cm, TA_CODE + " | EPAH Technical Assistance 2026")
        canvas.drawRightString(A4[0] - 1.6 * cm, 1 * cm, str(doc.page))
        canvas.restoreState()

    document = SimpleDocTemplate(str(path), pagesize=A4,
                                 leftMargin=1.7*cm, rightMargin=1.7*cm,
                                 topMargin=1.7*cm, bottomMargin=1.8*cm,
                                 title="EPAH TA26 - indicatori CIT Piemonte - anteprima v0.2",
                                 author="EPAH Diagnosis, assistenza tecnica 26-IT-Unione-TA26")
    story = []
    if nametag is not None:
        if not nametag.is_file():
            raise FileNotFoundError("Missing EPAH nametag original")
        story.extend([image_fit(nametag, 6*cm, 2.5*cm), Spacer(1, .7*cm)])
    else:
        story.append(Paragraph("EPAH Technical Assistance 2026", small))
    story.extend([
        Paragraph("Diagnosi territoriale della vulnerabilita alla poverta energetica", heading),
        Paragraph("FOCUS TECNICO | Combustibili e vetusta dei generatori", styles["Heading2"]),
        Spacer(1, .5*cm),
        Paragraph("Green Community Sinergie in Canavese - 27 Comuni", body),
        Paragraph("<b>Codice progetto:</b> " + TA_CODE + "<br/>"
                  "<b>Versione:</b> v0.2.0 CIT - anteprima tecnica<br/>"
                  "<b>Fonti:</b> Regione Piemonte / CSI Piemonte, Catasto Impianti Termici<br/>"
                  "<b>Data combustibili:</b> " + escape(stats["fuel"]["snapshot"]) + "<br/>"
                  "<b>Data installazioni:</b> " + escape(stats["age"]["snapshot"]), body),
        Spacer(1, .5*cm),
        Paragraph("Strumento sviluppato nell'ambito del programma di "
                  "Assistenza Tecnica EPAH 2026. Documento di lavoro per "
                  "FERVORES e l'Unione Montana; non una pubblicazione o "
                  "certificazione ufficiale della Commissione europea.", body),
        Paragraph("I dati CIT contano <b>gruppi termici registrati</b>, "
                  "non alloggi, edifici o famiglie. Queste due metriche sono "
                  "proxy di caratteristiche impiantistiche, non misure dirette "
                  "di poverta energetica.", body),
    ])
    for position, (key, name, label, caution) in enumerate([
        ("fuel", "Combustibili: gasolio e GPL", "Quota gruppi gasolio+GPL",
         "La presenza di GPL/gasolio puo riflettere l'assenza di rete metano "
         "e non dimostra di per se costi eccessivi o disagio familiare."),
        ("age", "Anzianita dei generatori", "Quota gruppi con anno installazione remoto",
         "La soglia e calcolata sull'anno riportato (20 anni di calendario), "
         "non necessariamente sulla data esatta di installazione."),
    ], start=1):
        s = stats[key]
        pooled = 100 * s["sum_numerator"] / s["sum_denominator"]
        story.extend([
            PageBreak(),
            Paragraph(f"{position}. {name}", heading),
            Paragraph(
                f"<b>Quota aggregata per gruppi:</b> {pooled:.2f}% "
                f"({s['sum_numerator']} / {s['sum_denominator']}). "
                f"<b>Media semplice delle 27 quote comunali:</b> "
                f"{s['municipal_mean']:.2f}%. Sono valori diversi: "
                "la mappa relativa usa soltanto la seconda.", body),
            Paragraph("Assoluta (cividis) e relativa alla media comunale "
                      "(verde = quota inferiore, grigio = media, "
                      "rosso = quota superiore).", small),
        ])
        maps = [image_fit(pngs[key+"_absolute"], 8.1*cm, 11*cm),
                image_fit(pngs[key+"_relative"], 8.1*cm, 11*cm)]
        img_table = Table([maps], colWidths=[8.3*cm, 8.3*cm])
        img_table.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),
                                       ("LEFTPADDING",(0,0),(-1,-1),0),
                                       ("RIGHTPADDING",(0,0),(-1,-1),0)]))
        story.extend([img_table, Spacer(1, .3*cm),
                      Paragraph(escape(caution), body),
                      Paragraph(f"Fonte: Regione Piemonte / CSI Piemonte, "
                                f"snapshot dichiarato {escape(s['snapshot'])}. "
                                "La variabilita dei conteggi rende "
                                "l'indicatore esplorativo.", small)])
    story.extend([
        PageBreak(),
        Paragraph("3. Metodologia, limiti e destinazione d'uso", heading),
        Paragraph("Gasolio+GPL: numeratore = numero di gruppi classificati "
                  "come gasolio o GPL. Denominatore = totale gruppi con "
                  "combustibile riconosciuto. Le categorie non riconosciute "
                  "sono escluse e impediscono la costruzione del rapporto "
                  "in modalita rigorosa.", body),
        Paragraph("Generatori datati: numeratore = gruppi con anno di "
                  "installazione non successivo all'anno dello snapshot "
                  "meno 20; denominatore = gruppi con anno noto. "
                  "Non si inferiscono anni da intervalli ambigui.", body),
        Paragraph("La graduazione cromatica assoluta mostra i valori; "
                  "la relativa indica scostamenti in punti percentuali dalla "
                  "media NON ponderata dei 27 Comuni. Nessun punteggio "
                  "composito viene calcolato.", body),
        Paragraph("Il mese di aggiornamento del catalogo non sostituisce "
                  "la data effettiva dei record. Le due date di snapshot "
                  "sono state dichiarate da chi ha scaricato le fonti "
                  "e devono essere confrontate con i metadati originali. "
                  "Le percentuali non rappresentano la quota di nuclei "
                  "familiari in poverta energetica.", body),
        Paragraph("Attribuzione: Regione Piemonte / CSI Piemonte; "
                  "licenza indicata nel catalogo CC BY 4.0. "
                  "Le elaborazioni e interpretazioni degli autori non "
                  "riflettono necessariamente la posizione della "
                  "Commissione europea o di EPAH.", small),
        Paragraph("Fonte combustibili: " + escape(FUEL_SOURCE), small),
        Paragraph("Fonte installazioni: " + escape(AGE_SOURCE), small),
    ])
    document.build(story, onFirstPage=footer, onLaterPages=footer)


def build(fuel_dir: Path, age_dir: Path, registry_path: Path,
          boundaries: Path, out: Path, nametag: Path | None = None) -> Path:
    if out.exists():
        raise FileExistsError("Output already exists; choose a fresh --out-dir")
    registry = load_registry(registry_path)
    reg_hash = hash_file(registry_path)
    fuel, fuel_meta = load_output(fuel_dir, registry, reg_hash, "fuel")
    age, age_meta = load_output(age_dir, registry, reg_hash, "age")
    geo = join_geo(boundaries, fuel, age)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".cit-v02-", dir=out.parent) as td:
        staged = Path(td) / "bundle"
        staged.mkdir()
        csvpath = staged / "cit_indicators_27.csv"
        with csvpath.open("w", encoding="utf-8", newline="") as f:
            fields = ["municipality", "istat_code", "diesel_lpg_share_pct",
                      "older_generator_share_pct", "fuel_group_denominator",
                      "age_group_denominator", "fuel_snapshot", "age_snapshot"]
            writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            for code, name in sorted(registry.items(), key=lambda p:p[1]):
                writer.writerow({
                    "municipality": name, "istat_code": code,
                    "diesel_lpg_share_pct": f"{fuel[code]['value']:.2f}",
                    "older_generator_share_pct": f"{age[code]['value']:.2f}",
                    "fuel_group_denominator": fuel[code]["denominator"],
                    "age_group_denominator": age[code]["denominator"],
                    "fuel_snapshot": fuel_meta["snapshot"],
                    "age_snapshot": age_meta["snapshot"],
                })
        write_geojson(geo, staged / "cit_indicators_27.geojson")
        specs = [
            ("fuel", "cit_diesel_lpg_share_pct", "Gasolio+GPL: quota gruppi termici"),
            ("age", "cit_older_generator_share_pct", "Gruppi termici datati (anno installazione)"),
        ]
        pngs = {}
        for prefix, field, name in specs:
            for mode in ("absolute", "relative"):
                path = staged / f"cit_{prefix}_{mode}.png"
                render_thematic_map(
                    geo, field, name, "%", path, mode=mode,
                    direction="higher_is_worse" if mode == "relative" else None,
                    footer=f"Regione Piemonte / CIT | {TA_CODE} | 27 Comuni | proxy, non poverta misurata",
                )
                pngs[prefix+"_"+mode] = path
        write_pdf(staged / "cit_technical_report_v0_2.pdf",
                  {"fuel": fuel_meta, "age": age_meta}, pngs, nametag)
        manifest = {
            "track": "v0.2_cit_technical_preview",
            "institutional_approval": "pending",
            "validated_for_energy_poverty_household_measurement": False,
            "municipalities": 27, "ta_code": TA_CODE,
            "source_meta": {"fuel": fuel_meta, "age": age_meta},
            "boundary_sha256": hash_file(boundaries),
            "registry_sha256": reg_hash,
            "geojson_crs": "OGC:CRS84", "map_crs": "EPSG:32632",
            "relative_reference": "unweighted_mean_of_27_municipal_values",
            "outputs_sha256": {p.name: hash_file(p) for p in staged.iterdir()
                               if p.is_file() and p.name != "cit_manifest_v0_2.json"},
        }
        (staged / "cit_manifest_v0_2.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        staged.rename(out)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare CIT v0.2 maps and technical EPAH PDF for 27 municipalities")
    parser.add_argument("--fuel-dir", type=Path, default=ROOT/"outputs/quality/cit_fuel_v02")
    parser.add_argument("--age-dir", type=Path, default=ROOT/"outputs/quality/cit_age_v02")
    parser.add_argument("--registry", type=Path, default=ROOT/"data/municipalities.csv")
    parser.add_argument("--boundaries-zip", type=Path, default=ROOT/"data/downloads/Limiti01012026_g.zip")
    parser.add_argument("--out-dir", type=Path, default=ROOT/"outputs/v0.2.0-cit-preview")
    parser.add_argument("--epah-nametag", type=Path,
                        help="Optional supplied EPAH_Color.png, proportions preserved")
    args = parser.parse_args()
    destination = build(args.fuel_dir, args.age_dir, args.registry,
                        args.boundaries_zip, args.out_dir, args.epah_nametag)
    print("EPAH CIT technical preview created:", destination)
    print("27 municipalities | 4 maps | CSV | CRS84 GeoJSON | PDF | SHA manifest")
    print("No household measures, no source or institutional approval inferred.")


if __name__ == "__main__":
    main()
