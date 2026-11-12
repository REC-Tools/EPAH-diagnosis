"""Separate v0.3 visual atlas. Render only available evidence, never promote it.

The nine technical pilot indicators are read through the audited v0.2 bundle
validator. H47/H50/H46/H03 are separate optional, strictly QA-checked inputs.
No legacy map PNGs, canonical data or prior review directories are modified.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import statistics
import tempfile
import unicodedata
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.patches import Patch, PathPatch
from pyproj import Transformer

from epah_diagnosis.cartography import _oriented_polygon_path, _polygons, check_source_crs
from epah_diagnosis.release_artifacts import check_geojson, SNAI_COLORS
from epah_diagnosis.report_v0_2 import verified_data

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data/municipalities.csv"
RELEASE_CONFIG = ROOT / "config/release_v0_1.json"
STATUS = "technical_draft_do_not_publish"
PROJECTION = "EPSG:32632"


@dataclass(frozen=True)
class Metric:
    id: str
    name: str
    unit: str
    year_field: str
    value_field: str
    category: str
    family: str
    description: str
    source: str


BASE = (
    Metric("population_65_plus", "Residenti con 65 anni e più", "%", "population_65_plus_year", "population_65_plus_pct", "numeric", "Demografia", "Quota di residenti di almeno 65 anni, non incidenza di povertà energetica.", "ISTAT / POSAS · pilota v0.1"),
    Metric("income_vulnerability", "Contribuenti con reddito fino a 15.000 €", "%", "income_vulnerability_year", "income_vulnerability_pct", "numeric", "Economia", "Contribuenti fiscali, non famiglie; anno riportato nel bundle.", "MEF IRPEF · pilota v0.1"),
    Metric("old_building_stock", "Edifici residenziali precedenti al 1981", "%", "old_building_stock_year", "old_building_stock_pct", "numeric", "Edifici", "Patrimonio storico, non prestazione energetica misurata.", "ISTAT 2011 · pilota v0.1"),
    Metric("heating_degree_days", "Gradi-giorno normativi DPR 412", "GG", "heating_degree_days_year", "heating_degree_days", "numeric", "Clima", "Indicatore normativo statico. NON confondere con HDD climatici osservati 2025.", "DPR 412/1993 · pilota v0.1"),
    Metric("mean_altitude", "Altitudine media comunale", "m", "mean_altitude_year", "mean_altitude_m", "numeric", "Territorio", "Descrittore geomorfologico, senza direzione di benessere.", "ISTAT · pilota v0.1"),
    Metric("dea_accessibility", "Tempo stradale verso DEA I/II", "min", "dea_access_year", "dea_access_minutes", "numeric", "Servizi", "Tempo su matrice stradale, non tempo TPL o ambulanza.", "ISTAT / revisione accessibilità · pilota"),
    Metric("upper_secondary_accessibility", "Tempo stradale verso scuola superiore", "min", "upper_secondary_access_year", "upper_secondary_access_minutes", "numeric", "Servizi", "Accesso stradale stimato, non accesso senza automobile.", "ISTAT / MIM · pilota v0.1"),
    Metric("rail_accessibility", "Tempo stradale verso ferrovia", "min", "rail_access_year", "rail_access_minutes", "numeric", "Servizi", "Accesso stradale a gateway, non frequenza treni o uso TPL.", "ISTAT / gateway · pilota v0.1"),
    Metric("snai_classification", "Classe SNAI 2020", "categoria", "snai_year", "snai_class", "categorical", "Territorio", "Classificazione istituzionale A–F, NON punteggio numerico.", "SNAI 2020 · pilota v0.1"),
)
EXTRA = (
    Metric("H47", "Residenti 0–11 anni", "%", "reference_date", "share_0_11_pct", "numeric", "Demografia", "Proxy demografico; stima provvisoria ISTAT 2026. Richiede l'artefatto QA aggiornato.", "ISTAT POSAS 2026 · anteprima tecnica"),
    Metric("H50", "Adulti 25–64 senza licenza media", "%", "reference_year", "share_below_lower_secondary_25_64_pct", "numeric", "Economia", "Senza titolo o sola elementare; NON include licenza media. Mapping ISTAT ancora da approvare.", "ISTAT Censimento 2024 · anteprima tecnica"),
    Metric("H46", "Disoccupati sulle forze di lavoro 15+", "%", "reference_year", "unemployment_rate_15_plus_pct", "numeric", "Economia", "Denominatore: occupati + disoccupati; inattivi esclusi. Stime ISTAT decimali, non arrotondate. Revisione scientifica del mapping pendente.", "ISTAT Censimento 2024 · anteprima tecnica"),
    Metric("H03", "HDD climatici stimati 2025", "°C·giorno", "reference_year", "hdd_eurostat_estimated_c_days", "numeric", "Clima", "Griglia ARPA 2025, Eurostat 15/18; approssimazione Tmin/Tmax; NON GG normativi.", "ARPA NWIOI 2025 · anteprima tecnica"),
)
METRICS = BASE + EXTRA
EXTRA_CSV = {
    "H50": "low_education_25_64_preview.csv",
    "H46": "unemployment_15_plus_preview.csv",
    "H03": "hdd_eurostat_annual_preview.csv",
}


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def byte_sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def norm_name(name: str) -> str:
    value = unicodedata.normalize("NFKD", name.casefold())
    return "".join(c for c in value if c.isalnum() and not unicodedata.combining(c))


def read_registry(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    entries = {r["istat_code"]: r["municipality"] for r in rows}
    if (len(rows) != 27 or len(entries) != 27
            or any(len(c) != 6 or not c.isdigit() for c in entries)):
        raise ValueError("Registry must have exactly 27 unique six-digit ISTAT codes")
    return entries


def read_csv_bytes(data: bytes) -> list[dict[str, str]]:
    with io.StringIO(data.decode("utf-8-sig"), newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("Missing or duplicate CSV headers")
        rows = list(reader)
    if any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError("Malformed CSV row")
    return rows


def parse_int(value: str, location: str) -> int:
    if not value.isdecimal() or not value.isascii():
        raise ValueError(f"{location}: required nonnegative integer")
    return int(value)


def parse_estimate(value: str, location: str) -> float:
    """Non-negative decimal: ISTAT census register estimates are not integers."""
    text = value.strip()
    if text != value or not text.isascii() or not text.replace(".", "", 1).isdecimal():
        raise ValueError(f"{location}: required nonnegative number")
    number = float(text)
    if not math.isfinite(number):
        raise ValueError(f"{location}: required finite nonnegative number")
    return number


def parse_value(text: str, metric: Metric) -> float | str:
    if metric.category == "categorical":
        if text not in SNAI_COLORS:
            raise ValueError(f"Invalid SNAI category {text!r}")
        return text
    if text.strip() != text or not text:
        raise ValueError(f"Missing or padded value for {metric.id}")
    try:
        value = float(text)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Non-numeric value for {metric.id}: {text!r}") from exc
    if not math.isfinite(value) or value < 0 or (metric.unit == "%" and value > 100):
        raise ValueError(f"Out-of-range observation for {metric.id}: {text!r}")
    return value


def check_preview(rows: list[dict[str, str]], metric: Metric,
                  registry: dict[str, str]) -> dict[str, dict]:
    if len(rows) != 27:
        raise ValueError(f"{metric.id}: expected exactly 27 rows")
    expected_year = {"H47": "2026-01-01", "H50": "2024", "H46": "2024", "H03": "2025"}[metric.id]
    result = {}
    for r in rows:
        code = (r.get("municipality_code") or "").strip()
        if code not in registry or code in result:
            raise ValueError(f"{metric.id}: invalid or duplicate code {code!r}")
        if norm_name(r.get("municipality", "")) != norm_name(registry[code]):
            raise ValueError(f"{metric.id}: municipality name/code mismatch {code}")
        if r.get("status") != STATUS or r.get(metric.year_field) != expected_year:
            raise ValueError(f"{metric.id}: invalid status/year for {code}")
        value = parse_value(r.get(metric.value_field, ""), metric)
        if metric.id == "H47":
            numerator = parse_int(r.get("population_0_11", ""), code)
            denominator = parse_int(r.get("population_total", ""), code)
        elif metric.id == "H50":
            numerator = parse_int(r.get("residents_below_lower_secondary_25_64", ""), code)
            denominator = parse_int(r.get("residents_25_64_total", ""), code)
        elif metric.id == "H46":
            numerator = parse_estimate(r.get("unemployed_15_plus", ""), code)
            denominator = parse_estimate(r.get("labour_force_15_plus", ""), code)
            employed = parse_estimate(r.get("employed_15_plus", ""), code)
            if not math.isclose(employed + numerator, denominator, rel_tol=0, abs_tol=1e-6):
                raise ValueError(f"{metric.id}: invalid labour force for {code}")
        else:
            numerator, denominator = None, None
            if r.get("temperature_days") != "365":
                raise ValueError("H03 requires 365 complete days in 2025")
        if numerator is not None:
            if denominator <= 0 or numerator > denominator or abs(100 * numerator / denominator - float(value)) > 0.011:
                raise ValueError(f"{metric.id}: percentage numerator/denominator mismatch {code}")
        result[code] = {"value": value, "year": expected_year}
    if set(result) != set(registry):
        raise ValueError(f"{metric.id}: incomplete municipal coverage")
    return result


def require_review(qa: dict, manifest: dict, metric: Metric,
                   csv_name: str, csv_bytes: bytes, qa_bytes: bytes,
                   registry_path: Path) -> None:
    if (qa.get("status") != STATUS or manifest.get("status") != STATUS
            or manifest.get("scientific_approval") is not False
            or (manifest.get("canonical_registry_modified") is not False if metric.id == "H47"
                else manifest.get("canonical_data_modified") is not False)):
        raise ValueError(f"{metric.id}: missing technical-only QA status")
    if manifest.get("municipality_registry_sha256") != file_sha(registry_path):
        raise ValueError(f"{metric.id}: municipality registry hash mismatch")
    hashes = manifest.get("outputs_sha256", {})
    if hashes.get(csv_name) != byte_sha(csv_bytes) or hashes.get("qa.json") != byte_sha(qa_bytes):
        raise ValueError(f"{metric.id}: output SHA-256 mismatch")
    qa_id = qa.get("epah_inventory_id", qa.get("indicator_inventory_id"))
    if qa_id != metric.id:
        raise ValueError(f"{metric.id}: mismatching QA indicator id")
    if (metric.id == "H50" and manifest.get("normalized_export_mapping_verified") is not False
            or metric.id == "H46" and manifest.get("official_source_mapping_verified") is not False
            or metric.id == "H03" and manifest.get("raw_netcdf_temporal_and_spatial_consistency_verified") is not False):
        raise ValueError(f"{metric.id}: unexpected methodological status")


def load_review_dir(path: Path, metric: Metric,
                    registry: dict[str, str], registry_path: Path) -> tuple[dict, dict]:
    filename = EXTRA_CSV[metric.id]
    candidate = path / filename
    qa_file, manifest_file = path / "qa.json", path / "manifest.json"
    data_bytes, qa_bytes = candidate.read_bytes(), qa_file.read_bytes()
    qa = json.loads(qa_bytes)
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    require_review(qa, manifest, metric, filename, data_bytes, qa_bytes, registry_path)
    values = check_preview(read_csv_bytes(data_bytes), metric, registry)
    evidence = {"preview_sha256": byte_sha(data_bytes),
                "manifest_sha256": file_sha(manifest_file),
                "evidence_level": "technical_candidate_unreviewed_mapping",
                "input_location": str(path)}
    return values, evidence


def load_h47_zip(path: Path, metric: Metric, registry: dict[str, str],
                 registry_path: Path) -> tuple[dict, dict]:
    if path.stat().st_size > 20 * 1024 * 1024:
        raise ValueError("Oversized H47 artifact; expected GitHub review ZIP")
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        expected = {"h47_preview/population_0_11_preview.csv", "h47_preview/qa.json",
                    "h47_preview/manifest.json", "source_observation.json",
                    "h47_independent_reproduction_audit.json"}
        if not expected <= names or len(names) > 10:
            raise ValueError("H47 requires the NEW GitHub review artifact with independent audit (PR #143), not the initial ZIP")
        if any(z.getinfo(name).file_size > 2 * 1024 * 1024 for name in expected):
            raise ValueError("Unexpected H47 artifact member size")
        audited_bytes = {name: z.read(name) for name in expected
                         if name != "h47_independent_reproduction_audit.json"}
        csv_bytes = audited_bytes["h47_preview/population_0_11_preview.csv"]
        qa_bytes = audited_bytes["h47_preview/qa.json"]
        manifest = json.loads(audited_bytes["h47_preview/manifest.json"])
        qa = json.loads(qa_bytes)
        audit = json.loads(z.read("h47_independent_reproduction_audit.json"))
        observation = json.loads(audited_bytes["source_observation.json"])
    if (audit.get("schema_version") != "2.0"
            or audit.get("audited_files_sha256") != {
                name: byte_sha(data) for name, data in audited_bytes.items()}
            or audit.get("original_source_registry_sha256") != file_sha(registry_path)):
        raise ValueError("H47 audit receipt missing or stale: regenerate the schema 2.0 independent audit from the original source")
    require_review(qa, manifest, metric, "population_0_11_preview.csv", csv_bytes,
                   qa_bytes, registry_path)
    if (qa.get("sex_totals_verified") is not True
            or audit.get("status") != "independently_reproduced_technical_only"
            or audit.get("municipality_coverage") != "27/27"
            or audit.get("scientific_approval") is not False
            or audit.get("original_source_zip_sha256") != manifest.get("input_original_zip_sha256")
            or observation.get("original_zip_sha256") != manifest.get("input_original_zip_sha256")
            or observation.get("scientific_approval") is not False):
        raise ValueError("H47 requires verified sex totals and consistent original-source audit")
    values = check_preview(read_csv_bytes(csv_bytes), metric, registry)
    return values, {"preview_sha256": byte_sha(csv_bytes), "input_artifact_sha256": file_sha(path),
                    "original_source_zip_sha256": audit["original_source_zip_sha256"],
                    "evidence_level": "independently_reproduced_technical_only", "input_location": str(path)}


def load_pilot(bundle: Path, registry_path: Path, release_config: Path) -> tuple[dict, dict, dict]:
    profiles, manifest = verified_data(bundle, registry_path, release_config)
    registry = read_registry(registry_path)
    features = json.loads((bundle / "municipality_profile.geojson").read_text(encoding="utf-8"))
    check_source_crs(features)
    check_geojson(features, {v: k for k, v in registry.items()}, enriched=True)
    by_name = {norm_name(item["municipality"]): item for item in profiles}
    data = {}
    for code, name in registry.items():
        record = by_name.get(norm_name(name))
        if record is None:
            raise ValueError(f"Missing pilot municipality {code} {name}")
        values = {}
        for metric in BASE:
            values[metric.id] = {"value": parse_value(str(record[metric.value_field]), metric),
                                 "year": str(record[metric.year_field])}
        data[code] = {"code": code, "name": name, "values": values}
    return data, features, {"release_manifest_sha256": file_sha(bundle / "release_manifest.json"),
                            "bundle_profile_sha256": file_sha(bundle / "municipality_profile.csv"),
                            "geometry_sha256": file_sha(bundle / "municipality_profile.geojson"),
                            "source_scope": "technical_pilot_v0.1_snapshot_9_indicators"}


def _make_map(features: dict, metric: Metric, values: dict, output: Path, fmt: str) -> None:
    transformer = Transformer.from_crs("EPSG:4326", PROJECTION, always_xy=True)
    present = [r["value"] for r in values.values()]
    categorical = metric.category == "categorical"
    if not present:
        return
    fig, ax = plt.subplots(figsize=(9.4, 7.3), facecolor="#FFFFFF")
    try:
        if not categorical:
            span_min, span_max = min(present), max(present)
            if span_min == span_max:
                span_min -= .5
                span_max += .5
            color_scale = Normalize(vmin=span_min, vmax=span_max)
            colors = plt.get_cmap("cividis")
        for feature in features["features"]:
            code = feature["properties"]["municipality_code"]
            val = values.get(code)
            face = (SNAI_COLORS[val["value"]] if categorical else colors(color_scale(val["value"]))) if val else "#E5E7EB"
            for rings in _polygons(feature["geometry"]):
                ax.add_patch(PathPatch(_oriented_polygon_path(rings, transformer),
                                       facecolor=face, edgecolor="#FFFFFF", linewidth=.45))
        ax.autoscale_view()
        ax.set_aspect("equal", adjustable="box")
        ax.set_axis_off()
        ax.set_title(metric.name, loc="left", fontsize=17, fontweight="semibold", color="#0F2940", pad=17)
        if categorical:
            legend = [Patch(facecolor=SNAI_COLORS[k], label="SNAI " + k) for k in sorted(set(present))]
            ax.legend(handles=legend, loc="upper left", bbox_to_anchor=(0, -.01),
                      ncol=min(6, len(legend)), frameon=False, fontsize=9)
        else:
            fig.colorbar(plt.cm.ScalarMappable(norm=color_scale, cmap=colors),
                         ax=ax, fraction=.033, pad=.024, shrink=.74, label=metric.unit)
        fig.text(.07, .075, f"{metric.source}  |  Copertura: {len(values)}/27  |  valori assoluti", fontsize=9, color="#405267")
        fig.text(.07, .045, "Anteprima tecnica v0.3 • Non è una mappa della povertà energetica • NON PUBBLICARE", fontsize=8, color="#64748B")
        output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output, format=fmt, dpi=170, facecolor="white", bbox_inches="tight", pad_inches=.24)
    finally:
        plt.close(fig)


def _make_distribution(metric: Metric, values: dict, registry: dict, output: Path, fmt: str) -> None:
    fig, ax = plt.subplots(figsize=(9.4, 8.8 if metric.category == "numeric" else 5.8))
    try:
        if metric.category == "categorical":
            counts = Counter(r["value"] for r in values.values())
            labels = list("ABCDEF")
            ax.bar(labels, [counts.get(k, 0) for k in labels], color=[SNAI_COLORS[k] for k in labels])
            ax.set_ylabel("Numero di Comuni")
            for i, label in enumerate(labels):
                ax.text(i, counts.get(label, 0) + .15, str(counts.get(label, 0)), ha="center", fontsize=9)
        else:
            ordered = sorted(((r["value"], registry[k]) for k, r in values.items()), key=lambda x: x[0])
            med = statistics.median(x for x, _ in ordered)
            ax.scatter([x for x, _ in ordered], range(len(ordered)), color="#16708B", s=40, zorder=3)
            ax.set_yticks(list(range(len(ordered))), [name for _, name in ordered], fontsize=8)
            ax.axvline(med, color="#BB6F31", linestyle="--", lw=1.5,
                       label=f"Mediana comunale (n={len(ordered)}): {med:.2f} {metric.unit}")
            ax.legend(loc="lower right", frameon=False, fontsize=9)
            ax.set_xlabel(metric.unit)
            ax.set_ylim(-.8, len(ordered) - .2)
        ax.grid(axis="x" if metric.category == "numeric" else "y", alpha=.16)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.set_title("Distribuzione · " + metric.name, loc="left", color="#0F2940", fontsize=15, pad=17)
        fig.text(.12, .01, "Confronti descrittivi, senza soglie di rischio • Anteprima tecnica NON PUBBLICARE", fontsize=8, color="#64748B")
        fig.savefig(output, format=fmt, dpi=170, bbox_inches="tight", facecolor="white", pad_inches=.22)
    finally:
        plt.close(fig)


def _atlas_html(payload: dict) -> str:
    safe = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), allow_nan=False)
    safe = safe.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    template = '''<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>EPAH | Atlante territoriale v0.3</title><style>
:root{--navy:#132d45;--ink:#1d3345;--muted:#556b78;--line:#dbe4e7;--pale:#f2f6f7;--accent:#137d91;--warn:#916126}
*{box-sizing:border-box}body{font:15px/1.5 system-ui,-apple-system,'Segoe UI',sans-serif;margin:0;background:var(--pale);color:var(--ink)}
header{padding:28px max(calc((100vw - 1160px)/2),24px);background:var(--navy);color:#fff}h1{margin:.1em 0;font-size:clamp(1.8rem,3vw,2.8rem);font-weight:650}header p{opacity:.85;margin:.4em 0}
main{max-width:1160px;margin:24px auto;padding:0 22px 50px}.intro,.panel{background:white;border:1px solid var(--line);border-radius:12px;padding:22px;margin-bottom:18px}
.statgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:0 0 18px}.stat{padding:18px;background:#fff;border-radius:11px;border:1px solid var(--line)}.stat strong{display:block;font-size:2rem;color:var(--navy)}
.note{color:var(--muted);font-size:.89rem}.notice{border-left:4px solid var(--warn);padding:10px 15px;background:#fffaf0}label{display:block;font-weight:650;margin-bottom:6px}
select,input{width:100%;padding:11px;border:1px solid #a7b9bf;border-radius:7px;font:inherit;color:var(--ink);background:white}
.controls{display:grid;grid-template-columns:2fr 1fr;gap:18px}.media{display:grid;grid-template-columns:1fr 1fr;gap:18px}.media img{width:100%;height:auto;border:1px solid var(--line);border-radius:7px}
.media figure{margin:0;min-width:0}.media figcaption{padding-top:8px;font-size:.86rem;color:var(--muted)}a{color:#006e8c}a:focus,select:focus,input:focus{outline:3px solid #b1d9e3}
#indicator-status{font-weight:650;margin:15px 0}table{border-collapse:collapse;width:100%}td,th{padding:8px 10px;text-align:left;border-bottom:1px solid var(--line)}th{background:#f2f7f8}td:last-child,th:last-child{text-align:right;font-variant-numeric:tabular-nums}tbody tr:hover{background:#f7fafb}
.tablewrap{max-height:600px;overflow:auto}.pending{padding:34px;background:#f6f7f8;border:1px dashed #bbc6ce;color:var(--muted);border-radius:8px}.hidden{display:none}
footer{color:var(--muted);text-align:center;padding:25px}
@media(max-width:780px){.media,.controls{grid-template-columns:1fr}.statgrid{grid-template-columns:repeat(3,1fr)}.stat strong{font-size:1.45rem}}@media(max-width:500px){.statgrid{grid-template-columns:1fr}}
</style></head><body>
<header><small>EPAH TECHNICAL ASSISTANCE · Sinergie in Canavese</small><h1>Atlante territoriale v0.3</h1><p>27 Comuni · Indicatori autonomi · Diagnosi esplorativa</p></header>
<main><section class="intro"><div class="notice"><strong>BOZZA TECNICA — NON PUBBLICARE.</strong> Non misura la povertà energetica familiare, non produce indici compositi o graduatorie di bisogno. Le osservazioni hanno anni e definizioni eterogenei.</div><p class="note" id="identical-note"></p></section>
<section class="statgrid"><div class="stat">Indicatori previsti<strong id="total">13</strong></div><div class="stat">Serie disponibili<strong id="available">—</strong></div><div class="stat">Comuni<strong>27</strong></div></section>
<section class="panel"><div class="controls"><div><label for="indicator">Indicatore</label><select id="indicator"></select></div><div><label for="search">Cerca Comune</label><input id="search" type="search" placeholder="Nome o codice ISTAT"></div></div>
<p id="indicator-status" aria-live="polite"></p><p id="indicator-note" class="note"></p><p id="source-note" class="note"></p></section>
<section class="panel"><h2>Mappe e distribuzione</h2><div id="graphs" class="media"></div><div id="pending" class="pending hidden">Valori comunali non ancora disponibili: nessuna mappa né grafico viene inventato.</div></section>
<section class="panel"><h2>Valori comunali</h2><p class="note">La mediana nei grafici è descrittiva, non una soglia di vulnerabilità. I Comuni sono presentati senza punteggio complessivo.</p><div class="tablewrap"><table><thead><tr><th>Comune</th><th>Codice ISTAT</th><th>Anno</th><th>Valore</th></tr></thead><tbody id="rows"></tbody></table></div></section>
</main><footer>EPAH v0.3 · Uso interno FERVORES / Unione Montana · Fonte e QA in atlas_manifest.json</footer>
<script type="application/json" id="data">__PAYLOAD__</script><script>
'use strict';const data=JSON.parse(document.getElementById('data').textContent);const $=id=>document.getElementById(id);const select=$('indicator');
$('available').textContent=data.indicators.filter(x=>x.available).length;
$('identical-note').textContent=data.identical_numeric_series.length?'Attenzione: alcune serie comunali del pilota risultano identiche fra loro. Consultare atlas_manifest.json prima di interpretarle come evidenze indipendenti.':'';
for(const i of data.indicators){const opt=document.createElement('option');opt.value=i.id;opt.textContent=i.name+(i.available?' · '+i.count+'/27':' · DATI ASSENTI');select.append(opt)}
function text(parent,tag,content){const el=document.createElement(tag);el.textContent=content;parent.append(el);return el}
function draw(){const item=data.indicators.find(i=>i.id===select.value);$('indicator-status').textContent=item.available?'Anteprima tecnica · '+item.count+'/27 Comuni':'DATI ASSENTI — pipeline disponibile, elaborazione non acquisita';$('indicator-note').textContent=item.description;$('source-note').textContent='Fonte: '+item.source+' · '+(item.years.join(', ')||'anno non disponibile');
const graphs=$('graphs');graphs.replaceChildren();$('pending').classList.toggle('hidden',item.available);
if(item.available){for(const kind of ['map','distribution']){const fig=document.createElement('figure');const img=document.createElement('img');img.src='charts/'+item.id+'_'+kind+'.png';img.alt=(kind==='map'?'Mappa tematica di ':'Distribuzione comunale di ')+item.name;fig.append(img);const cap=document.createElement('figcaption');for(const format of ['png','svg']){const a=document.createElement('a');a.href='charts/'+item.id+'_'+kind+'.'+format;a.textContent='Apri '+format.toUpperCase();cap.append(a);cap.append(document.createTextNode('  ·  '))}fig.append(cap);graphs.append(fig)}}
const q=$('search').value.toLocaleLowerCase('it-IT').trim();const body=$('rows');body.replaceChildren();for(const r of data.municipalities){if(q&&!r.name.toLocaleLowerCase('it-IT').includes(q)&&!r.code.includes(q))continue;const tr=document.createElement('tr');const v=r.values[item.id];text(tr,'td',r.name);text(tr,'td',r.code);text(tr,'td',v?v.year:'—');text(tr,'td',v?(typeof v.value==='number'?new Intl.NumberFormat('it-IT',{maximumFractionDigits:2}).format(v.value):v.value)+' '+item.unit:'n.d.');body.append(tr)}}
select.addEventListener('change',draw);$('search').addEventListener('input',draw);draw();
</script></body></html>'''
    return template.replace("__PAYLOAD__", safe)


def build(bundle: Path, out_dir: Path, *, registry_path: Path = REGISTRY,
          release_config: Path = RELEASE_CONFIG,
          h47_zip: Path | None = None, h50_dir: Path | None = None,
          h46_dir: Path | None = None, h03_dir: Path | None = None) -> Path:
    if out_dir.exists():
        raise FileExistsError("Choose a NEW --out-dir; existing evidence cannot be overwritten")
    source_paths = [bundle, registry_path, release_config, *(p for p in
                    (h47_zip, h50_dir, h46_dir, h03_dir) if p is not None)]
    destination = out_dir.resolve()
    if any(destination.is_relative_to(p.resolve()) for p in source_paths
           if p.is_dir()):
        raise ValueError("Output directory must not be inside an input/evidence folder")
    registry = read_registry(registry_path)
    municipalities, geometry, pilot_evidence = load_pilot(bundle, registry_path, release_config)
    supplied = {"H47": h47_zip, "H50": h50_dir, "H46": h46_dir, "H03": h03_dir}
    evidence = {"pilot": pilot_evidence}
    for metric in EXTRA:
        location = supplied[metric.id]
        if location is None:
            continue
        rows, proof = (load_h47_zip(location, metric, registry, registry_path) if metric.id == "H47"
                       else load_review_dir(location, metric, registry, registry_path))
        for code, observation in rows.items():
            municipalities[code]["values"][metric.id] = observation
        evidence[metric.id] = proof
    identical_numeric_series = []
    for i, first in enumerate(BASE):
        if first.category != "numeric":
            continue
        for second in BASE[i + 1:]:
            if (second.category == "numeric" and all(
                    municipalities[c]["values"][first.id]["value"] ==
                    municipalities[c]["values"][second.id]["value"] for c in registry)):
                identical_numeric_series.append([first.id, second.id])
    payload = {
        "status": STATUS, "publication_allowed": False, "no_composite_score": True,
        "identical_numeric_series": identical_numeric_series,
        "municipality_count": 27,
        "indicators": [],
        "municipalities": [municipalities[c] for c in sorted(municipalities)],
    }
    for metric in METRICS:
        series = {c: record["values"][metric.id] for c, record in municipalities.items()
                  if metric.id in record["values"]}
        if series and len(series) != 27:
            raise ValueError(f"Partial indicator {metric.id}; expected full coverage")
        payload["indicators"].append({
            "id": metric.id, "name": metric.name, "unit": metric.unit,
            "family": metric.family, "description": metric.description,
            "source": metric.source, "available": bool(series), "count": len(series),
            "years": sorted({r["year"] for r in series.values()}),
            "evidence": "technical_pilot" if metric in BASE else "technical_v0_3_candidate" if series else "not_available",
        })
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".epah-v03-atlas-", dir=out_dir.parent) as td:
        stage = Path(td) / "atlas"
        (stage / "charts").mkdir(parents=True)
        for metric in METRICS:
            series = {c: r["values"][metric.id] for c, r in municipalities.items()
                      if metric.id in r["values"]}
            if not series:
                continue
            for kind, builder in (("map", _make_map), ("distribution", _make_distribution)):
                for suffix in ("png", "svg"):
                    target = stage / "charts" / f"{metric.id}_{kind}.{suffix}"
                    if kind == "map":
                        builder(geometry, metric, series, target, suffix)
                    else:
                        builder(metric, series, registry, target, suffix)
        (stage / "atlas_data.json").write_text(json.dumps(payload, ensure_ascii=False,
                indent=2, allow_nan=False) + "\n", encoding="utf-8")
        (stage / "index.html").write_text(_atlas_html(payload), encoding="utf-8")
        file_hashes = {str(p.relative_to(stage)).replace("\\", "/"): file_sha(p)
                       for p in sorted(stage.rglob("*")) if p.is_file()}
        manifest = {
            "status": STATUS, "publication_allowed": False, "no_composite_score": True,
            "municipalities": 27, "indicator_slots": 13,
            "indicators_available": [m["id"] for m in payload["indicators"] if m["available"]],
            "indicators_pending": [m["id"] for m in payload["indicators"] if not m["available"]],
            "visualization": "newly_rendered_metric_EPSG32632_not_legacy_png",
            "all_original_v0_2_maps_reused": False,
            "registry_sha256": file_sha(registry_path), "input_evidence": evidence,
            "identical_numeric_series_review": identical_numeric_series,
            "output_sha256": file_hashes,
            "limitations": "Old nine series reproduce technical v0.1 source values. Candidate H47/H50/H46/H03 are separate exploratory snapshots, not scientific approvals or measured household energy poverty.",
        }
        (stage / "atlas_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (stage / "README_REVIEW.txt").write_text(
            "EPAH v0.3 ATLANTE ESPLORATIVO - NON PUBBLICARE\n"
            "Aprire index.html in browser (offline). Mappe e grafici nuovi in charts/.\n"
            "9 serie dal pilota storico; H47/H50/H46/H03 solo se forniti con QA.\n"
            "I dati fonte dei 9 possono richiedere revisione: cambiare il renderer NON aggiorna i numeri.\n"
            "Consultare atlas_manifest.json per serie presenti/assenti e relative evidenze.\n",
            encoding="utf-8",
        )
        if out_dir.exists():
            raise FileExistsError("Output created concurrently; never overwrite")
        os.replace(stage, out_dir)
    return out_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=ROOT / "outputs/v0.1.0-pilot")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--release-config", type=Path, default=RELEASE_CONFIG)
    parser.add_argument("--h47-zip", type=Path, help="2026 POSAS review artifact with schema 2.0 independent audit receipt")
    parser.add_argument("--h50-dir", type=Path, help="H50 technical QA preview directory")
    parser.add_argument("--h46-dir", type=Path, help="H46 technical QA preview directory")
    parser.add_argument("--h03-dir", type=Path, help="H03 technical QA preview directory (h03_preview for NWIOI)")
    args = parser.parse_args()
    try:
        path = build(args.bundle, args.out_dir, registry_path=args.registry,
                     release_config=args.release_config, h47_zip=args.h47_zip,
                     h50_dir=args.h50_dir, h46_dir=args.h46_dir, h03_dir=args.h03_dir)
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        parser.exit(2, f"BLOCKED: {exc}\n")
    print(f"EPAH v0.3 visual review (not for publication): {path / 'index.html'}")
    print(f"Manifest: {path / 'atlas_manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
