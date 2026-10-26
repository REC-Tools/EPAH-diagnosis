from epah_diagnosis import source_monitor


def test_check_source_detects_new_version(monkeypatch):
    source = {
        "id": "demo",
        "name": "Demo",
        "data_url": "https://example.test/current.zip",
        "reference_year": 2024,
        "next_url_template": "https://example.test/data_{year}.zip",
    }

    def fake_probe(url, timeout=25):
        if "2025" in url:
            return True, 200
        return True, 200

    monkeypatch.setattr(source_monitor, "_probe_url", fake_probe)

    result = source_monitor.check_source(source)

    assert result.status == "update_available"
    assert result.next_version_found is True
    assert result.next_version_year == 2025


def test_check_source_reports_unreachable(monkeypatch):
    source = {
        "id": "demo",
        "name": "Demo",
        "data_url": "https://example.test/current.zip",
        "reference_year": 2024,
    }

    monkeypatch.setattr(source_monitor, "_probe_url", lambda *args, **kwargs: (False, 404))

    result = source_monitor.check_source(source)

    assert result.status == "error"
    assert result.current_reachable is False
