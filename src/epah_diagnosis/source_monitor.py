from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


DEFAULT_TIMEOUT = 25


@dataclass
class CheckResult:
    source_id: str
    source_name: str
    status: str
    current_reachable: bool
    current_http_status: int | None
    next_version_found: bool
    next_version_year: int | None
    landing_latest_reference_year: int | None
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _probe_url(url: str, timeout: int = DEFAULT_TIMEOUT) -> tuple[bool, int | None]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "EPAH-diagnosis-source-monitor/1.0",
            "Range": "bytes=0-1023",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 400, response.status
    except urllib.error.HTTPError as exc:
        return False, exc.code
    except (urllib.error.URLError, TimeoutError):
        return False, None


def _read_text(url: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "EPAH-diagnosis-source-monitor/1.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read(2_000_000)
    for encoding in ("utf-8", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _discover_landing_year(source: dict[str, Any]) -> int | None:
    pattern = source.get("landing_page_year_pattern")
    landing_url = source.get("landing_url")
    if not pattern or not landing_url:
        return None

    try:
        text = _read_text(landing_url)
    except Exception:
        return None

    matches = re.findall(pattern, text, flags=re.IGNORECASE)
    if not matches:
        return None

    years: list[int] = []
    for match in matches:
        if isinstance(match, tuple):
            candidates = match
        else:
            candidates = (match,)
        for candidate in candidates:
            if str(candidate).isdigit():
                years.append(int(candidate))
    return max(years) if years else None


def check_source(source: dict[str, Any]) -> CheckResult:
    current_ok, current_status = _probe_url(source["data_url"])
    reference_year = int(source["reference_year"])

    next_found = False
    next_year = None
    template = source.get("next_url_template")
    if template:
        candidate_year = reference_year + 1
        candidate_url = template.format(year=candidate_year)
        next_found, _ = _probe_url(candidate_url)
        if next_found:
            next_year = candidate_year

    landing_latest = _discover_landing_year(source)

    signals: list[str] = []
    status = "ok"

    if not current_ok:
        status = "error"
        signals.append("current source is not reachable")

    if next_found:
        status = "update_available"
        signals.append(f"new dataset candidate detected for {next_year}")

    if landing_latest and landing_latest > reference_year:
        status = "update_available"
        signals.append(
            f"landing page mentions a newer reference year ({landing_latest})"
        )

    if not signals:
        signals.append("source reachable; no newer version detected")

    return CheckResult(
        source_id=source["id"],
        source_name=source["name"],
        status=status,
        current_reachable=current_ok,
        current_http_status=current_status,
        next_version_found=next_found,
        next_version_year=next_year,
        landing_latest_reference_year=landing_latest,
        message="; ".join(signals),
    )


def load_registry(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        registry = json.load(handle)
    if registry.get("version") != 1:
        raise ValueError("Unsupported source registry version.")
    return registry


def run_checks(registry_path: Path) -> list[CheckResult]:
    registry = load_registry(registry_path)
    return [check_source(source) for source in registry["sources"]]


def render_markdown(results: list[CheckResult]) -> str:
    lines = [
        "# EPAH source monitor",
        "",
        "| Source | Status | Current source | New version | Notes |",
        "|---|---|---:|---:|---|",
    ]
    for result in results:
        current = "OK" if result.current_reachable else "FAIL"
        new_version = str(result.next_version_year) if result.next_version_found else "-"
        lines.append(
            f"| {result.source_name} | {result.status} | {current} | "
            f"{new_version} | {result.message} |"
        )
    lines.append("")
    return "\n".join(lines)
