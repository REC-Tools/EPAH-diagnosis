"""V0.2 technical territorial diagnosis: PDF narrative from an audited v0.1 bundle.

No canonical promotion, no CIT input, no individual household inference.
The input bundle is verified independently before report contents are derived.
"""
from __future__ import annotations

import csv
import json
import math
import statistics
from collections import Counter
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from epah_diagnosis.municipality_profile import NUMERIC_INDICATORS
from epah_diagnosis.release_artifacts import (
    MAP_SPECS, sha256_file, validate_bundle_contents,
)

TOTAL_MUNICIPALITIES = 27
FIELDS = (
    ("population_65_plus_pct", "Popolazione con 65 anni e oltre", "%", "population_65_plus_year"),
    ("income_vulnerability_pct", "Contribuenti con reddito fino a 15.000 EUR", "%", "income_vulnerability_year"),
    ("old_building_stock_pct", "Edifici residenziali costruiti prima del 1981", "%", "old_building_stock_year"),
    ("heating_degree_days", "Gradi-giorno per riscaldamento", "GG", "heating_degree_days_year"),
    ("mean_altitude_m", "Altitudine media comunale", "m", "mean_altitude_year"),
    ("dea_access_minutes", "Accesso stradale a DEA I/II (proxy)", "min", "dea_access_year"),
    ("upper_secondary_access_minutes", "Accesso stradale a scuole superiori (proxy)", "min", "upper_secondary_access_year"),
    ("rail_access_minutes", "Accesso stradale a ferrovia (proxy)", "min", "rail_access_year"),
)
FIELD_LABELS = {key: label for key, label, _, _ in FIELDS}
MAP_FIELDS = {
    "old_building_stock_pct": "map_old_building_stock.png",
    "income_vulnerability_pct": "map_income_vulnerability.png",
}


def verified_data(bundle: Path, registry_file: Path, release_config: Path) -> tuple[list[dict], dict]:
    """Fail closed on altered inputs, missing values or malformed 27-town coverage."""
    config = json.loads(release_config.read_text(encoding="utf-8"))
    required = config.get("required_artifacts")
    if not isinstance(required, list):
        raise ValueError("Missing v0.1 required artifact list")
    with registry_file.open(encoding="utf-8-sig", newline="") as stream:
        entries = list(csv.DictReader(stream))
    registry = {item["municipality"]: item["istat_code"] for item in entries}
    if (len(entries) != TOTAL_MUNICIPALITIES or len(registry) != TOTAL_MUNICIPALITIES
            or any(len(code) != 6 or not code.isdigit() for code in registry.values())
            or len(set(registry.values())) != TOTAL_MUNICIPALITIES):
        raise ValueError("Report requires the registered 27 unique ISTAT municipalities")
    validate_bundle_contents(bundle, registry, required)
    manifest = json.loads((bundle / "release_manifest.json").read_text(encoding="utf-8"))
    if not (manifest.get("municipalities") == 27
            and manifest.get("core_indicators") == 9
            and manifest.get("observations") == 243
            and manifest.get("no_composite_score") is True):
        raise ValueError("V0.1 provenance/indicator scope differs from the report")
    with (bundle / "municipality_profile.csv").open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        reader = csv.DictReader(stream)
        profiles = list(reader)
    if len(profiles) != 27 or {p["municipality"] for p in profiles} != set(registry):
        raise ValueError("Report profile does not match registered municipalities")
    for p in profiles:
        for key, _, unit, year_key in FIELDS:
            try:
                val = float(p[key])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"Missing/invalid {key} for {p['municipality']}") from exc
            if (not math.isfinite(val) or val < 0
                    or (unit == "%" and val > 100)
                    or (unit == "min" and val > 1440)
                    or not p.get(year_key)):
                raise ValueError(f"Out-of-range or undated {key} for {p['municipality']}")
        if p.get("snai_class") not in "ABCDEF" or not p.get("snai_year"):
            raise ValueError("Invalid SNAI category/year")
    return profiles, manifest


def identical_numeric_series(profiles: list[dict]) -> list[dict]:
    """Detect exact municipal value equality; NEVER infer source equivalence."""
    from itertools import combinations

    if len(profiles) != TOTAL_MUNICIPALITIES:
        raise ValueError("Expected 27 municipal profiles for series comparison")
    matches = []
    for first, second in combinations(FIELDS, 2):
        a, b = first[0], second[0]
        if all(float(p[a]) == float(p[b]) for p in profiles):
            matches.append({
                "indicator_a": a, "indicator_b": b,
                "municipalities_equal": TOTAL_MUNICIPALITIES,
                "interpretation": "observed_values_identical_review_source_methods",
            })
    return matches


