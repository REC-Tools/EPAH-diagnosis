# Diagnostic maps — correct scale and canonical pipeline

The nine official PNG maps are generated through
  python scripts/build_v0_1_bundle.py
**only after** the existing 27 x 9 source/methodology release gates.

## CRS handling

- ISTAT 2026 generalized municipal boundaries: EPSG:32632 (WGS84/UTM32N).
- Stored GeoJSON: geographic WGS84/CRS84 (lon,lat; EPSG:4326 values).
- All PNG maps: in-memory EPSG:4326 -> EPSG:32632 transformation
  with pyproj always_xy=True. Matplotlib equal aspect is now 1:1 METRES.
  Equal aspect on longitude/latitude degrees distorted the map near 45N.

The reusable renderer is src/epah_diagnosis/cartography.py. Polygon holes
and multipolygons are retained. The GeoJSON, municipality data and
source approval statuses are never projected or modified by rendering.

## Compatibility commands (PREVIEW ONLY)

- python scripts/build_municipality_geojson.py
- python scripts/generate_diagnostic_maps.py
- python scripts/generate_overlap_map.py

These commands now share the canonical map renderer rather than duplicate
polygon loops. Files under outputs/maps/ are local previews, not approved
v0.1 results. The overlap is a three-dimensional descriptive proxy, never
a composite energy-poverty score.
