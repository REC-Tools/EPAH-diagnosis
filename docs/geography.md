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

## Reliable official ZIP acquisition

The default command downloads the official 2026 ISTAT generalized boundary
archive. Interrupted or short HTTP responses are retried up to four times,
resuming with HTTP Range when supported by the server. A 200 response to a
range request is treated as a fresh download; a mismatched Content-Range
is rejected. The original ZIP must pass archive/CRC checks before any
administrative boundary processing or output write.

Run the regular command after updating the repository:

```powershell
python scripts/acquire_municipality_boundaries.py
```

When the ISTAT server repeatedly interrupts scripted transfers, save the
complete official `Limiti01012026_g.zip` archive in your browser from:

https://www.istat.it/storage/cartografia/confini_amministrativi/generalizzati/2026/Limiti01012026_g.zip

Then use the offline fallback (Windows PowerShell):

```powershell
python scripts/acquire_municipality_boundaries.py --source-zip "$env:USERPROFILE\\Downloads\\Limiti01012026_g.zip"
```

The file is checked as a valid ZIP containing shapefile data (including
CRC verification); the existing 27-municipality filtering and WGS84/CRS84
export remain unchanged. An incomplete transfer is never published to
`data/geography/municipalities_2026.geojson`.
