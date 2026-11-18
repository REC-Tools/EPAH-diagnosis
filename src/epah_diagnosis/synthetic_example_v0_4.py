"""Deterministic fictional inputs exercising the production output chain.

This demonstration never acquires, verifies or substitutes territorial sources.
It has no dependency on pytest, private files or a source checkout.
"""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import tempfile


def _json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                    encoding="utf-8")


def _inputs(directory: Path):
    from . import visual_atlas_v0_4 as atlas
    from .release_artifacts import NUMERIC_FIELDS

    directory.mkdir()
    names = {f"001{i:03d}": ("Synthetic Vallè 01" if i == 1 else f"Synthetic Comune {i:02d}")
             for i in range(1, 28)}
    registry = directory / "municipalities.csv"
    registry.write_text("municipality,istat_code\n" + "".join(
        f"{name},{code}\n" for code, name in names.items()), encoding="utf-8")
    features = []
    for i, (code, name) in enumerate(names.items()):
        x, y = 7 + (i % 9) * .04, 45 + (i // 9) * .04
        features.append({"type": "Feature", "properties": {
            "municipality_code": code, "municipality": name, "snai_class": "ABCDEF"[i % 6],
            **{field: float(i) for field in NUMERIC_FIELDS}}, "geometry": {
                "type": "Polygon", "coordinates": [[[x, y], [x+.035, y],
                    [x+.035, y+.035], [x, y+.035], [x, y]]]}})
    geometry = {"type": "FeatureCollection", "features": features}
    _json(directory / "municipality_profile.geojson", geometry)
    metrics = tuple(replace(metric, source="SYNTHETIC TEST ONLY")
                    for metric in (*atlas.v3.METRICS, *atlas.NEW))
    indicators = []
    for metric in metrics:
        available = metric.id not in {"H03", "H04", "H05", "ADD-HOUSING-01"}
        period = "2026-01-01" if metric.id == "H47" else "2024"
        indicators.append({"id": metric.id, "name": metric.name, "unit": metric.unit,
            "family": metric.family, "source": metric.source,
            "description": "SYNTHETIC TEST ONLY. " + metric.description,
            "available": available, "count": 27 if available else 0,
            "years": [period] if available else [],
            "evidence": "technical_synthetic_only" if available else "not_available"})
    towns = []
    for index, (code, name) in enumerate(names.items()):
        towns.append({"code": code, "name": name, "values": {
            m["id"]: {"value": "ABCDEF"[index % 6] if m["unit"] == "categoria" else float(index),
                       "year": m["years"][0]} for m in indicators if m["available"]}})
    payload = {"status": atlas.STATUS, "publication_allowed": False,
        "scientific_approval": False, "no_composite_score": True,
        "municipality_count": 27, "synthetic_fixture": True,
        "identical_numeric_series": [], "indicators": indicators, "municipalities": towns}
    _json(directory / "synthetic_snapshot.json", payload)
    return registry, geometry, metrics, payload


def build(out_dir: Path) -> Path:
    """Publish a fresh audited demonstration; never modify an existing destination."""
    if out_dir.exists() or out_dir.is_symlink():
        raise FileExistsError("Choose a fresh synthetic example destination; no overwrite")
    from .directory_publication import publish_directory
    from .output_bundle_quality_v0_4 import audit_bundle
    from .output_hub_v0_4 import build as build_hub
    from .output_quality_v0_4 import audit, _sha
    from .review_pack_v0_4 import build as build_review
    from .visual_atlas_v0_4 import _render_atlas, STATUS

    out_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".epah-synthetic-", dir=out_dir.parent) as temporary:
        stage = Path(temporary) / "example"
        stage.mkdir()
        registry, geometry, metrics, payload = _inputs(stage / "inputs")
        atlas = stage / "atlas"
        (atlas / "charts").mkdir(parents=True)
        manifest = {"status": STATUS, "publication_allowed": False,
            "scientific_approval": False, "synthetic_fixture": True,
            "registry_sha256": _sha(registry), "input_evidence": {}}
        _render_atlas(atlas, payload, manifest, registry, geometry, metrics=metrics, evidence={})
        review = build_review(atlas, registry, stage / "review")
        hub = build_hub(atlas, review, stage / "hub")
        qa = stage / "qa"
        qa.mkdir()
        _json(qa / "pack.json", audit(review, atlas=atlas))
        _json(qa / "hub.json", audit_bundle(hub))
        receipt = {"schema_version": "0.4-synthetic-example-1",
            "status": STATUS, "result": "synthetic_example_ready",
            "synthetic_fixture": True, "source_ingestion_performed": False,
            "publication_allowed": False, "scientific_approval": False,
            "visual_review_completed": False, "entrypoint": "hub/index.html",
            "municipalities": 27, "indicator_slots": 16, "observations": 432,
            "indicators_available": [m["id"] for m in payload["indicators"] if m["available"]],
            "indicators_pending": [m["id"] for m in payload["indicators"] if not m["available"]],
            "inputs_sha256": {p.name: _sha(p) for p in sorted((stage / "inputs").iterdir())},
            "artifacts_sha256": {name: _sha(stage / name) for name in (
                "atlas/atlas_manifest.json", "review/manifest.json", "hub/manifest.json",
                "qa/pack.json", "qa/hub.json")}}
        _json(stage / "run.json", receipt)
        (stage / "README_REVIEW.txt").write_text(
            "ESEMPIO SINTETICO - NON PUBBLICARE\n"
            "Comuni, geometrie e valori fittizi. Nessuna verifica di fonti territoriali.\n"
            "Aprire hub/index.html. Input sintetici in inputs/, audit in qa/, ricevuta in run.json.\n",
            encoding="utf-8")
        publish_directory(stage, out_dir)
    return out_dir
