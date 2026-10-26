from __future__ import annotations

import io
import json
import re
import tempfile
import unicodedata
import urllib.request
import zipfile
from pathlib import Path

import shapefile
from pyproj import Transformer


BOUNDARIES_2026_URL = (
    "https://www.istat.it/storage/cartografia/confini_amministrativi/"
    "generalizzati/2026/Limiti01012026_g.zip"
)


def normalize_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _transform_coords(value, transformer: Transformer):
    if (
        isinstance(value, (list, tuple))
        and len(value) == 2
        and all(isinstance(item, (int, float)) for item in value)
    ):
        x, y = transformer.transform(value[0], value[1])
        return [x, y]
    if isinstance(value, (list, tuple)):
        return [_transform_coords(item, transformer) for item in value]
    return value


def _shape_to_wgs84_geojson(shape, transformer: Transformer) -> dict:
    geometry = shape.__geo_interface__
    return {
        "type": geometry["type"],
        "coordinates": _transform_coords(geometry["coordinates"], transformer),
    }


def _find_municipality_shapefile(archive: zipfile.ZipFile) -> str:
    candidates = [
        name
        for name in archive.namelist()
        if name.lower().endswith(".shp")
        and Path(name).name.lower().startswith("com")
    ]
    if not candidates:
        raise ValueError("Municipality shapefile not found in ISTAT archive.")

    generalized = [
        name
        for name in candidates
        if "_g_" in Path(name).name.lower() or Path(name).name.lower().endswith("_g.shp")
    ]
    return sorted(generalized or candidates)[0]


def parse_boundaries_zip(
    payload: bytes,
    municipality_names: set[str],
) -> dict:
    wanted = {normalize_name(name): name for name in municipality_names}

    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        shp_name = _find_municipality_shapefile(archive)
        stem = str(Path(shp_name).with_suffix(""))
        members = [
            name
            for name in archive.namelist()
            if str(Path(name).with_suffix("")) == stem
        ]

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            for member in members:
                target = tmp_path / Path(member).name
                target.write_bytes(archive.read(member))

            shp_path = tmp_path / Path(shp_name).name
            reader = shapefile.Reader(str(shp_path), encoding="utf-8")
            fields = [field[0] for field in reader.fields[1:]]
            upper = {field.upper(): field for field in fields}

            if "COMUNE" not in upper:
                raise ValueError(f"COMUNE field not found. Fields: {fields}")

            code_field = upper.get("PRO_COM_T") or upper.get("PRO_COM")
            if code_field is None:
                raise ValueError(f"PRO_COM_T/PRO_COM field not found. Fields: {fields}")

            name_field = upper["COMUNE"]
            transformer = Transformer.from_crs("EPSG:32632", "EPSG:4326", always_xy=True)

            features = []
            found = set()

            try:
                for shape_record in reader.iterShapeRecords():
                    record = shape_record.record
                    shape = shape_record.shape
                    values = dict(zip(fields, record))
                    official_name = str(values[name_field]).strip()
                    key = normalize_name(official_name)
                    if key not in wanted:
                        continue

                    code = str(values[code_field]).strip()
                    if code.endswith(".0"):
                        code = code[:-2]
                    code = re.sub(r"\D", "", code).zfill(6)[-6:]

                    features.append(
                        {
                            "type": "Feature",
                            "properties": {
                                "municipality": wanted[key],
                                "official_name": official_name,
                                "municipality_code": code,
                                "boundary_year": 2026,
                                "source": "ISTAT - Confini delle unita amministrative a fini statistici",
                            },
                            "geometry": _shape_to_wgs84_geojson(shape, transformer),
                        }
                    )
                    found.add(key)
            finally:
                reader.close()

    missing = sorted(wanted[key] for key in wanted.keys() - found)
    if missing:
        raise ValueError(
            "Municipalities not found in ISTAT boundary file: " + ", ".join(missing)
        )
    if len(features) != len(wanted):
        raise ValueError(
            f"Expected {len(wanted)} municipality features, found {len(features)}."
        )

    features.sort(key=lambda feature: feature["properties"]["municipality"])

    return {
        "type": "FeatureCollection",
        "name": "Green Community Sinergie in Canavese - municipalities 2026",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
        },
        "features": features,
    }


def download_boundaries(url: str = BOUNDARIES_2026_URL) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 EPAH-diagnosis/1.0",
            "Accept": "application/zip,application/octet-stream,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def write_geojson(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
