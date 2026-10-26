from epah_diagnosis.rail_access import parse_rfi_stations_html


def test_parse_rfi_stations_html_filters_piemonte():
    html = """
    <table>
      <tr>
        <th>Stazione</th><th>Indirizzo</th><th>Comune</th>
        <th>Provincia</th><th>Classificazione</th>
      </tr>
      <tr>
        <td>Ivrea</td><td>Corso Nigra</td><td>Ivrea</td>
        <td>Torino</td><td>PLUS</td>
      </tr>
      <tr>
        <td>Rivarolo</td><td>Corso Torino</td><td>Rivarolo Canavese</td>
        <td>Torino</td><td>LOCAL PLUS</td>
      </tr>
      <tr>
        <td>Milano Centrale</td><td>Piazza Duca d'Aosta</td><td>Milano</td>
        <td>Milano</td><td>MAIN HUB</td>
      </tr>
    </table>
    """

    stations = parse_rfi_stations_html(html)

    assert [station.station_name for station in stations] == ["Ivrea", "Rivarolo"]
    assert stations[0].municipality == "Ivrea"
    assert stations[1].classification == "LOCAL PLUS"
