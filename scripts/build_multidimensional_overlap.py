from __future__ import annotations

import json
from pathlib import Path

from epah_diagnosis.overlap import INDICATORS, add_overlap_classification, read_green_community_benchmark


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "derived" / "municipality_profile.geojson"
INDICATOR_DIR = ROOT / "data" / "indicators"
OUTPUT = ROOT / "data" / "derived" / "municipality_overlap.geojson"


def main() -> None:
    if not INPUT.exists():
        raise FileNotFoundError(
            f"Missing {INPUT}. Run build_municipality_geojson.py first."
        )

    benchmarks: dict[str, float] = {}
    for indicator, metadata in INDICATORS.items():
        path = INDICATOR_DIR / metadata["benchmark_file"]
        if not path.exists():
            raise FileNotFoundError(
                f"Missing {path}. Re-run the corresponding indicator finalizer."
            )
        benchmarks[indicator] = read_green_community_benchmark(path)

    data = json.loads(INPUT.read_text(encoding="utf-8"))
    classified = add_overlap_classification(data, benchmarks)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(classified, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("Green Community weighted benchmarks:")
    for indicator, value in benchmarks.items():
        print(f"  {indicator}: {value:.2f}%")

    counts = {level: 0 for level in range(4)}
    for feature in classified["features"]:
        level = feature["properties"]["vulnerability_overlap_count"]
        counts[level] += 1

    print("Municipalities by overlap:")
    for level in range(4):
        print(f"  {level} dimensions above benchmark: {counts[level]}")
    print(f"Output: {OUTPUT}")


if __name__ == "__main__":
    main()
