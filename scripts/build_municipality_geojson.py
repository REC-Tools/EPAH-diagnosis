from __future__ import annotations

from pathlib import Path

from epah_diagnosis.mapping import write_enriched_geojson


ROOT = Path(__file__).resolve().parents[1]
BOUNDARIES = ROOT / "data" / "geography" / "municipalities_2026.geojson"
PROFILES = ROOT / "data" / "derived" / "municipality_profile.csv"
OUTPUT = ROOT / "data" / "derived" / "municipality_profile.geojson"


def main() -> None:
    if not BOUNDARIES.exists():
        raise FileNotFoundError(
            f"Missing {BOUNDARIES}. Run acquire_municipality_boundaries.py first."
        )
    if not PROFILES.exists():
        raise FileNotFoundError(
            f"Missing {PROFILES}. Run build_municipality_profile.py first."
        )

    enriched = write_enriched_geojson(BOUNDARIES, PROFILES, OUTPUT)
    print(f"Built {len(enriched['features'])} enriched municipality features.")
    print(f"Output: {OUTPUT}")


if __name__ == "__main__":
    main()
