"""Inspect ISTAT tenure source snapshots, without calculating rental indicators."""
from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation, localcontext
import hashlib
import json
from pathlib import Path
import re
from xml.etree import ElementTree as ET

FLOW = "DF_DCSS_HUDW_1_COM"
NS = {"s": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure",
      "c": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common",
      "m": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message",
      "g": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic"}
DIMENSIONS = ("FREQ", "REF_AREA", "INDICATOR", "TENURE_STATUS_HOU", "PERIOD_CONSTRUCT",
              "OCC_STATUS_CDW", "USE_FLOOR_SPACEGROUP", "NUMBER_OCCUPANTS",
              "DENSITY_STANDARD", "HEATING_SYSTEM_TYPE")
SELECTION = {"FREQ": "A", "INDICATOR": "NPHH_AV", "PERIOD_CONSTRUCT": "ALL",
             "OCC_STATUS_CDW": "ALL", "USE_FLOOR_SPACEGROUP": "ALL",
             "NUMBER_OCCUPANTS": "TOT", "DENSITY_STANDARD": "ALL", "HEATING_SYSTEM_TYPE": "ALL"}
CATEGORIES = {"ALL", "OWN", "RENT", "OTH_OR"}
DENOMINATOR_NOTE = "TIT_POSSESSO__ALL_N1"


def _xml(raw):
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValueError("DTD/entity declarations are not supported")
    try:
        return ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ValueError("Expected complete SDMX XML") from exc


def metadata_profile(raw: bytes) -> dict:
    root = _xml(raw)
    flows = root.findall(".//s:Dataflow", NS)
    if (len(flows) != 1 or any(flows[0].get(k) != v for k, v in
                             {"id": FLOW, "agencyID": "IT1", "version": "1.0"}.items())):
        raise ValueError("Expected the verified ISTAT tenure flow, agency and version")
    ref = flows[0].find("s:Structure/Ref", NS)
    structures = root.findall(".//s:DataStructure", NS)
    expected_dsd = {"id": "DCSS_HUDW_TV", "agencyID": "IT1", "version": "1.0"}
    if (ref is None or len(structures) != 1
            or any(ref.get(k) != v or structures[0].get(k) != v for k, v in expected_dsd.items())):
        raise ValueError("Unexpected flow/DSD binding")
    dims = structures[0].findall("s:DataStructureComponents/s:DimensionList/s:Dimension", NS)
    if sorted((int(d.get("position", "0")), d.get("id")) for d in dims) != list(enumerate(DIMENSIONS, 1)):
        raise ValueError("Tenure dimension order changed; review the source")
    times = structures[0].findall("s:DataStructureComponents/s:DimensionList/s:TimeDimension", NS)
    if len(times) != 1 or times[0].get("id") != "TIME_PERIOD" or times[0].get("position") != "11":
        raise ValueError("Unexpected annual time dimension")
    schemes = {e.get("id"): e for e in root.findall(".//s:Codelist", NS)}
    codes = {}
    for dim in dims:
        enum = dim.find("s:LocalRepresentation/s:Enumeration/Ref", NS)
        if enum is None or enum.get("id") not in schemes:
            raise ValueError("Missing dimension codelist")
        codes[dim.get("id")] = {e.get("id") for e in schemes[enum.get("id")].findall("s:Code", NS)}
    if any(value not in codes[name] for name, value in SELECTION.items()) or not CATEGORIES <= codes["TENURE_STATUS_HOU"]:
        raise ValueError("The verified selection is absent from source codelists")
    notes = [e for e in root.findall(".//s:Codelist/s:Code", NS) if e.get("id") == DENOMINATOR_NOTE]
    if len(notes) != 1:
        raise ValueError("The denominator-universe note requires source review")
    labels = {e.get("{http://www.w3.org/XML/1998/namespace}lang"): e.text
              for e in notes[0].findall("c:Name", NS)}
    if not labels or any(not text for text in labels.values()):
        raise ValueError("Missing denominator note text")
    return {"metadata_sha256": hashlib.sha256(raw).hexdigest(), "area_codes": codes["REF_AREA"],
            "denominator_note": {"id": DENOMINATOR_NOTE, "source_text": labels}}


def _values(element):
    if element is None:
        return {}
    result = {}
    for child in element.findall("g:Value", NS):
        name, value = child.get("id"), child.get("value")
        if not name or value is None or name in result:
            raise ValueError("Ambiguous SDMX key or attributes")
        result[name] = value
    return result


def inspect_response(raw: bytes, code: str, profile: dict) -> dict:
    if not re.fullmatch(r"[0-9]{6}", code) or code not in profile["area_codes"]:
        raise ValueError("Expected a municipal code present in the verified metadata")
    root = _xml(raw)
    if root.tag != "{" + NS["m"] + "}GenericData":
        raise ValueError("Expected SDMX GenericData 2.1, not an error page")
    binding = root.find("m:Header/m:Structure/c:StructureUsage/Ref", NS)
    if binding is None or any(binding.get(k) != v for k, v in {"id": FLOW, "agencyID": "IT1", "version": "1.0"}.items()):
        raise ValueError("Unexpected SDMX response flow")
    datasets = root.findall("m:DataSet", NS)
    if len(datasets) != 1:
        raise ValueError("Expected one source dataset")
    observations, seen = [], set()
    for series in datasets[0].findall("g:Series", NS):
        key = _values(series.find("g:SeriesKey", NS))
        if (set(key) != set(DIMENSIONS) or key["REF_AREA"] != code
                or any(key[name] != value for name, value in SELECTION.items())
                or key["TENURE_STATUS_HOU"] not in CATEGORIES):
            raise ValueError("Unexpected municipal identity, dimension selection or tenure category")
        category = key["TENURE_STATUS_HOU"]
        if category in seen:
            raise ValueError("Repeated tenure series; do not silently select or sum")
        seen.add(category)
        obs = series.findall("g:Obs", NS)
        if len(obs) != 1:
            raise ValueError("Expected one latest observation per series")
        times = obs[0].findall("g:ObsDimension", NS)
        if (len(times) != 1 or times[0].get("id") != "TIME_PERIOD"
                or not re.fullmatch(r"[0-9]{4}", times[0].get("value", ""))):
            raise ValueError("Expected an explicit annual source period")
        values = obs[0].findall("g:ObsValue", NS)
        if len(values) > 1:
            raise ValueError("Repeated observation value")
        value = values[0] if values else None
        observations.append({"source_key": key, "period": times[0].get("value"),
                             "value_as_received": None if value is None else value.get("value"),
                             "attributes": {"dataset": _values(datasets[0].find("g:Attributes", NS)),
                                            "series": _values(series.find("g:Attributes", NS)),
                                            "observation": _values(obs[0].find("g:Attributes", NS))}})
    issues, numeric = [], {}
    if seen != CATEGORIES:
        issues.append("missing_tenure_categories")
    periods = sorted({o["period"] for o in observations})
    if len(periods) != 1:
        issues.append("source_periods_missing_or_different")
    for obs in observations:
        category = obs["source_key"]["TENURE_STATUS_HOU"]
        try:
            number = Decimal(obs["value_as_received"] or "NaN")
            if not number.is_finite() or number < 0:
                raise InvalidOperation
            numeric[category] = number
        except InvalidOperation:
            issues.append("missing_or_invalid_value:" + category)
        for scope, attrs in obs["attributes"].items():
            if "OBS_STATUS" in attrs:
                issues.append("source_flag_requires_review:" + category + ":" + scope + ":" + attrs["OBS_STATUS"])
    denominator = next((o for o in observations if o["source_key"]["TENURE_STATUS_HOU"] == "ALL"), None)
    note_present = denominator is not None and any(
        attrs.get("NOTE_TENURE_STATUS_HOU") == DENOMINATOR_NOTE for attrs in denominator["attributes"].values())
    if not note_present:
        issues.append("denominator_universe_note_absent")
    if "ALL" in numeric and numeric["ALL"] <= 0:
        issues.append("denominator_not_positive")
    difference = None
    if CATEGORIES <= numeric.keys() and len(periods) == 1:
        with localcontext() as context:
            context.prec = max(28, sum(len(n.as_tuple().digits) + abs(n.as_tuple().exponent)
                                       for n in numeric.values()) + 4)
            difference = str(numeric["ALL"] - sum((numeric[k] for k in ["OWN", "RENT", "OTH_OR"]), Decimal(0)))
        if Decimal(difference) != 0:
            issues.append("partition_not_exact_no_tolerance_applied")
    return {"schema_version": "0.5-tenure-source-review-1", "status": "technical_draft_do_not_publish",
            "result": "source_snapshot_requires_review", "istat_code": code,
            "source_sha256": hashlib.sha256(raw).hexdigest(), "metadata_sha256": profile["metadata_sha256"],
            "source_periods": periods, "latest_per_series_only": True, "target_analysis_year": 2025,
            "observations": observations, "missing_categories": sorted(CATEGORIES - seen),
            "denominator_universe": profile["denominator_note"], "denominator_note_present": note_present,
            "partition_difference_as_received": difference, "review_issues": issues,
            "indicator_calculated": False, "municipal_series_added": 0,
            "scientific_approval": False, "publication_allowed": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xml", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--istat-code", required=True)
    parser.add_argument("--json-out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = inspect_response(args.xml.read_bytes(), args.istat_code, metadata_profile(args.metadata.read_bytes()))
        with args.json_out.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    except (ValueError, OSError, TypeError, KeyError) as exc:
        parser.exit(2, f"BLOCKED: {exc}\n")
    print("Tenure source inspected; calculations and approvals remain false.")
    return 0
