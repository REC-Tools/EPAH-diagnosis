"""Visual atlas tests: fake observations; no inferred energy-poverty prevalence."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
import json
import zipfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import pytest

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "scripts/build_v0_3_visual_atlas.py"
SPEC = importlib.util.spec_from_file_location("build_v0_3_visual_atlas", FILE)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
import sys
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


def registry_file(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    path = tmp_path / "municipalities.csv"
    registry = {f"001{i:03d}": f"Comune {i}" for i in range(1, 28)}
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["municipality", "istat_code"])
        w.writerows((name, code) for code, name in registry.items())
    return path, registry


def sample_preview(registry: dict[str, str], metric: str, *, status: str = mod.STATUS):
    m = next(x for x in mod.EXTRA if x.id == metric)
    rows = []
    for code, name in registry.items():
        row = {"municipality_code": code, "municipality": name,
               m.year_field: {"H47":"2026-01-01", "H50":"2024", "H46":"2024", "H03":"2025"}[metric],
               "status": status, m.value_field: "5.00"}
        if metric == "H47":
            row.update(population_total="100", population_0_11="5")
        if metric == "H50":
            row.update(residents_25_64_total="100", residents_below_lower_secondary_25_64="5")
        if metric == "H46":
            row.update(labour_force_15_plus="100", unemployed_15_plus="5", employed_15_plus="95")
        if metric == "H03":
            row["temperature_days"] = "365"
        rows.append(row)
    return rows


def as_csv(rows):
    with io.StringIO(newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        return f.getvalue().encode("utf-8")


def test_inventory_has_9_plus_4_no_fake_total():
    assert len(mod.METRICS) == 13
    assert len(mod.BASE) == 9
    assert {m.id for m in mod.EXTRA} == {"H47", "H50", "H46", "H03"}
    assert len({m.id for m in mod.METRICS}) == 13


@pytest.mark.parametrize("metric", ["H47", "H50", "H46", "H03"])
def test_27_comuni_expected(metric, tmp_path):
    _, reg = registry_file(tmp_path)
    spec = next(x for x in mod.EXTRA if x.id == metric)
    rows = sample_preview(reg, metric)
    output = mod.check_preview(rows, spec, reg)
    assert len(output) == 27
    assert output["001001"]["value"] == 5.0
    with pytest.raises(ValueError, match="27 rows"):
        mod.check_preview(rows[:-1], spec, reg)


def test_no_fake_zero_for_missing_municipality(tmp_path):
    _, reg = registry_file(tmp_path)
    metric = mod.EXTRA[0]
    rows = sample_preview(reg, "H47")
    rows[0][metric.value_field] = ""
    with pytest.raises(ValueError, match="Missing"):
        mod.check_preview(rows, metric, reg)


def test_duplicate_code_rejected(tmp_path):
    _, reg = registry_file(tmp_path)
    rows = sample_preview(reg, "H47")
    rows[-1]["municipality_code"] = rows[0]["municipality_code"]
    with pytest.raises(ValueError, match="duplicate code"):
        mod.check_preview(rows, mod.EXTRA[0], reg)


def test_numerator_denominator_mismatch_rejected(tmp_path):
    _, reg = registry_file(tmp_path)
    rows = sample_preview(reg, "H46")
    rows[0]["employed_15_plus"] = "90"
    with pytest.raises(ValueError, match="labour force"):
        mod.check_preview(rows, next(x for x in mod.EXTRA if x.id == "H46"), reg)


def test_nonfinite_and_out_of_range_values_rejected(tmp_path):
    _, reg = registry_file(tmp_path)
    rows = sample_preview(reg, "H03")
    rows[0]["hdd_eurostat_estimated_c_days"] = "nan"
    with pytest.raises(ValueError, match="Out-of-range"):
        mod.check_preview(rows, next(x for x in mod.EXTRA if x.id == "H03"), reg)
    rows = sample_preview(reg, "H50")
    rows[0]["share_below_lower_secondary_25_64_pct"] = "150"
    with pytest.raises(ValueError, match="Out-of-range"):
        mod.check_preview(rows, next(x for x in mod.EXTRA if x.id == "H50"), reg)


def test_h03_rejects_missing_day(tmp_path):
    _, reg = registry_file(tmp_path)
    rows = sample_preview(reg, "H03")
    rows[0]["temperature_days"] = "364"
    with pytest.raises(ValueError, match="365"):
        mod.check_preview(rows, next(x for x in mod.EXTRA if x.id == "H03"), reg)


def test_preview_status_and_year_rejected(tmp_path):
    _, reg = registry_file(tmp_path)
    for change in ({"reference_year": "2023"}, {"status": "Dato validato"}):
        rows = sample_preview(reg, "H46")
        rows[0].update(change)
        with pytest.raises(ValueError, match="status/year"):
            mod.check_preview(rows, next(x for x in mod.EXTRA if x.id == "H46"), reg)


def test_h47_old_artifact_fails_closed(tmp_path):
    p, reg = registry_file(tmp_path)
    z = tmp_path / "old.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("h47_preview/population_0_11_preview.csv", as_csv(sample_preview(reg, "H47")))
        f.writestr("h47_preview/qa.json", "{}")
        f.writestr("h47_preview/manifest.json", "{}")
        f.writestr("source_observation.json", "{}")
    with pytest.raises(ValueError, match="NEW GitHub review artifact"):
        mod.load_h47_zip(z, mod.EXTRA[0], reg, p)


def test_manifest_tampering_is_rejected(tmp_path):
    path, reg = registry_file(tmp_path)
    d = tmp_path / "h50"
    d.mkdir()
    content = as_csv(sample_preview(reg, "H50"))
    (d / "low_education_25_64_preview.csv").write_bytes(content)
    qa = {"status":mod.STATUS,"epah_inventory_id":"H50"}
    qa_bytes = json.dumps(qa).encode()
    (d / "qa.json").write_bytes(qa_bytes)
    manifest = {"status":mod.STATUS,"scientific_approval":False,"canonical_data_modified":False,
                "normalized_export_mapping_verified":False,
                "municipality_registry_sha256":mod.file_sha(path),
                "outputs_sha256":{"low_education_25_64_preview.csv":mod.byte_sha(content),"qa.json":mod.byte_sha(qa_bytes)}}
    (d / "manifest.json").write_text(json.dumps(manifest))
    rows, proof = mod.load_review_dir(d, next(x for x in mod.EXTRA if x.id == "H50"), reg, path)
    assert len(rows) == 27 and proof["evidence_level"] == "technical_candidate_unreviewed_mapping"
    (d / "low_education_25_64_preview.csv").write_bytes(content + b"\n")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        mod.load_review_dir(d, next(x for x in mod.EXTRA if x.id == "H50"), reg, path)


def test_svg_map_projected_and_png_is_new(tmp_path):
    geometry = {"type": "FeatureCollection", "crs": {"type":"name", "properties":{"name":"OGC:CRS84"}},
                "features":[{"type":"Feature","properties":{"municipality_code":"001001"},
                             "geometry":{"type":"Polygon","coordinates":[[
                               [7,45],[7.05,45],[7.05,45.05],[7,45.05],[7,45]
                             ]]}}]}
    values = {"001001": {"value": 5.0,"year":"2026-01-01"}}
    m = mod.EXTRA[0]
    png = tmp_path / "h47_map.png"
    svg = tmp_path / "h47_map.svg"
    mod._make_map(geometry, m, values, png, "png")
    mod._make_map(geometry, m, values, svg, "svg")
    assert png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert b"<svg" in svg.read_bytes()[:4000]


def test_html_does_not_inject_source_values():
    content = mod._atlas_html({"indicators":[], "municipalities":[],"evil":"</script><script>alert(1)</script>"})
    assert "<script>alert(1)</script>" not in content
    assert "\\u003c/script" in content


def test_output_cannot_overwrite_existing(tmp_path):
    dest = tmp_path / "review"
    dest.mkdir()
    with pytest.raises(FileExistsError, match="NEW"):
        mod.build(tmp_path / "unavailable", dest)


def test_atlas_build_uses_9_and_marks_four_pending(tmp_path, monkeypatch):
    registry_path, reg = registry_file(tmp_path)
    samples = {}
    features = []
    for i, (code, name) in enumerate(reg.items()):
        vals = {}
        for j, spec in enumerate(mod.BASE):
            vals[spec.id] = {"value": "C" if spec.category == "categorical" else float(10 + j + i/10),
                             "year": "2021"}
        samples[code] = {"code": code, "name": name, "values": vals}
        lon = 7 + (i % 6) * .07
        lat = 45 + (i // 6) * .07
        ring = [[lon,lat],[lon+.06,lat],[lon+.06,lat+.06],[lon,lat+.06],[lon,lat]]
        features.append({"type":"Feature","properties":{"municipality":name,"municipality_code":code},
                         "geometry":{"type":"Polygon","coordinates":[ring]}})
    geometry = {"type":"FeatureCollection","crs":{"type":"name","properties":{"name":"OGC:CRS84"}},
                "features": features}
    monkeypatch.setattr(mod, "load_pilot", lambda *a: (samples, geometry, {"synthetic_test": True}))
    # A separate test renders real PNG/SVG; this one covers the run manifest/
    # pending indicators without drawing 36 figures in CI.
    def mock_plot(*args):
        args[-2].write_bytes(("synthetic-chart-" + args[-1]).encode())
    monkeypatch.setattr(mod, "_make_map", mock_plot)
    monkeypatch.setattr(mod, "_make_distribution", mock_plot)
    result = mod.build(tmp_path / "not-used", tmp_path / "atlas", registry_path=registry_path,
                       release_config=tmp_path / "not-used")
    manifest = json.loads((result / "atlas_manifest.json").read_text(encoding="utf-8"))
    data = json.loads((result / "atlas_data.json").read_text(encoding="utf-8"))
    assert len(data["indicators"]) == 13
    assert len(manifest["indicators_available"]) == 9
    assert set(manifest["indicators_pending"]) == {"H47", "H50", "H46", "H03"}
    assert len(list((result / "charts").glob("*.png"))) == 18
    assert len(list((result / "charts").glob("*.svg"))) == 18
    assert "H03" in (result / "index.html").read_text(encoding="utf-8")
    assert "NON PUBBLICARE" in (result / "index.html").read_text(encoding="utf-8")
    with pytest.raises(FileExistsError):
        mod.build(tmp_path / "not-used", result, registry_path=registry_path)


def test_h46_accepts_istat_register_estimates(tmp_path):
    _, reg = registry_file(tmp_path)
    spec = next(x for x in mod.EXTRA if x.id == "H46")
    rows = sample_preview(reg, "H46")
    for row in rows:
        row.update(employed_15_plus="93", unemployed_15_plus="7.970101160766249",
                   labour_force_15_plus="100.97010116076625", unemployment_rate_15_plus_pct="7.89")
    assert mod.check_preview(rows, spec, reg)["001001"]["value"] == 7.89
    rows[0]["employed_15_plus"] = "94"
    with pytest.raises(ValueError, match="invalid labour force"):
        mod.check_preview(rows, spec, reg)
    rows[0]["employed_15_plus"] = "-93"
    with pytest.raises(ValueError, match="nonnegative"):
        mod.check_preview(rows, spec, reg)
