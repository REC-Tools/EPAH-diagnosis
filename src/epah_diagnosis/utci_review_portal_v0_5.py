"""Present the existing UTCI source audit in a portable, unapproved local pack."""
from __future__ import annotations

import argparse
from html import escape
import json
from pathlib import Path
import shutil
import tempfile

from .directory_publication import publish_directory
from .provenance import sha256_file
from .utci_export_review_v0_5 import inspect_export

ISSUES = {
    "day_units_not_explicit": "L'unità dei giorni non è confermata dagli attributi del campo. Non viene dedotta dal nome.",
    "time_bounds_require_interpretation": "I limiti temporali richiedono interpretazione; non dimostrano da soli un anno completo.",
    "time_reference_year_mismatch": "Il tempo della fonte non coincide con l'anno richiesto al controllo.",
    "calendar_not_explicit": "Il calendario non è dichiarato; quello usato per decodificare non è una conferma della fonte.",
    "time_bounds_missing": "La fonte non offre i limiti temporali richiesti dal controllo.",
    "selected_values_masked": "Sono presenti valori mascherati. Rimangono distinti dagli zeri validi.",
    "selected_values_unmasked_nonfinite": "Sono presenti valori non finiti non mascherati, da verificare.",
    "selected_values_outside_day_range": "Alcuni valori sono fuori dall'intervallo numerico dei giorni dell'anno candidato.",
    "selected_values_fractional": "Sono presenti valori frazionari: non vengono arrotondati.",
    "selected_values_no_finite_data": "Non sono disponibili valori finiti da descrivere.",
}

STYLE = """
:root{font-family:system-ui,sans-serif;color:#203640;background:#eef3f4;color-scheme:light}
*{box-sizing:border-box}body{margin:0}header{background:#173f4e;color:white;padding:2rem max(1rem,calc((100vw - 1000px)/2))}
h1{font-size:clamp(1.7rem,4vw,2.5rem);margin:.5rem 0}header p{max-width:75ch}main,footer{max-width:1040px;margin:auto;padding:1rem}
section{background:white;border:1px solid #cbd7dc;border-radius:10px;padding:1.3rem;margin-bottom:1rem}h2{font-size:1.3rem;margin-top:0}
p,li{line-height:1.6}a{color:#075781;text-underline-offset:3px}a:focus-visible,summary:focus-visible,pre:focus-visible{outline:3px solid #ae5700;outline-offset:3px}
nav{display:flex;gap:1.2rem;flex-wrap:wrap}table{border-collapse:collapse;width:100%}th,td{text-align:left;vertical-align:top;border-bottom:1px solid #d6e0e4;padding:.7rem;overflow-wrap:anywhere}
th{width:45%}.notice{padding:.8rem 1rem;background:#fff4df;border-left:4px solid #ad6400}.synthetic{background:#fff4df;color:#442700;padding:.8rem}
code{overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:28rem;overflow:auto;background:#f1f5f6;padding:1rem;font-size:.85rem}small{display:block;margin-top:.4rem}
@media(max-width:560px){section{padding:1rem}th,td{padding:.55rem;font-size:.92rem}}@media print{body{background:white}header{background:white;color:#203640}section{border-radius:0}pre{max-height:none;overflow:visible}}
"""


def _text(value) -> str:
    if value is None or value == "":
        return "Non dichiarato / non disponibile"
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, allow_nan=False)
    return escape(str(value))


def _table(rows) -> str:
    return "<table><tbody>" + "".join(
        f"<tr><th scope='row'>{escape(label)}</th><td>{_text(value)}</td></tr>"
        for label, value in rows) + "</tbody></table>"


