from epah_diagnosis.heat_stress import classify_daily_max_utci


def test_heat_stress_thresholds_follow_copernicus_utci_categories():
    assert classify_daily_max_utci(31.9) == (False, False, False)
    assert classify_daily_max_utci(32.0) == (True, False, False)
    assert classify_daily_max_utci(38.0) == (True, True, False)
    assert classify_daily_max_utci(46.0) == (True, True, False)
    assert classify_daily_max_utci(46.1) == (True, True, True)
