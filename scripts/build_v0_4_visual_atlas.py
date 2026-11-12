"""v0.4 technical atlas extension, leaving the stable v0.3 builder untouched.

The verified v0.3 atlas is regenerated from its original inputs into a private
temporary directory. Three v0.4 slots are appended. Missing previews remain
explicitly unavailable; no synthetic municipal values are created.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date
from decimal import Decimal, InvalidOperation
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
V3_PATH = ROOT / "scripts/build_v0_3_visual_atlas.py"
spec = importlib.util.spec_from_file_location("epah_v03_atlas_for_v04", V3_PATH)
assert spec and spec.loader
v3 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = v3
spec.loader.exec_module(v3)

STATUS = "technical_draft_do_not_publish"
NEW = (
    v3.Metric("H04", "CDD climatici annui stimati 2025", "°C·giorno",
              "reference_year", "cdd_eurostat_estimated_c_days", "numeric", "Clima",
              "Stima Eurostat 24/21 su Tmin/Tmax ARPA; non misura discomfort, consumi o ondate di calore.",
              "ARPA NWIOI 2025 · anteprima tecnica"),
    v3.Metric("H05", "APE residenziali validi in classe F/G", "%",
              "reference_date", "value_pct", "numeric", "Edifici",
              "Quota fra soli APE residenziali validi forniti nella fonte, non fra tutte le abitazioni.",
              "Piemonte SICEE/SIPEE o SIAPE · fonte da verificare"),
    v3.Metric("ADD-HOUSING-01", "Abitazioni non occupate da residenti", "%",
              "reference_date", "value_pct", "numeric", "Edifici",
              "Abitazioni non occupate da persone residenti: non equivale a case vuote o seconde case.",
              "ISTAT Censimento 2023 · fonte da verificare"),
)
HOUSING = {"H05": "h05_ape_fg", "ADD-HOUSING-01": "dwellings_not_occupied_by_residents"}


def _decimal(raw: str, *, integer: bool = False) -> Decimal:
    if (not isinstance(raw, str) or not raw or raw != raw.strip() or not raw.isascii()
            or raw.count(".") > 1 or not raw.replace(".", "", 1).isdigit()
            or integer and not raw.isdigit()):
        raise ValueError("Preview requires an explicit nonnegative finite decimal")
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError("Invalid decimal observation") from exc
    if not value.is_finite() or value < 0:
        raise ValueError("Invalid or negative observation")
    return value


def _review(path: Path, filename: str, indicator: str, registry_path: Path,
            *, climate: bool) -> tuple[list[dict[str, str]], dict]:
    candidate, qa_file, manifest_file = (path / filename, path / "qa.json", path / "manifest.json")
    data = candidate.read_bytes()
    qa_bytes = qa_file.read_bytes()
    qa = json.loads(qa_bytes)
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if (qa.get("status") != STATUS or manifest.get("status") != STATUS
            or manifest.get("scientific_approval") is not False
            or manifest.get("canonical_data_modified") is not False
            or manifest.get("municipality_registry_sha256") != v3.file_sha(registry_path)
            or manifest.get("outputs_sha256", {}).get(filename) != v3.byte_sha(data)
            or manifest.get("outputs_sha256", {}).get("qa.json") != v3.byte_sha(qa_bytes)):
        raise ValueError(f"{indicator}: candidate QA, registry or manifest mismatch")
    if climate:
        if (qa.get("epah_inventory_id") != "H04"
                or manifest.get("source_to_municipality_mapping_verified") is not False
                or manifest.get("indicator_id") != "H04"):
            raise ValueError("H04: expected unapproved source mapping")
    else:
        if (manifest.get("indicator_id") != indicator
                or manifest.get("source_mapping_verified") is not False
                or qa.get("qa", {}).get("source_mapping_verified") is not False):
            raise ValueError(f"{indicator}: expected unreviewed source mapping")
        if indicator == "h05_ape_fg" and qa.get("qa", {}).get("residential_filter_verified") is not False:
            raise ValueError("H05: residential filter may not be assumed validated")
    for key in (("original_tmin_netcdf_sha256", "original_tmax_netcdf_sha256",
                 "normalized_daily_csv_sha256") if climate
                else ("original_export_sha256", "normalized_csv_sha256")):
        digest = manifest.get(key)
        if (not isinstance(digest, str) or len(digest) != 64
                or any(c not in "0123456789abcdef" for c in digest)):
            raise ValueError(f"{indicator}: source identity digest missing")
    rows = v3.read_csv_bytes(data)
    if len(rows) != 27:
        raise ValueError(f"{indicator}: expected 27 municipal observations")
    receipt = {"preview_sha256": v3.byte_sha(data),
               "manifest_sha256": v3.file_sha(manifest_file),
               "evidence_level": "technical_candidate_unreviewed_source_mapping",
               "input_location": str(path),
               "original_source_sha256": manifest.get("original_export_sha256"),
               "normalized_daily_csv_sha256": manifest.get("normalized_daily_csv_sha256")}
    return rows, {"receipt": receipt, "manifest": manifest, "qa": qa}


def _check_scope(rows: list[dict], registry: dict[str, str]) -> dict[str, dict]:
    indexed = {}
    for row in rows:
        code = row.get("municipality_code")
        if (code not in registry or code in indexed
                or v3.norm_name(row.get("municipality", "")) != v3.norm_name(registry[code])):
            raise ValueError("Duplicate or mismatched municipality in candidate preview")
        if row.get("status") != STATUS:
            raise ValueError("Candidate is not marked as technical-only")
        indexed[code] = row
    if set(indexed) != set(registry):
        raise ValueError("Candidate does not cover all 27 registered municipalities")
    return indexed


def load_h04(path: Path, h03_dir: Path, registry: dict[str, str],
             registry_path: Path) -> tuple[dict, dict]:
    rows, info = _review(path, "cdd_eurostat_annual_preview.csv", "H04",
                         registry_path, climate=True)
    h03_manifest = json.loads((h03_dir / "manifest.json").read_text(encoding="utf-8"))
    h04_manifest = info["manifest"]
    keys = ("normalized_daily_csv_sha256", "original_tmin_netcdf_sha256",
            "original_tmax_netcdf_sha256")
    if any(h03_manifest.get(key) != h04_manifest.get(key) for key in keys):
        raise ValueError("H03/H04 must use the exact same normalized daily Tmin/Tmax inputs")
    h03_rows = _check_scope(v3.read_csv_bytes(
        (h03_dir / "hdd_eurostat_annual_preview.csv").read_bytes()), registry)
    h04_rows = _check_scope(rows, registry)
    values = {}
    for code, row in h04_rows.items():
        h03 = h03_rows[code]
        if (row.get("reference_year") != "2025"
                or h03.get("reference_year") != row.get("reference_year")
                or row.get("temperature_days") != "365"
                or any(row.get(field) != h03.get(field) for field in (
                    "temperature_days", "grid_cell_id", "grid_latitude", "grid_longitude"))):
            raise ValueError(f"H03/H04 {code}: year, coverage or cell selection mismatch")
        amount = _decimal(row.get("cdd_eurostat_estimated_c_days"))
        values[code] = {"value": float(amount), "year": "2025"}
    return values, info["receipt"]


def load_housing(path: Path, kind: str, registry: dict[str, str],
                 registry_path: Path) -> tuple[dict, dict]:
    source_id = HOUSING[kind]
    rows, info = _review(path, source_id + "_preview.csv", source_id,
                         registry_path, climate=False)
    indexed = _check_scope(rows, registry)
    values = {}
    periods = set()
    for code, row in indexed.items():
        if row.get("indicator_id") != source_id:
            raise ValueError(f"{kind}: mismatching candidate indicator ID")
        period = row.get("reference_date")
        try:
            parsed = date.fromisoformat(period)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"{kind}/{code}: invalid reference date") from exc
        if parsed.isoformat() != period or kind == "ADD-HOUSING-01" and period != "2023-12-31":
            raise ValueError(f"{kind}/{code}: incorrect reference period")
        periods.add(period)
        numerator = _decimal(row.get("numerator"), integer=True)
        denominator = _decimal(row.get("denominator"), integer=True)
        percent = _decimal(row.get("value_pct"))
        if (denominator <= 0 or numerator > denominator or percent > 100
                or abs(percent - Decimal(100) * numerator / denominator) > Decimal("0.011")):
            raise ValueError(f"{kind}/{code}: numerator/denominator reconciliation mismatch")
        values[code] = {
            "value": float(percent), "year": period,
            "numerator": row["numerator"], "denominator": row["denominator"],
            "universe": ("valid_residential_ape_certificates" if kind == "H05"
                         else "census_dwellings_2023"),
        }
    if len(periods) != 1:
        raise ValueError(f"{kind}: mixed municipal reference dates")
    return values, info["receipt"]


def build(bundle: Path, out_dir: Path, *, registry_path: Path = v3.REGISTRY,
          release_config: Path = v3.RELEASE_CONFIG, h47_zip: Path | None = None,
          h50_dir: Path | None = None, h46_dir: Path | None = None,
          h03_dir: Path | None = None, h04_dir: Path | None = None,
          h05_dir: Path | None = None, housing_dir: Path | None = None) -> Path:
    if out_dir.exists():
        raise FileExistsError("Choose a fresh v0.4 atlas output directory")
    if h04_dir is not None and h03_dir is None:
        raise ValueError("H04 requires the H03 review directory from the same source")
    sources = (bundle, registry_path, release_config, h47_zip, h50_dir, h46_dir,
               h03_dir, h04_dir, h05_dir, housing_dir)
    if any(out_dir.resolve().is_relative_to(p.resolve()) for p in sources if p is not None):
        raise ValueError("Output directory must not be nested in the source folders")
    registry = v3.read_registry(registry_path)
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".epah-v04-atlas-", dir=out_dir.parent) as temporary:
        work = Path(temporary)
        old = work / "v03"
        v3.build(bundle, old, registry_path=registry_path, release_config=release_config,
                 h47_zip=h47_zip, h50_dir=h50_dir, h46_dir=h46_dir, h03_dir=h03_dir)
        payload = json.loads((old / "atlas_data.json").read_text(encoding="utf-8"))
        manifest = json.loads((old / "atlas_manifest.json").read_text(encoding="utf-8"))
        if (manifest.get("registry_sha256") != v3.file_sha(registry_path)
                or manifest.get("output_sha256", {}).get("atlas_data.json") != v3.file_sha(old / "atlas_data.json")
                or payload.get("publication_allowed") is not False):
            raise ValueError("Generated v0.3 atlas integrity check failed")
        optional = {"H04": h04_dir, "H05": h05_dir, "ADD-HOUSING-01": housing_dir}
        new_values, evidence = {}, {}
        for metric in NEW:
            location = optional[metric.id]
            if location is None:
                continue
            values, proof = (load_h04(location, h03_dir, registry, registry_path)
                             if metric.id == "H04"
                             else load_housing(location, metric.id, registry, registry_path))
            new_values[metric.id] = values
            evidence[metric.id] = proof
        for item in payload["municipalities"]:
            for identifier, by_code in new_values.items():
                item["values"][identifier] = by_code[item["code"]]
        for metric in NEW:
            series = new_values.get(metric.id, {})
            payload["indicators"].append({
                "id": metric.id, "name": metric.name, "unit": metric.unit,
                "family": metric.family, "description": metric.description,
                "source": metric.source, "available": bool(series), "count": len(series),
                "years": sorted({r["year"] for r in series.values()}),
                "evidence": "technical_v0_4_candidate_unreviewed" if series else "not_available",
            })
        if len(payload["indicators"]) != len(v3.METRICS) + len(NEW):
            raise ValueError("Unexpected atlas inventory")
        payload["schema_version"] = "0.4-technical-atlas"
        payload["no_composite_score"] = True
        stage = work / "atlas"
        shutil.copytree(old, stage)
        geometry = json.loads((bundle / "municipality_profile.geojson").read_text(encoding="utf-8"))
        v3.check_source_crs(geometry)
        v3.check_geojson(geometry, {name: code for code, name in registry.items()}, enriched=True)
        for metric in NEW:
            series = new_values.get(metric.id, {})
            if not series:
                continue
            for kind, renderer in (("map", v3._make_map), ("distribution", v3._make_distribution)):
                for suffix in ("png", "svg"):
                    output = stage / "charts" / f"{metric.id}_{kind}.{suffix}"
                    if kind == "map":
                        renderer(geometry, metric, series, output, suffix)
                    else:
                        renderer(metric, series, registry, output, suffix)
        html = v3._atlas_html(payload)
        html = html.replace("Atlante territoriale v0.3", "Atlante territoriale v0.4")
        html = html.replace('Indicatori previsti<strong id="total">13</strong>',
                            f'Indicatori previsti<strong id="total">{len(payload["indicators"])}</strong>')
        html = html.replace("EPAH v0.3 · Uso interno", "EPAH v0.4 · Uso interno")
        if 'Indicatori previsti<strong id="total">13</strong>' in html:
            raise ValueError("Atlas HTML inventory was not updated")
        (stage / "index.html").write_text(html, encoding="utf-8")
        (stage / "atlas_data.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        manifest.update({
            "schema_version": "0.4-technical-atlas", "indicator_slots": len(payload["indicators"]),
            "indicators_available": [m["id"] for m in payload["indicators"] if m["available"]],
            "indicators_pending": [m["id"] for m in payload["indicators"] if not m["available"]],
            "input_evidence": {**manifest["input_evidence"], **evidence},
            "new_candidate_review_status": "technical_only_mapping_not_scientifically_approved",
            "no_composite_score": True, "publication_allowed": False,
        })
        manifest["output_sha256"] = {p.relative_to(stage).as_posix(): v3.file_sha(p)
                                      for p in sorted(stage.rglob("*"))
                                      if p.is_file() and p.name not in {"atlas_manifest.json", "README_REVIEW.txt"}}
        (stage / "atlas_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        (stage / "README_REVIEW.txt").write_text(
            "EPAH v0.4 ATLANTE TECNICO — NON PUBBLICARE\n"
            "16 slot: 9 indicatori pilota, 4 candidati v0.3, 3 slot nuovi H04/H05/ADD-HOUSING-01.\n"
            "Assenza fonte significa dato non acquisito; nessuna imputazione o approvazione scientifica.\n"
            "H04 richiede stesso dato giornaliero di H03; le classi APE non rappresentano l'intero patrimonio.\n"
            "Eseguire revisione delle fonti originali, geometria, periodo e limiti prima di condividere risultati.\n",
            encoding="utf-8")
        if out_dir.exists():
            raise FileExistsError("Output created concurrently")
        os.replace(stage, out_dir)
    return out_dir


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=ROOT / "outputs/v0.1.0-pilot")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=v3.REGISTRY)
    parser.add_argument("--release-config", type=Path, default=v3.RELEASE_CONFIG)
    parser.add_argument("--h47-zip", type=Path)
    parser.add_argument("--h50-dir", type=Path)
    parser.add_argument("--h46-dir", type=Path)
    parser.add_argument("--h03-dir", type=Path)
    parser.add_argument("--h04-dir", type=Path)
    parser.add_argument("--h05-dir", type=Path)
    parser.add_argument("--housing-dir", type=Path)
    args = parser.parse_args(argv)
    try:
        out = build(args.bundle, args.out_dir, registry_path=args.registry,
                    release_config=args.release_config, h47_zip=args.h47_zip,
                    h50_dir=args.h50_dir, h46_dir=args.h46_dir,
                    h03_dir=args.h03_dir, h04_dir=args.h04_dir,
                    h05_dir=args.h05_dir, housing_dir=args.housing_dir)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        parser.exit(2, f"BLOCKED: {exc}\n")
    print(f"v0.4 technical atlas (NOT for publication): {out / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