def computed_facts(profiles: list[dict]) -> dict:
    """Descriptive municipal statistics only: never a composite poverty score."""
    if len(profiles) != TOTAL_MUNICIPALITIES:
        raise ValueError("Expected 27 distinct municipality profiles")
    indicators = {}
    for key, label, unit, year_key in FIELDS:
        values = sorted(float(p[key]) for p in profiles)
        year_values = sorted({str(p[year_key]) for p in profiles})
        indicators[key] = {
            "label": label, "unit": unit, "reference_years": year_values,
            "municipalities": len(values),
            "min": round(values[0], 2),
            "median": round(statistics.median(values), 2),
            "max": round(values[-1], 2),
            "range": round(values[-1] - values[0], 2),
            "aggregation": "unweighted_municipality_descriptive",
        }
    # Three separate yes/no signals; a descriptive intersection, not a score.
    three = (
        "population_65_plus_pct", "income_vulnerability_pct", "old_building_stock_pct",
    )
    medians = {k: indicators[k]["median"] for k in three}
    counts = {
        "above_income_and_building_medians": sum(
            float(p[three[1]]) > medians[three[1]]
            and float(p[three[2]]) > medians[three[2]] for p in profiles
        ),
        "above_all_three_medians": sum(
            all(float(p[k]) > medians[k] for k in three) for p in profiles
        ),
    }
    return {
        "status": "technical_v0_2_draft_do_not_publish",
        "population_inference": "not_permitted",
        "composite_energy_poverty_score": False,
        "municipalities": TOTAL_MUNICIPALITIES,
        "indicators": indicators,
        "snai_categories": dict(sorted(Counter(p["snai_class"] for p in profiles).items())),
        "identical_numeric_series": identical_numeric_series(profiles),
        "descriptive_overlap": {
            **counts, "denominator_municipalities": TOTAL_MUNICIPALITIES,
            "rule": "Strictly greater than each separate unweighted municipal median; "
                    "no additive index, no household attribution, no causal inference.",
            "benchmark_years_differ": True,
        },
    }


def _styles() -> dict:
    s = getSampleStyleSheet()
    s.add(ParagraphStyle(
        name="EPTitle", parent=s["Title"], fontName="Helvetica-Bold",
        fontSize=23, leading=29, textColor=colors.HexColor("#12354B"),
        spaceAfter=18,
    ))
    s.add(ParagraphStyle(
        name="EPHeading", parent=s["Heading2"], fontName="Helvetica-Bold",
        fontSize=15, leading=19, textColor=colors.HexColor("#12354B"),
        spaceAfter=12, spaceBefore=4,
    ))
    s.add(ParagraphStyle(
        name="EPBody", parent=s["BodyText"], fontName="Helvetica",
        fontSize=10, leading=15, spaceAfter=13,
    ))
    s.add(ParagraphStyle(
        name="EPNote", parent=s["BodyText"], fontName="Helvetica",
        fontSize=8.3, leading=12, textColor=colors.HexColor("#445569"),
        spaceAfter=9,
    ))
    s.add(ParagraphStyle(
        name="EPCell", parent=s["BodyText"], fontName="Helvetica",
        fontSize=8, leading=11,
    ))
    s.add(ParagraphStyle(
        name="EPHeadCell", parent=s["EPCell"], fontName="Helvetica-Bold",
        textColor=colors.white,
    ))
    return s


def _table(rows: list[list[str]], widths: list[float], styles: dict):
    data = [
        [Paragraph(escape(str(c)), styles["EPHeadCell" if i == 0 else "EPCell"])
         for c in row]
        for i, row in enumerate(rows)
    ]
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#163F56")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
            colors.HexColor("#F0F5F7"), colors.white,
        ]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, 0), .5, colors.HexColor("#0B6B75")),
        ("LINEBELOW", (0, 1), (-1, -1), .2, colors.HexColor("#CAD6DD")),
    ]))
    return table


