"""Optional lossless count adapters for QA-checked v0.3 candidate previews.

A binding to the *exact* snapshot recorded in atlas_manifest is mandatory.
This adapter checks preview integrity and arithmetic; it does not certify the
ISTAT source mapping or grant a methodological/publication approval.
"""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
from pathlib import Path
import unicodedata
import zipfile

STATUS = "technical_draft_do_not_publish"
FIELDS = {
    "H46": ("unemployment_15_plus_preview.csv", "unemployed_15_plus",
            "labour_force_15_plus", "unemployment_rate_15_plus_pct",
            "reference_year", "2024", "labour_force_15_plus"),
    "H50": ("low_education_25_64_preview.csv",
            "residents_below_lower_secondary_25_64", "residents_25_64_total",
            "share_below_lower_secondary_25_64_pct", "reference_year", "2024",
            "residents_25_64_including_unknown_education"),
    "H47": ("population_0_11_preview.csv", "population_0_11",
            "population_total", "share_0_11_pct", "reference_date", "2026-01-01",
            "resident_population_provisional_2026"),
}
H47_MEMBERS = {
    "h47_preview/population_0_11_preview.csv",
    "h47_preview/qa.json", "h47_preview/manifest.json",
    "source_observation.json", "h47_independent_reproduction_audit.json",
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _name(s: str) -> str:
    text = unicodedata.normalize("NFKD", s.casefold())
    return "".join(c for c in text if c.isalnum() and not unicodedata.combining(c))


def _decimal(raw: str, *, integer: bool, location: str) -> Decimal:
    if (not isinstance(raw, str) or not raw or raw != raw.strip()
            or not raw.isascii() or raw.count(".") > 1
            or not raw.replace(".", "", 1).isdigit()
            or integer and not raw.isdigit()):
        raise ValueError(f"{location}: invalid nonnegative {'integer' if integer else 'decimal'} count")
    try:
        number = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"{location}: invalid decimal count") from exc
    if not number.is_finite() or number < 0:
        raise ValueError(f"{location}: non-finite or negative count")
    return number


def _csv(data: bytes) -> list[dict[str, str]]:
    with io.StringIO(data.decode("utf-8-sig"), newline="") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)) or not headers:
            raise ValueError("Duplicate or missing preview headers")
        rows = list(reader)
    if any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError("Malformed candidate preview CSV")
    return rows


def _load(kind: str, path: Path, registry_digest: str,
          atlas_evidence: dict) -> tuple[bytes, dict, dict, dict]:
    filename = FIELDS[kind][0]
    if kind == "H47":
        if path.stat().st_size > 20 * 1024 * 1024:
            raise ValueError("Oversized H47 review ZIP")
        with zipfile.ZipFile(path) as archive:
            if (len(archive.namelist()) != len(set(archive.namelist()))
                    or not H47_MEMBERS <= set(archive.namelist()) or len(archive.namelist()) > 10
                    or any(archive.getinfo(name).file_size > 2 * 1024 * 1024
                           for name in H47_MEMBERS)):
                raise ValueError("H47 requires the complete schema-2.0 review ZIP")
            audited = {name: archive.read(name) for name in H47_MEMBERS
                       if name != "h47_independent_reproduction_audit.json"}
            audit = json.loads(archive.read("h47_independent_reproduction_audit.json"))
        if atlas_evidence.get("input_artifact_sha256") != hashlib.sha256(path.read_bytes()).hexdigest():
            raise ValueError("H47 ZIP does not match the verified atlas input")
        if (audit.get("schema_version") != "2.0"
                or audit.get("audited_files_sha256") != {key: _sha(value) for key, value in audited.items()}
                or audit.get("original_source_registry_sha256") != registry_digest
                or audit.get("status") != "independently_reproduced_technical_only"
                or audit.get("municipality_coverage") != "27/27"
                or audit.get("scientific_approval") is not False):
            raise ValueError("H47 independent audit receipt is missing or stale")
        csv_bytes = audited["h47_preview/population_0_11_preview.csv"]
        qa_bytes = audited["h47_preview/qa.json"]
        manifest = json.loads(audited["h47_preview/manifest.json"])
        observation = json.loads(audited["source_observation.json"])
        qa = json.loads(qa_bytes)
        if (qa.get("sex_totals_verified") is not True
                or manifest.get("canonical_registry_modified") is not False
                or audit.get("original_source_zip_sha256") != manifest.get("input_original_zip_sha256")
                or observation.get("original_zip_sha256") != manifest.get("input_original_zip_sha256")
                or observation.get("scientific_approval") is not False):
            raise ValueError("H47 original source or sex-total audit mismatch")
        entry = "population_0_11_preview.csv"
    else:
        csv_bytes = (path / filename).read_bytes()
        qa_bytes = (path / "qa.json").read_bytes()
        qa = json.loads(qa_bytes)
        manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
        if (manifest.get("canonical_data_modified") is not False
                or kind == "H46" and manifest.get("official_source_mapping_verified") is not False
                or kind == "H50" and manifest.get("normalized_export_mapping_verified") is not False):
            raise ValueError(f"{kind}: unexpected canonical or mapping approval")
        entry = filename
    if (atlas_evidence.get("preview_sha256") != _sha(csv_bytes)
            or manifest.get("status") != STATUS or qa.get("status") != STATUS
            or manifest.get("scientific_approval") is not False
            or manifest.get("municipality_registry_sha256") != registry_digest
            or manifest.get("outputs_sha256", {}).get(entry) != _sha(csv_bytes)
            or manifest.get("outputs_sha256", {}).get("qa.json") != _sha(qa_bytes)
            or qa.get("epah_inventory_id", qa.get("indicator_inventory_id")) != kind):
        raise ValueError(f"{kind}: preview, QA, manifest or atlas receipt mismatch")
    return csv_bytes, qa, manifest, {"preview_sha256": _sha(csv_bytes)}


