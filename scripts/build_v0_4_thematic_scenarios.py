"""Create exploratory theme rankings from an integrity-checked atlas snapshot."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from epah_diagnosis.cli import read_municipality_codes
from epah_diagnosis.experimental_previews import _destination, _publish
from epah_diagnosis.provenance import sha256_file
from epah_diagnosis.thematic_scenarios import THEMES, analyse

ROOT = Path(__file__).resolve().parents[1]


def build(atlas: Path, registry: Path, out_dir: Path, themes: list[str], *, global_scenario=False):
    data_file, manifest_file = atlas / "atlas_data.json", atlas / "atlas_manifest.json"
    target = _destination(out_dir, [data_file, manifest_file, registry])
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if (manifest.get("status") != "technical_draft_do_not_publish"
            or manifest.get("publication_allowed") is not False
            or manifest.get("output_sha256", {}).get("atlas_data.json") != sha256_file(data_file)
            or manifest.get("registry_sha256") != sha256_file(registry)):
        raise ValueError("Atlas status, registry or data hash mismatch")
    data = json.loads(data_file.read_text(encoding="utf-8"))
    if data.get("status") != "technical_draft_do_not_publish" or data.get("publication_allowed") is not False:
        raise ValueError("Only explicit technical atlas snapshots are accepted")
    registered = read_municipality_codes(registry)
    if {(r["name"], r["code"]) for r in data["municipalities"]} != set(registered.items()):
        raise ValueError("Atlas municipalities differ from the registered names/codes")
    result = analyse(data["municipalities"], themes, global_scenario=global_scenario)
    result["synthetic_input"] = data.get("synthetic_input", False)
    result["source_evidence_not_reaudited"] = True
    rows = []
    for town in result["municipalities"]:
        row = {"municipality_code": town["code"], "municipality": town["name"], "status": result["status"]}
        for theme, values in town["themes"].items():
            row.update({f"{theme}_{key}": value for key, value in values.items()})
        row.update({f"global_{key}": value for key, value in town.get("global_selected_themes", {}).items()})
        rows.append(row)
    return _publish(target, {"atlas_data": data_file, "atlas_manifest": manifest_file, "registry": registry}, rows,
                    {"kind": "experimental_thematic_scenarios", "contains_composite_scores": True,
                     "municipalities": 27, "selected_themes": themes,
                     "synthetic_input": result["synthetic_input"]}, result)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--atlas-dir", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=ROOT / "data/municipalities.csv")
    parser.add_argument("--themes", required=True, help="Comma-separated: " + ",".join(THEMES))
    parser.add_argument("--global-scenario", action="store_true", help="Explicit optional synthesis of selected themes only")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        out = build(args.atlas_dir, args.registry, args.out_dir,
                    [t.strip() for t in args.themes.split(",")], global_scenario=args.global_scenario)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"BLOCKED: {exc}\n")
    print(f"EXPERIMENTAL SCENARIOS - NOT AN OFFICIAL POVERTY RANKING: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
