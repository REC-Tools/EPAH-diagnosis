from epah_diagnosis.istat_building_stock import parse_building_stock_page


def test_parse_building_stock_page():
    html = """
    <html><body>
      <table>
        <tr><th>Indicatore</th><th>1991</th><th>2001</th><th>2011</th></tr>
        <tr>
          <td>Incidenza degli edifici in pessimo stato di conservazione</td>
          <td>...</td><td>2.5</td><td>3.4</td>
        </tr>
        <tr>
          <td>Consistenza delle abitazioni storiche occupate</td>
          <td>31.0</td><td>28.0</td><td>25.5</td>
        </tr>
      </table>
      <table>
        <tr><th>Indicatore</th><th>Comune A</th><th>Piemonte</th><th>Italia</th></tr>
        <tr>
          <td>Incidenza degli edifici in pessimo stato di conservazione</td>
          <td>3.4</td><td>1.2</td><td>1.7</td>
        </tr>
        <tr>
          <td>Consistenza delle abitazioni storiche occupate</td>
          <td>25.5</td><td>16.8</td><td>10.2</td>
        </tr>
      </table>
    </body></html>
    """

    result = parse_building_stock_page(html, "001001", "Comune A")

    assert result.historic_occupied_dwellings_pct == 25.5
    assert result.poor_condition_buildings_pct == 3.4
    assert result.region_historic_pct == 16.8
    assert result.italy_historic_pct == 10.2
    assert result.region_poor_condition_pct == 1.2
    assert result.italy_poor_condition_pct == 1.7
