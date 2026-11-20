"""Rehashed active CSS and duplicate attributes must not pass a local pack audit."""
import pytest

from epah_diagnosis.utci_review_audit_v0_5 import audit_pack
from test_utci_review_audit_v0_5 import pack, rehash


@pytest.mark.parametrize("kind", ["extra_style", "inline_url", "escaped_css_url", "css_import",
                                 "duplicate_href", "duplicate_href_case", "duplicate_refresh"])
def test_rehashed_offline_content_bypasses_are_rejected(pack, kind):
    path = pack / "index.html"
    html = path.read_text(encoding="utf-8")
    old, new = {
        "extra_style": ("</head>", '<style>@import url(https://example.invalid/x.css);</style></head>'),
        "inline_url": ("<main>", '<main style="background-image:url(https://example.invalid/pixel)">'),
        "escaped_css_url": ("</style>", r'body{background-image:u\72l(https://example.invalid/pixel)}' + "</style>"),
        "css_import": ("</style>", '@import "https://example.invalid/x.css";</style>'),
        "duplicate_href": ('href="source/original.nc"', 'href="https://example.invalid/" href="source/original.nc"'),
        "duplicate_href_case": ('href="source/original.nc"', 'HREF="https://example.invalid/" href="source/original.nc"'),
        "duplicate_refresh": ("</head>", '<meta http-equiv="refresh" http-equiv="x" content="0;url=https://example.invalid/"></head>'),
    }[kind]
    assert old in html
    path.write_text(html.replace(old, new), encoding="utf-8")
    rehash(pack, "index.html")
    with pytest.raises(ValueError):
        audit_pack(pack)