def enrich(kind: str, path: Path, registry: dict[str, str],
           registry_digest: str, atlas_evidence: dict, atlas_towns: dict) -> tuple[dict, dict]:
    """Return per-code exact-count text and a non-approval integrity receipt."""
    if kind not in FIELDS:
        raise ValueError(f"Unsupported candidate adapter: {kind}")
    if not isinstance(atlas_evidence, dict) or set(atlas_towns) != set(registry):
        raise ValueError(f"{kind}: missing atlas evidence or municipality coverage")
    preview, _, _, receipt = _load(kind, path, registry_digest, atlas_evidence)
    filename, nkey, dkey, ratekey, periodkey, expected, universe = FIELDS[kind]
    records = _csv(preview)
    if len(records) != 27:
        raise ValueError(f"{kind}: expected 27 candidate rows")
    result = {}
    for raw in records:
        code = raw.get("municipality_code", "")
        if code not in registry or code in result or _name(raw.get("municipality", "")) != _name(registry[code]):
            raise ValueError(f"{kind}: duplicate or unknown municipality {code}")
        if raw.get("status") != STATUS or raw.get(periodkey) != expected:
            raise ValueError(f"{kind}/{code}: unexpected status or period")
        fraction = kind == "H46"
        numerator = _decimal(raw.get(nkey), integer=not fraction, location=code)
        denominator = _decimal(raw.get(dkey), integer=not fraction, location=code)
        if denominator <= 0 or numerator > denominator:
            raise ValueError(f"{kind}/{code}: invalid numerator or denominator")
        rate = _decimal(raw.get(ratekey), integer=False, location=code)
        if (rate > 100 or abs(rate - 100 * numerator / denominator) > Decimal("0.011")):
            raise ValueError(f"{kind}/{code}: count/rate mismatch")
        atlas_obs = atlas_towns[code].get("values", {}).get(kind)
        if (not isinstance(atlas_obs, dict) or atlas_obs.get("year") != expected
                or type(atlas_obs.get("value")) not in {int, float}
                or not abs(Decimal(str(atlas_obs["value"])) - rate) <= Decimal("0.00000001")):
            raise ValueError(f"{kind}/{code}: preview diverges from atlas displayed rate")
        if kind == "H46":
            employed = _decimal(raw.get("employed_15_plus"), integer=False, location=code)
            if abs(employed + numerator - denominator) > Decimal("0.000001"):
                raise ValueError(f"{kind}/{code}: employed + unemployed does not reconcile")
        result[code] = {
            "numerator": raw[nkey], "denominator": raw[dkey],
            "universe": universe, "value": raw[ratekey],
        }
    if set(result) != set(registry):
        raise ValueError(f"{kind}: incomplete candidate scope")
    receipt["integrity_status"] = "technical_preview_bound_to_atlas_not_source_approval"
    if kind == "H47":
        receipt["independent_reproduction_receipt_checked"] = True
    return result, receipt
