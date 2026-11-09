#!/usr/bin/env python3
"""Technical-only EPAH H46 intake from ISTAT 2024 SDMX (27 municipalities).

Run inside EPAH-diagnosis repository. Output is raw evidence and an audit of
codes; it is NOT a scientifically approved unemployment indicator. The separate
prepare_unemployment_15_plus_v0_3.py requires an independently reviewed mapping.

No third-party packages needed. ISTAT rate-limits SDMX (~5 requests/min/IP):
this script makes at most TWO requests (one dataflow DSD, one data query), with
no automatic retries. Never schedule aggressive parallel downloads.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

FLOW = "DF_DCSS_ISTR_LAV_PEN_2_TV_3"
BASE = "https://esploradati.istat.it/SDMXWS/rest"
METADATA_URL = f"{BASE}/dataflow/IT1/{FLOW}/1.0/?detail=Full&references=Descendants"
# H50 uses these dimensions. Used ONLY as a marked fallback if H46 DSD cannot be parsed.
H50_DIMENSION_ORDER = (
    "FREQ", "REF_AREA", "INDICATOR", "GENDER", "AGE_NOCLASS", "CITIZENSHIP",
    "EDU_ATTAIN", "CUR_ACT_STAT", "LOC_DEST", "REAS_COMMUTING",
)
TARGET_YEAR = "2024"
STATUS = "technical_draft_do_not_publish"
ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest()


def registry(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not {"istat_code", "municipality"}.issubset(reader.fieldnames or []):
            raise ValueError("registry must contain istat_code and municipality")
        entries: dict[str, str] = {}
        for row in reader:
            code = (row.get("istat_code") or "").strip()
            name = (row.get("municipality") or "").strip()
            if not re.fullmatch(r"[0-9]{6}", code) or not name or code in entries:
                raise ValueError(f"Invalid/duplicate registry row: {row}")
            entries[code] = name
    if len(entries) != 27:
        raise ValueError(f"Expected exactly 27 municipalities, found {len(entries)}")
    return entries


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_metadata(raw: bytes) -> tuple[list[str], dict[str, dict[str, str]]]:
    """Return DSD dimension order plus observed-value labels, when XML provides them."""
    root = ET.fromstring(raw)
    candidates = []
    dimension_codelists: dict[str, str] = {}
    for ds in root.iter():
        if local(ds.tag) != "DataStructure":
            continue
        dims = []
        links = {}
        for node in ds.iter():
            if local(node.tag) != "Dimension" or not node.get("id"):
                continue
            pos = node.get("position")
            if not pos or not pos.isdigit():
                continue
            name = node.get("id")
            dims.append((int(pos), name))
            for part in node.iter():
                if local(part.tag) == "Ref" and part.get("id") and part.get("class") == "Codelist":
                    links[name] = part.get("id")
        if dims and {"FREQ", "REF_AREA"}.issubset(name for _, name in dims):
            candidates.append((sorted(dims), links))
    if len(candidates) != 1:
        return [], {}
    positions, dimension_codelists = candidates[0]
    # The time dimension is not part of the time-series key.
    if [p for p, _ in positions] != list(range(1, len(positions) + 1)):
        return [], {}
    wanted = set(dimension_codelists.values())
    schemes: dict[str, dict[str, str]] = {}
    for codelist in root.iter():
        if local(codelist.tag) != "Codelist" or codelist.get("id") not in wanted:
            continue
        labels = {}
        for code in codelist:
            if local(code.tag) != "Code" or not code.get("id"):
                continue
            names = [(n.attrib.get("{http://www.w3.org/XML/1998/namespace}lang", ""), n.text or "")
                     for n in code if local(n.tag) == "Name"]
            italian = next((label for lang, label in names if lang.lower().startswith("it")), "")
            english = next((label for lang, label in names if lang.lower().startswith("en")), "")
            label = italian or english or (names[0][1] if names else "")
            if label:
                labels[code.get("id")] = label
        schemes[codelist.get("id")] = labels
    return [name for _, name in positions], {
        dim: schemes.get(ref, {}) for dim, ref in dimension_codelists.items()
    }


def fetch_one(url: str, target: Path, accept: str, timeout: int) -> None:
    req = Request(url, headers={"Accept": accept, "User-Agent": "EPAH-diagnosis-H46/0.3"})
    try:
        with urlopen(req, timeout=timeout) as response, target.open("wb") as stream:
            status = response.getcode()
            if status != 200:
                raise RuntimeError(f"Unexpected HTTP status {status} from {url}")
            shutil.copyfileobj(response, stream)
    except HTTPError as exc:
        message = exc.read(500).decode("utf-8", errors="replace")
        raise RuntimeError(f"ISTAT HTTP {exc.code} at {url}: {message}") from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f"ISTAT network error at {url}: {exc}") from exc
    if target.stat().st_size < 20:
        raise RuntimeError(f"Empty/incomplete response at {url}")


def build_key(dims: list[str], codes: list[str]) -> str:
    if "FREQ" not in dims or "REF_AREA" not in dims:
        raise ValueError(f"DSD missing FREQ/REF_AREA: {dims}")
    selected = ["" for _ in dims]
    selected[dims.index("FREQ")] = "A"
    selected[dims.index("REF_AREA")] = "+".join(codes)
    return ".".join(selected)


def reduce_csv(raw_file: Path, selected_file: Path,
               municipalities: dict[str, str], metadata_labels: dict[str, dict[str, str]]) -> dict:
    columns_required = {"REF_AREA", "TIME_PERIOD", "GENDER", "OBS_VALUE"}
    categories: dict[str, Counter[str]] = {}
    rows_original = rows_2024_any_gender = rows_selected = 0
    area_counts = Counter()
    status_counter = Counter()
    with raw_file.open("r", newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)) or not columns_required.issubset(fields):
            raise ValueError(f"ISTAT response is not expected SDMX CSV. Columns: {fields[:20]}")
        if "CUR_ACT_STAT" not in fields:
            raise ValueError("CUR_ACT_STAT missing: dataset appears to be the wrong ISTAT flow")
        with selected_file.open("w", encoding="utf-8", newline="") as dest:
            writer = csv.DictWriter(dest, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            for no, row in enumerate(reader, 2):
                rows_original += 1
                if None in row or any(v is None for v in row.values()):
                    raise ValueError(f"Malformed response CSV at row {no}")
                code = row["REF_AREA"].strip()
                if code not in municipalities or row["TIME_PERIOD"].strip() != TARGET_YEAR:
                    continue
                rows_2024_any_gender += 1
                # H50's original ISTAT export uses T for gender total, but check the actual file.
                if row["GENDER"].strip() not in {"T", "TOTAL"}:
                    continue
                if row["OBS_VALUE"].strip() == "":
                    status_counter["missing_observation_value"] += 1
                if row.get("OBS_STATUS", "").strip():
                    status_counter[f"obs_status:{row['OBS_STATUS'].strip()}"] += 1
                writer.writerow(row)
                rows_selected += 1
                area_counts[code] += 1
                for dimension in fields:
                    if dimension in ("OBS_VALUE", "DATAFLOW") or dimension.startswith("NOTE_"):
                        continue
                    if dimension in {"FREQ", "REF_AREA", "INDICATOR", "GENDER",
                                     "AGE_NOCLASS", "CITIZENSHIP", "EDU_ATTAIN", "CUR_ACT_STAT",
                                     "LOC_DEST", "REAS_COMMUTING", "TIME_PERIOD", "OBS_STATUS"}:
                        categories.setdefault(dimension, Counter())[row[dimension]] += 1
    codebook = {
        dim: [
            {"code": value, "label_from_metadata": metadata_labels.get(dim, {}).get(value, ""), "rows": count}
            for value, count in sorted(counter.items())
        ]
        for dim, counter in sorted(categories.items())
    }
    return {
        "status": STATUS,
        "source_flow": FLOW,
        "reference_year": TARGET_YEAR,
        "sex_selected": "T or TOTAL only",
        "rows_in_api_response": rows_original,
        "rows_2024_for_27_municipalities_all_sexes": rows_2024_any_gender,
        "rows_2024_for_27_municipalities_total_sex": rows_selected,
        "municipality_coverage": f"{len(area_counts)}/27",
        "missing_municipalities": [{"code": code, "name": name} for code, name in municipalities.items() if code not in area_counts],
        "rows_per_municipality": {code: area_counts[code] for code in sorted(area_counts)},
        "observation_warnings": dict(status_counter),
        "codes_needing_scientific_mapping": codebook,
        "normalized_to_H46_contract": False,
        "scientific_approval": False,
        "note": "Raw technical intake. No inference of labour-force categories or age aggregation without official codelist review.",
    }


def acquire(args: argparse.Namespace, work: Path) -> dict:
    """Write every evidence file into ``work``; return the coverage audit."""
    municipalities = registry(args.registry)
    metadata_labels: dict[str, dict[str, str]] = {}
    dimension_status = "unverified_fallback_to_h50_structure"
    dims = list(H50_DIMENSION_ORDER)
    original = work / "ISTAT_censimento_2024_lavoro_original.csv"
    if args.original_export is None:
        print("Request 1/2: ISTAT H46 dataflow metadata (one request, no retries)", flush=True)
        metadata_file = work / "ISTAT_H46_dataflow_metadata.xml"
        try:
            fetch_one(METADATA_URL, metadata_file,
                      "application/vnd.sdmx.structure+xml;version=2.1", args.timeout)
            try:
                parsed_dims, metadata_labels = parse_metadata(metadata_file.read_bytes())
                if parsed_dims:
                    dims = parsed_dims
                    dimension_status = "parsed_from_istat_dsd"
                else:
                    print("WARNING: could not identify DSD dimensions; using explicit H50-order fallback", file=sys.stderr)
            except ET.ParseError:
                print("WARNING: metadata is not parseable as SDMX XML; using H50-order fallback", file=sys.stderr)
        except RuntimeError as exc:
            print(f"WARNING: metadata unavailable: {exc}", file=sys.stderr)
            metadata_file.unlink(missing_ok=True)
        key = build_key(dims, sorted(municipalities))
        url = f"{BASE}/data/IT1,{FLOW},1.0/{quote(key, safe='.+')}"
        print("Request 2/2: ISTAT H46 data for 27 municipalities (all years, filtered locally)", flush=True)
        print("Query URL:", url, flush=True)
        fetch_one(url, original, "application/vnd.sdmx.data+csv;version=1.0.0", args.timeout)
    else:
        if not args.original_export.is_file():
            raise ValueError(f"Original file is absent: {args.original_export}")
        shutil.copyfile(args.original_export, original)
        url = "local-official-export; API origin not independently attested by this program"
        dimension_status = "manual_export; DSD not fetched"
    selected = work / "H46_ISTAT_2024_27_comuni.csv"
    audit = reduce_csv(original, selected, municipalities, metadata_labels)
    audit["api_data_url"] = url
    audit["api_metadata_url"] = METADATA_URL
    audit["dimension_order"] = dims
    audit["dimension_order_provenance"] = dimension_status
    if audit["rows_2024_for_27_municipalities_total_sex"] == 0:
        raise ValueError("No 2024 rows with GENDER=T/TOTAL. Inspect original and status codes.")
    with (work / "H46_codebook_and_coverage.json").open("w", encoding="utf-8") as handle:
        json.dump(audit, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    manifest = {
        "status": STATUS,
        "acquired_at_utc": datetime.now(timezone.utc).isoformat(),
        "reference_year": TARGET_YEAR,
        "source_flow": FLOW,
        "api_data_url": url,
        "api_metadata_url": METADATA_URL,
        "dimension_order_provenance": dimension_status,
        "municipality_registry_sha256": sha256(args.registry),
        "files_sha256": {p.name: sha256(p) for p in sorted(work.iterdir()) if p.is_file()},
        "normalized_status_mapping_verified": False,
        "scientific_approval": False,
        "canonical_data_modified": False,
    }
    (work / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return audit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=ROOT / "data/municipalities.csv")
    parser.add_argument("--out-dir", type=Path, required=True, help="Fresh folder, never overwrite")
    parser.add_argument("--original-export", type=Path,
                        help="Use existing official ISTAT CSV export instead of online API")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args(argv)
    if args.out_dir.exists():
        parser.error("Output directory already exists: choose a new one")
    args.out_dir.parent.mkdir(parents=True, exist_ok=True)
    # Stage everything next to the destination: a failed download or a malformed
    # response never leaves a half-written evidence folder behind.
    with tempfile.TemporaryDirectory(prefix=".epah-h46-intake-", dir=args.out_dir.parent) as td:
        work = Path(td) / "intake"
        work.mkdir()
        audit = acquire(args, work)
        if args.out_dir.exists():
            raise FileExistsError("Output created concurrently; never overwrite")
        os.replace(work, args.out_dir)
    print(f"H46 raw data: {audit['rows_2024_for_27_municipalities_total_sex']} rows; "
          f"municipality coverage {audit['municipality_coverage']}")
    print("Status: technical_draft_do_not_publish; inspect H46_codebook_and_coverage.json")
    if audit["municipality_coverage"] != "27/27":
        print("WARNING: incomplete coverage - do not normalize or publish", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, OSError, csv.Error) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        raise SystemExit(1)
