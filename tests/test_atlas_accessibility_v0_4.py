"""Step 7: v0.4 atlas is keyboard/mobility friendly without changing data."""
from __future__ import annotations

from html.parser import HTMLParser
import json
import re

import pytest

from epah_diagnosis.atlas_accessibility_v0_4 import enhance_atlas_html
from test_v0_3_visual_atlas import mod as v3


class Structure(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.labels = []
        self.scopes = []
        self.attrs_by_id = {}
        self.skip_links = []

    def handle_starttag(self, tag, attrs):
        props = dict(attrs)
        if "id" in props:
            self.ids.append(props["id"])
            self.attrs_by_id[props["id"]] = props
        if tag == "label":
            self.labels.append(props.get("for"))
        if tag == "th":
            self.scopes.append(props.get("scope"))
        if tag == "a" and props.get("class") == "skip-link":
            self.skip_links.append(props.get("href"))


def _atlas_html():
    payload = {
        "status": "technical_draft_do_not_publish",
        "publication_allowed": False,
        "no_composite_score": True,
        "identical_numeric_series": [],
        "indicators": [{
            "id": "H46", "name": "Disoccupati 15+", "source": "ISTAT",
            "description": "Dati sintetici di test, NON PUBBLICARE",
            "unit": "%", "family": "Economia",
            "available": False, "count": 0, "years": [],
        }],
        "municipalities": [{
            "code": f"001{i:03d}",
            "name": "Borgo dell'Àlbero" if i == 1 else f"Synthetic Comune {i:02d}",
            "values": {},
        } for i in range(1, 28)],
    }
    return v3._atlas_html(payload)


def _embedded_payload(html):
    result = re.search(
        r'<script type="application/json" id="data">([\s\S]*?)</script>', html,
    )
    assert result
    return json.loads(result.group(1)), result.group(1)


def test_a11y_enhancement_preserves_all_data_bytes_and_nonpublication():
    raw = _atlas_html()
    enhanced = enhance_atlas_html(raw)
    assert _embedded_payload(raw) == _embedded_payload(enhanced)
    assert "BOZZA TECNICA" in enhanced
    assert "NON PUBBLICARE" in enhanced
    assert "Non acquisito" in enhanced
    assert "n.d." not in enhanced
    assert "item.unit" in enhanced  # units, source and periods remain data-driven
    assert "normaliseSearch" in enhanced
    assert ".normalize('NFD')" in enhanced
    assert "r.code.includes(q)" in enhanced
    assert "tabIndex=-1" in enhanced
    assert "found.focus()" in enhanced
    assert "choice.value='';draw()" in enhanced
    assert "scrollIntoView({block:'nearest'})" in enhanced
    assert "matches+' Comuni su 27" in enhanced
    assert "matches===0" in enhanced
    assert "Nessun Comune corrisponde" in enhanced
    assert "img.loading='lazy'" in enhanced
    assert "Tutti i valori comunali sono disponibili nella tabella" in enhanced
    assert "innerHTML" not in enhanced  # safe textContent and DOM node construction
    assert "<script src=" not in enhanced
    assert "<link rel=\"stylesheet\" href=\"http" not in enhanced


def test_landmarks_native_controls_labels_and_mobile_scroll():
    page = enhance_atlas_html(_atlas_html())
    found = Structure()
    found.feed(page)
    assert len(found.ids) == len(set(found.ids))  # no duplicate IDs
    assert found.skip_links == ["#indicator"]
    for target in ("indicator", "search", "municipality-choice"):
        assert target in found.labels
        assert target in found.ids
    assert "reset-search" in found.ids
    assert found.attrs_by_id["reset-search"]["type"] == "button"
    assert found.attrs_by_id["result-count"]["role"] == "status"
    assert found.attrs_by_id["result-count"]["aria-live"] == "polite"
    assert found.attrs_by_id["indicator-status"]["role"] == "status"
    assert found.attrs_by_id["municipality-choice"]["aria-controls"] == "rows"
    assert found.attrs_by_id["search"]["aria-describedby"] == "search-help"
    assert found.attrs_by_id["municipal-table"] is not None
    assert found.scopes == ["col"] * 4
    assert found.attrs_by_id["contenuto-principale"] == {}
    assert "role=\"region\"" in page
    assert "tabindex=\"0\"" in page
    assert "aria-label=\"Tabella dei 27 Comuni" in page
    assert "@media(max-width:500px)" in page
    assert "min-width:590px" in page
    assert ":focus-visible" in page
    assert "prefers-reduced-motion" in page


def test_fails_closed_if_template_mismatch_or_already_modified():
    raw = _atlas_html()
    with pytest.raises(ValueError, match="template anchor"):
        enhance_atlas_html(raw.replace(
            '<label for="search">Cerca Comune</label>', '<label for="search">Trovami</label>',
        ))
    enhanced = enhance_atlas_html(raw)
    with pytest.raises(ValueError, match="template anchor"):
        enhance_atlas_html(enhanced)
    with pytest.raises(ValueError, match="unpublished"):
        enhance_atlas_html(raw.replace("BOZZA TECNICA", "APPROVATO"))


def test_embedded_json_rejects_injection_and_allows_accents():
    raw = _atlas_html()
    assert "Borgo dell" not in raw or "Borgo dell" in raw  # JSON is embedded, not HTML text
    payload, _ = _embedded_payload(enhance_atlas_html(raw))
    assert payload["municipalities"][0]["name"] == "Borgo dell'Àlbero"
    payload["municipalities"][0]["name"] = "</script><script>alert(1)</script>"
    html = enhance_atlas_html(v3._atlas_html(payload))
    assert "<script>alert(1)</script>" not in html
    assert "\\u003c/script" in html
    assert _embedded_payload(html)[0] == payload
