"""Reproduce the provenance and singleton defects found before integration."""
from copy import deepcopy
import json
from xml.etree import ElementTree as ET

import pytest

from epah_diagnosis.tenure_intake_v0_5 import acquire
from epah_diagnosis.tenure_source_review_v0_5 import NS, inspect_response, metadata_profile
from test_tenure_intake_v0_5 import inputs, response


@pytest.mark.parametrize("problem", ["changed_seed", "changed_prior_bytes", "missing_prior_bytes", "changed_prior_hash"])
def test_reviewed_seed_must_match_prior_bytes_and_receipt_before_reuse(inputs, tmp_path, problem):
    meta, seed, registry, codes = inputs
    prior = tmp_path / "prior"
    acquire(meta, seed, registry, codes[0], prior,
            fetch=lambda url: (200, response(url.split("/A.")[1].split(".")[0]), None), wait=lambda _: None)
    original = prior / "raw" / f"{codes[0]}.xml"
    if problem == "changed_seed":
        seed.write_bytes(response(codes[0], values={"ALL": "11.000000", "OWN": "7.123456"}))
    elif problem == "changed_prior_bytes":
        original.write_bytes(b"changed synthetic evidence")
    elif problem == "missing_prior_bytes":
        original.unlink()
    else:
        receipt = json.loads((prior / "run.json").read_text())
        receipt["records"][0]["response_sha256"] = "f" * 64
        (prior / "run.json").write_text(json.dumps(receipt), encoding="utf-8")
    before = {p.relative_to(prior): p.read_bytes() for p in prior.rglob("*") if p.is_file()}
    seed_before = seed.read_bytes()
    out = tmp_path / "blocked"
    with pytest.raises((ValueError, OSError)):
        acquire(meta, seed, registry, codes[0], out, reuse_run=prior,
                fetch=lambda _: pytest.fail("must not fetch"), wait=lambda _: pytest.fail("must not wait"))
    assert not out.exists() and seed.read_bytes() == seed_before
    assert before == {p.relative_to(prior): p.read_bytes() for p in prior.rglob("*") if p.is_file()}


@pytest.mark.parametrize("path", [
    "m:Header", "m:Header/m:Structure", "m:Header/m:Structure/c:StructureUsage",
    "m:Header/m:Structure/c:StructureUsage/Ref", "m:DataSet/g:Series/g:SeriesKey",
    "m:DataSet/g:Attributes", "m:DataSet/g:Series/g:Attributes",
    "m:DataSet/g:Series/g:Obs/g:Attributes",
])
def test_duplicate_response_singletons_are_rejected_even_when_first_is_valid(inputs, path):
    meta, _, _, codes = inputs
    root = ET.fromstring(response(codes[0], flag="p"))
    parent_path, _, child_tag = path.rpartition("/")
    parent = root.find(parent_path, NS) if parent_path else root
    child = parent.find(child_tag, NS)
    if child is None:
        child = ET.SubElement(parent, "{" + NS["g"] + "}Attributes")
    duplicate = deepcopy(child)
    if child_tag == "g:SeriesKey":
        duplicate.find("g:Value[@id='REF_AREA']", NS).set("value", codes[1])
    parent.append(duplicate)
    raw = ET.tostring(root)
    with pytest.raises(ValueError, match="singleton"):
        inspect_response(raw, codes[0], metadata_profile(meta.read_bytes()))
    assert ET.tostring(root) == raw


@pytest.mark.parametrize("path", [
    ".//s:Dataflow/s:Structure", ".//s:Dataflow/s:Structure/Ref",
    ".//s:DataStructure/s:DataStructureComponents/s:DimensionList",
    ".//s:Dimension/s:LocalRepresentation/s:Enumeration",
    ".//s:Dimension/s:LocalRepresentation/s:Enumeration/Ref",
])
def test_duplicate_metadata_singletons_are_not_silently_selected(inputs, path):
    root = ET.fromstring(inputs[0].read_bytes())
    child = root.find(path, NS)
    parent = next(parent for parent in root.iter() if child in list(parent))
    duplicate = deepcopy(child)
    if path.endswith("s:DimensionList"):
        duplicate.clear()  # A second empty container was ignored by the old reader.
    parent.append(duplicate)
    with pytest.raises(ValueError, match="singleton"):
        metadata_profile(ET.tostring(root))