def _image(path: Path, max_width: float = 16.5 * cm,
           max_height: float = 15.5 * cm) -> Image:
    picture = Image(str(path))
    ratio = min(max_width / picture.imageWidth, max_height / picture.imageHeight)
    picture.drawWidth = picture.imageWidth * ratio
    picture.drawHeight = picture.imageHeight * ratio
    picture.hAlign = "CENTER"
    return picture


def _footer(canvas, doc):
    canvas.saveState()
    w, _ = A4
    canvas.setStrokeColor(colors.HexColor("#A5B5C1"))
    canvas.line(1.7 * cm, 1.3 * cm, w - 1.7 * cm, 1.3 * cm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#456074"))
    canvas.drawString(1.7 * cm, 1.05 * cm, "EPAH TA 26-IT-Unione-TA26 | Bozza tecnica v0.2")
    canvas.drawRightString(w - 1.7 * cm, 1.05 * cm, str(doc.page))
    canvas.restoreState()


def write_report(path: Path, bundle: Path, profiles: list[dict],
                 facts: dict, config: dict) -> None:
    """Nine-section PDF with independent maps, source years and cautious interpretation."""
    styles = _styles()
    P = lambda txt, kind="EPBody": Paragraph(txt, styles[kind])
    H = lambda txt: P(txt, "EPHeading")
    story = []
    ta_code = escape(config["ta_code"])
    audience = escape(config["audience"])

    # 1. Cover
    story += [
        Spacer(1, 2.4 * cm),
        P("Diagnosi territoriale della vulnerabilita alla poverta energetica", "EPTitle"),
        P("Green Community Sinergie in Canavese | 27 Comuni", "EPHeading"),
        Spacer(1, 0.8 * cm),
        P("Versione <b>v0.2 - bozza tecnica non pubblicabile</b>. "
          "Elaborazione di screening comunale, basata sul bundle pilota v0.1.", "EPBody"),
        P("Sviluppato nell'ambito del programma di Assistenza Tecnica EPAH 2026.", "EPBody"),
        P("Codice progetto: <b>" + ta_code + "</b><br/>"
          "Destinatari: " + audience + "<br/>"
          "Redazione e approvazione istituzionale: da confermare.", "EPBody"),
        Spacer(1, 1.1 * cm),
        P("Non e un documento ufficiale della Commissione europea, "
          "non identifica famiglie in poverta energetica e non determina "
          "un indice composito.", "EPNote"),
        PageBreak(),
    ]
    # 2. Executive summary
    old = facts["indicators"]["old_building_stock_pct"]
    inc = facts["indicators"]["income_vulnerability_pct"]
    dea = facts["indicators"]["dea_access_minutes"]
    story += [
        H("1 | Sintesi per il decisore"),
        P("Il lavoro confronta 27 Comuni attraverso nove indicatori distinti per "
          "definizione. Alcune serie numeriche possono coincidere: i valori "
          "sono aggregati territoriali, con anni e denominatori differenti."),
        P(f"<b>Patrimonio edilizio:</b> la quota di edifici residenziali pre-1981 "
          f"varia dal {old['min']:.1f}% al {old['max']:.1f}% tra i Comuni (fonte 2011)."),
        P(f"<b>Fragilita reddituale:</b> il proxy relativo ai contribuenti con reddito "
          f"fino a 15.000 EUR presenta una mediana comunale del {inc['median']:.1f}% "
          f"(anno/i: {', '.join(inc['reference_years'])})."),
        P(f"<b>Accessibilita sanitaria:</b> il tempo stradale proxy verso DEA I/II "
          f"varia da {dea['min']:.1f} a {dea['max']:.1f} minuti. "
          "Non e il tempo misurato dalle singole abitazioni."),
        H("Domande operative"),
        P("Quali edifici pubblici e abitazioni necessitano di verifiche energetiche "
          "piu approfondite? Quali popolazioni possono incontrare barriere di accesso "
          "ai servizi? Quali evidenze locali servono prima di disegnare misure?"),
        P("Nessuna delle tre evidenze dimostra, da sola o combinata, quante "
          "famiglie vivano in poverta energetica.", "EPNote"),
        PageBreak(),
    ]
    # 3. Hypothesis-evidence connections
    story += [
        H("2 | Ipotesi e dati disponibili"),
        P("Le ipotesi orientano la raccolta dati e il confronto locale. "
          "Non sono conclusioni causali o classificazioni individuali."),
        _table([
            ["Ipotesi di lavoro", "Proxy disponibile", "Che cosa non misura"],
            ["Edifici piu vecchi possono richiedere interventi mirati",
             "Quota edifici prima del 1981 (2011)", "APE, consumi reali e comfort"],
            ["Fragilita economica richiede approfondimenti",
             "Quota contribuenti con reddito fino a 15.000 EUR",
             "Reddito equivalente delle famiglie e bollette"],
            ["L'accesso ai servizi puo essere piu complesso nei Comuni periferici",
             "Tempi verso DEA, scuole, ferrovia",
             "Tempo porta a porta, orari e accessibilita individuale"],
            ["Il clima puo incidere sul fabbisogno energetico",
             "Gradi-giorno e altitudine",
             "Consumi e spese energetiche effettive"],
        ], [5.3*cm, 5.6*cm, 6*cm], styles),
        Spacer(1, .5*cm),
        P("La metodologia segue una logica di screening ispirata alla diagnosi EPAH: "
          "ipotesi, indicatori, valutazione dei dati, interpretazione e consultazione.",
          "EPNote"),
        PageBreak(),
    ]
    # 4. Nine indicators and gaps
    story += [
        H("3 | Nove indicatori, nove provenienze"),
        P("Anni e unita sono mantenuti separati. Le medie comunali non "
          "sono stime ponderate della popolazione."),
    ]
    rows = [["Indicatore", "Unita", "Anno/i"]]
    for key, label, unit, _ in FIELDS:
        rows.append([label, unit, ", ".join(facts["indicators"][key]["reference_years"])])
    rows.append(["Classificazione territoriale SNAI", "A-F", ", ".join(
        sorted({p["snai_year"] for p in profiles}))])
    story += [
        _table(rows, [9.2*cm, 2.2*cm, 5.5*cm], styles),
        Spacer(1, .35*cm),
        P("Dimensioni non coperte in modo diretto: consumi e spesa domestica, "
          "APE aggiornate, efficienza impianti, impatti su salute/comfort, "
          "partecipazione e misure di policy. Assenza non equivale a valore zero.",
          "EPNote"),
        PageBreak(),
    ]
    # 5-6. Maps embedded from the existing audited package
    for n, (field, title, note) in enumerate((
        ("old_building_stock_pct", "4 | Patrimonio edilizio",
         "Una quota storica di edifici pre-1981 non e una misura diretta "
         "della prestazione energetica attuale."),
        ("income_vulnerability_pct", "5 | Fragilita economica",
         "I contribuenti con reddito fino a 15.000 EUR non coincidono "
         "con i nuclei familiari e non misurano la spesa energetica."),
    )):
        meta = facts["indicators"][field]
        story += [
            H(title),
            P(f"{escape(meta['label'])}: distribuzione comunale, "
              f"{escape(', '.join(meta['reference_years']))}. Unita: {meta['unit']}."),
            _image(bundle / "maps" / MAP_FIELDS[field]),
            Spacer(1, .45*cm),
            P(note, "EPNote"),
            P("La mappa e riprodotta dal bundle pilota v0.1 e conserva "
              "la propria legenda originale. Le geometrie comunali "
              "non consentono inferenze sui singoli residenti.", "EPNote"),
            PageBreak(),
        ]
    # 7. Numeric spread
    story += [
        H("6 | Variabilita tra i 27 Comuni"),
        P("Minimo, mediana e massimo sono calcolati sui 27 valori comunali "
          "indipendentemente dalla popolazione. Non sono soglie di poverta energetica."),
    ]
    rows = [["Indicatore", "Min", "Mediana", "Max", "Unita"]]
    for key, _, unit, _ in FIELDS:
        item = facts["indicators"][key]
        rows.append([FIELD_LABELS[key],
                     f"{item['min']:.1f}", f"{item['median']:.1f}",
                     f"{item['max']:.1f}", unit])
    story += [
        _table(rows, [8.1*cm, 2.2*cm, 2.6*cm, 2.2*cm, 1.8*cm], styles),
        Spacer(1, .45*cm),
        P("SNAI (categorie): " + "; ".join(
            f"{key}: {count}" for key, count in facts["snai_categories"].items()
        ) + ". La classe SNAI e categoriale, non una scala numerica di rischio.", "EPNote"),
        PageBreak(),
    ]
    # 8. Multidimensional reading without composite score
    overlap = facts["descriptive_overlap"]
    duplicates = facts.get("identical_numeric_series", [])
    if duplicates:
        examples = [
            FIELD_LABELS[x["indicator_a"]] + " / " + FIELD_LABELS[x["indicator_b"]]
            for x in duplicates[:2]
        ]
        identity_warning = (
            "ATTENZIONE - serie coincidenti in 27/27 Comuni: "
            + "; ".join(escape(x) for x in examples)
            + (f" (e altre {len(duplicates)-2} coppie)." if len(duplicates)>2 else ".")
            + " Non equivale a una validazione delle fonti o a due evidenze indipendenti."
        )
    else:
        identity_warning = "Nessuna coincidenza perfetta fra le otto serie numeriche."
    story += [
        H("7 | Lettura incrociata descrittiva"),
        P(identity_warning, "EPNote"),
        P("Se due serie numeriche coincidono in tutti i Comuni, "
          "la loro co-occorrenza non e una seconda evidenza empirica indipendente. "
          "Verificare definizione delle destinazioni e metodo prima dell'uso.", "EPNote"),
        P("Tre dimensioni esplorative sono lette separatamente: eta della "
          "popolazione, quota di contribuenti a reddito basso e patrimonio "
          "edilizio storico. Le soglie qui usate sono mediane dei 27 Comuni, "
          "non benchmark di fabbisogno o indicatori validati di poverta."),
        P(f"<b>{overlap['above_income_and_building_medians']} su 27</b> Comuni "
          "sono sopra la mediana sia per quota di contribuenti a basso "
          "reddito sia per quota di edifici pre-1981."),
        P(f"<b>{overlap['above_all_three_medians']} su 27</b> Comuni sono "
          "sopra le rispettive mediane di tutte e tre le dimensioni."),
        P("Questi sono <b>conteggi di co-occorrenza descrittiva</b>, non "
          "un punteggio cumulativo: non classificano famiglie, non "
          "stabiliscono causalita e non giustificano graduatorie di rischio."),
        H("Come utilizzare il confronto"),
        P("Usare le sovrapposizioni per formulare domande ai Comuni e "
          "confrontare i proxy con conoscenze locali, consumi aggregati "
          "e informazioni raccolte con metodi appropriati."),
        P("Gli anni di osservazione non sono omogenei: una stessa intersezione "
          "non implica un fenomeno simultaneo.", "EPNote"),
        PageBreak(),
    ]
    # 9. Methods, caveats and next steps
    story += [
        H("8 | Azioni, metodo e limiti"),
        P("<b>Per FERVORES:</b> usare le distribuzioni comunali come traccia "
          "di consultazione; definire con i membri quali dati di consumo "
          "aggregati e quali bisogni possono essere verificati senza "
          "trattamento improprio di dati personali."),
        P("<b>Per Unione Montana e Comuni:</b> validare interpretazioni territoriali "
          "con uffici tecnici e sociali; verificare dove interventi edilizi "
          "e accessibilita ai servizi richiedano nuovi rilievi."),
        P("<b>Per la prossima release:</b> approfondire fonti energetiche "
          "comparabili, vintage, accessibilita transregionale e revisione "
          "metodologica prima di ogni pubblicazione."),
        H("Tracciabilita"),
        P("Tutti i 27 profili, le nove mappe originali, gli anni e le "
          "evidenze di fonte sono disponibili nel bundle v0.1 collegato. "
          "Questo rapporto verifica i relativi hash e non modifica "
          "dati o approvazioni. GeoJSON: CRS84/WGS84; cartografia "
          "tematica: proiezione metrica EPSG:32632.", "EPBody"),
        P("Il contenuto e elaborato nell'ambito dell'assistenza tecnica. "
          "Le analisi e interpretazioni degli autori non rappresentano "
          "necessariamente la posizione della Commissione europea o di EPAH.",
          "EPNote"),
        P("BOZZA TECNICA v0.2 | NON PUBBLICARE come diagnosi istituzionalmente "
          "approvata. Nessuna inferenza a livello di nucleo familiare.", "EPNote"),
    ]

    doc = SimpleDocTemplate(
        str(path), pagesize=A4, leftMargin=1.8*cm, rightMargin=1.8*cm,
        topMargin=1.7*cm, bottomMargin=1.8*cm,
        title="EPAH Diagnosis v0.2 - Diagnosi territoriale - Bozza tecnica",
        author=config["author_label"], subject="27 municipal territorial screening, not household poverty",
    )
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