def render(report: dict, *, synthetic: bool) -> str:
    """Render only the audit snapshot; no NetCDF reads or scientific formulas."""
    field = report["selected_field"]
    attributes = report["variables"][field]["attributes"]
    stats = report["selected_values"]
    time = report.get("time", {})
    issues = report["issues"]
    warning = ("<p class='synthetic'><strong>DATI SINTETICI · NON SONO DATI TERRITORIALI</strong></p>"
               if synthetic else "<p>Fonte locale da verificare; questo pacchetto non certifica la provenienza CDS.</p>")
    issue_list = ("<ul>" + "".join(
        "<li>" + escape(ISSUES.get(issue, "Controllo della fonte da approfondire."))
        + "<small><code>" + escape(issue) + "</code></small></li>" for issue in issues) + "</ul>"
        if issues else "<p>Nessuna anomalia nei controlli strutturali eseguiti. La revisione scientifica resta aperta.</p>")
    identity = _table([
        ("Campo selezionato esplicitamente", field),
        ("Descrizione ricevuta", attributes.get("long_name")),
        ("Unità dichiarata nel file", attributes.get("units")),
        ("Anno richiesto al controllo", report["reference_year"]),
        ("Tempo decodificato della fonte", time.get("decoded_values")),
        ("Limiti temporali decodificati", time.get("decoded_bounds")),
        ("Calendario dichiarato", time.get("attributes", {}).get("calendar")),
        ("Calendario usato per decodificare", time.get("calendar_used_for_decoding")),
    ])
    values = _table([(label, stats[key]) for label, key in [
        ("Valori totali nel campo", "cells"), ("Valori finiti", "finite"),
        ("Valori mascherati", "masked"), ("Non finiti non mascherati", "unmasked_nonfinite"),
        ("Zeri validi", "zero"), ("Minimo numerico", "minimum"), ("Massimo numerico", "maximum"),
        ("Valori frazionari", "fractional"),
        ("Valori fuori dall'intervallo numerico candidato", "outside_day_range"),
        ("Limite gregoriano usato nella diagnostica", "gregorian_year_day_limit"),
    ]])
    coordinates = _table([
        ("Latitudini dei centri", report.get("latitude", {}).get("values")),
        ("Passi di latitudine", report.get("latitude", {}).get("steps")),
        ("Longitudini dei centri", report.get("longitude", {}).get("values")),
        ("Passi di longitudine", report.get("longitude", {}).get("steps")),
    ])
    metadata = escape(json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2))
    return f"""<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>UTCI · revisione della fonte</title><style>{STYLE}</style></head>
<body><header><p>BOZZA TECNICA · technical_draft_do_not_publish</p><h1>UTCI: revisione della fonte</h1><p>Originale locale, controlli e questioni aperte. Non sono risultati comunali né una validazione scientifica.</p>{warning}</header>
<main><section aria-labelledby="documents"><h2 id="documents">Documenti del pacchetto</h2><nav aria-label="Originale e controlli"><a href="source/original.nc">Originale NetCDF</a><a href="review.json">Controllo JSON</a><a href="manifest.json">Manifest degli hash</a></nav><p>Conservare e trasferire l'intera cartella. La consultazione non richiede servizi remoti o credenziali.</p><p>SHA-256 dell'originale: <code>{escape(report['source_sha256'])}</code></p></section>
<section aria-labelledby="identity"><h2 id="identity">Campo e periodo della fonte</h2>{identity}<p>Anno richiesto e tempo della fonte restano distinti. Non viene rietichettato il periodo del file.</p></section>
<section aria-labelledby="issues"><h2 id="issues">Questioni da revisionare ({len(issues)})</h2>{issue_list}<p class="notice">Soglia e significato del campo, completezza giornaliera e copertura comunale: da verificare. Nessun risultato è approvato e la pubblicazione territoriale non è autorizzata.</p></section>
<section aria-labelledby="values"><h2 id="values">Valori numerici del campo</h2>{values}<p>Le diagnostiche riguardano i valori del file, non medie comunali. Il confronto numerico con i giorni dell'anno non conferma l'unità o la completezza. Nessun valore viene convertito, arrotondato o sostituito con zero.</p></section>
<section aria-labelledby="coordinates"><h2 id="coordinates">Coordinate e copertura</h2>{coordinates}<p>L'inviluppo dei centri delle celle non dimostra la copertura dei poligoni comunali. Intersezioni, aree valide e media ponderata per superficie non sono calcolate.</p></section>
<section aria-labelledby="next"><h2 id="next">Prossima revisione</h2><ol><li>Documentare unità, soglia, minimo giornaliero e cumulatività del campo selezionato.</li><li>Interpretare il periodo e verificare i contributi giornalieri dell'anno.</li><li>Verificare copertura e compatibilità delle geometrie comunali.</li><li>Confermare proiezione equivalente e trattamento delle lacune prima dell'aggregazione.</li></ol><details><summary>Metadati e diagnostiche completi</summary><pre tabindex="0" aria-label="Controllo completo della fonte">{metadata}</pre></details></section></main>
<footer>Pacchetto di revisione della fonte. Nessun indicatore calcolato; approvazione scientifica e pubblicazione restano separate dai controlli software.</footer></body></html>"""


def build_portal(source: Path, out_dir: Path, *, reference_year: int, field: str,
                 synthetic: bool = False) -> Path:
    """Audit source bytes and expose a complete new folder, never replacing evidence."""
    if out_dir.exists() or out_dir.is_symlink():
        raise FileExistsError("Choose a fresh portal destination; no overwrite")
    if not source.is_file():
        raise ValueError("Require an existing local NetCDF file")
    report = inspect_export(source, reference_year=reference_year, field=field)
    if "selected_values" not in report:
        raise ValueError("Choose an existing real numeric field explicitly")
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".utci-portal-", dir=out_dir.parent) as temporary:
        stage = Path(temporary) / "portal"
        (stage / "source").mkdir(parents=True)
        original = stage / "source" / "original.nc"
        shutil.copyfile(source, original)
        if sha256_file(original) != report["source_sha256"]:
            raise ValueError("Copied source differs from inspected bytes; discard the pack")
        (stage / "review.json").write_text(
            json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        (stage / "index.html").write_text(render(report, synthetic=synthetic), encoding="utf-8", newline="\n")
        manifest = {
            "schema_version": "0.5-utci-review-portal-manifest-1",
            "status": "technical_draft_do_not_publish",
            "entrypoint": "epah methodology utci-portal",
            "input_kind": "synthetic_declared" if synthetic else "unclassified_local_source",
            "reference_year": reference_year, "selected_field": field,
            "source_sha256": report["source_sha256"],
            "files_sha256": {name: sha256_file(stage / name)
                             for name in ("source/original.nc", "review.json", "index.html")},
            "scientific_approval": False, "publication_allowed": False,
            "aggregation_performed": False,
        }
        (stage / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        if sha256_file(source) != report["source_sha256"]:
            raise ValueError("Source changed during preparation; discard the pack")
        return publish_directory(stage, out_dir)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, required=True, help="Existing local NetCDF; no acquisition")
    parser.add_argument("--reference-year", type=int, required=True)
    parser.add_argument("--field", required=True, help="Explicit numeric field for source review")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--synthetic", action="store_true", help="Label declared synthetic input prominently")
    args = parser.parse_args(argv)
    try:
        result = build_portal(args.file, args.out_dir, reference_year=args.reference_year,
                              field=args.field, synthetic=args.synthetic)
    except (ValueError, OSError, TypeError, KeyError, RuntimeError) as exc:
        parser.exit(2, f"BLOCKED: {exc}\n")
    print(f"Pacchetto UTCI di revisione pronto: {result / 'index.html'}; nessuna approvazione scientifica.")
    return 0
