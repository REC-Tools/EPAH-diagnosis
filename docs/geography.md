# Municipal boundaries

The geographic baseline uses the official ISTAT municipal administrative
boundaries updated to **1 January 2026**.

Source:

- landing page: ISTAT, *Confini delle unita amministrative a fini statistici*
- dataset: generalized 2026 administrative boundaries
- source CRS: WGS84 / UTM zone 32N (EPSG:32632)

The acquisition script:

`python scripts/acquire_municipality_boundaries.py`

filters the national municipal layer to the 27 Green Community municipalities
and writes:

`data/geography/municipalities_2026.geojson`

The output is transformed to EPSG:4326 / CRS84 for interoperability with web
maps, QGIS and reporting tools.

The generalized version is preferred because the diagnosis is performed at
municipality scale and does not require cadastral-level boundary detail.

## Metric aspect of PNG exports

The stored GeoJSON stays geographic WGS84/CRS84. PNGs now use an
in-memory EPSG:32632 projection so equal aspect means equal metres;
no shape, attribute, or source-validation status is rewritten.
