"""Render replayed heat counts on source cells, without municipal allocation."""
from html import escape
import csv
import io

from .utci_heat_source_v0_5 import inspect


def review(annual, daily_zip):
    report = inspect(annual, daily_zip, year=2025)
    if report['issues'] or report['result'] != 'daily_replay_matches_annual':
        raise ValueError('Heat requires complete daily coverage and all four annual replays')
    return report


def rows(report):
    return [dict(series_id='LOCAL-UTCI-HEAT-GRID-2025', related_candidate='V05-03',
                 period=2025, scope='source_grid_cell', latitude=lat, longitude=lon,
                 threshold_celsius=field['threshold_celsius'], operator='>',
                 unit='days_per_year', value=field['replayed_strict_counts'][i][j],
                 valid_days=report['valid_days_per_cell'][i][j])
            for field in report['fields']
            for i, lat in enumerate(report['latitudes'])
            for j, lon in enumerate(report['longitudes'])]


def csv_bytes(report):
    stream = io.StringIO(newline='')
    values = rows(report)
    writer = csv.DictWriter(stream, fieldnames=list(values[0]))
    writer.writeheader()
    writer.writerows(values)
    return ('\ufeff' + stream.getvalue()).encode('utf-8')


def panel(report):
    latitudes = sorted(report['latitudes'], reverse=True)
    longitudes = sorted(report['longitudes'])
    count = len(latitudes) * len(longitudes)
    parts = ['<section class="notice"><h3>Caldo UTCI 2025 · celle originali</h3>',
             f'<p><strong>{count} celle dell’export · {report["distinct_daily_dates"]} date · quattro soglie separate.</strong> ',
             'Dettaglio mostrato: griglia 0,25°. Nessuna media comunale, interpolazione, ',
             'correzione altimetrica o attribuzione del dato alle famiglie. Le celle possono essere condivise ',
             'da più Comuni. L’intero export comprende anche aree esterne al perimetro dei 27 Comuni.</p>',
             '<p>Conteggi dei massimi giornalieri strettamente maggiori di 26, 32, 38 e 46 °C, ',
             'riprodotti dagli originali. Le soglie sono cumulative: <strong>non sommarle</strong>. ',
             'La coincidenza tra &gt; e ≥ non dimostra la semantica degli estremi del produttore. ',
             'Risultato tecnico, senza approvazione scientifica o autorizzazione alla diffusione. ',
             'Non rappresenta comfort interno o prevalenza di povertà energetica.</p>',
             '<p><a href="heat_grid.csv">Scarica tutte le celle CSV</a> · ',
             '<a href="heat_source_audit.json">Replay, copertura e hash JSON</a></p></section>']
    for field in report['fields']:
        threshold = field['threshold_celsius']
        width, height = 130 + 76 * len(longitudes), 100 + 54 * len(latitudes)
        parts.extend([f'<h3>Massimo UTCI &gt; {threshold} °C · giorni nel 2025</h3>',
                      '<p>Nord in alto. Latitudine e longitudine identificano i centri delle celle; ',
                      'i riquadri sono uno schema della griglia, non confini comunali. ',
                      'Colori sulla stessa scala 0–365 giorni per tutte le soglie; valori zero espliciti.</p>',
                      f'<div class="chart"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="Griglia UTCI sopra {threshold} gradi">',
                      f'<title>Giorni con massimo UTCI sopra {threshold} °C. Valori anche nella tabella seguente.</title>'])
        for j, lon in enumerate(longitudes):
            parts.append(f'<text x="{94+j*76}" y="25" font-size="13">{lon:g}° E</text>')
        for i, lat in enumerate(latitudes):
            parts.append(f'<text x="8" y="{68+i*54}" font-size="13">{lat:g}° N</text>')
            oi = report['latitudes'].index(lat)
            for j, lon in enumerate(longitudes):
                oj = report['longitudes'].index(lon)
                value = field['replayed_strict_counts'][oi][oj]
                lightness = 97 - 55 * value / 365
                color = '#fff' if lightness < 55 else '#193d48'
                x, y = 82+j*76, 38+i*54
                parts.append(f'<rect x="{x}" y="{y}" width="72" height="50" fill="hsl(28 75% {lightness:.2f}%)" stroke="#718582"/>')
                parts.append(f'<text x="{x+27}" y="{y+30}" fill="{color}" font-size="16">{value}</text>')
        parts.append('</svg></div><details><summary>Tabella delle celle accessibile e stampabile</summary>')
        parts.append('<div class="table"><table><caption>2025 · giorni/anno · soglia &gt; ' + threshold + ' °C</caption><thead><tr><th>Latitudine</th><th>Longitudine</th><th>Giorni</th><th>Giorni validi</th></tr></thead><tbody>')
        for row in rows(report):
            if row['threshold_celsius'] == threshold:
                parts.append(f'<tr><td>{row["latitude"]}</td><td>{row["longitude"]}</td><td>{row["value"]}</td><td>{row["valid_days"]}</td></tr>')
        parts.append('</tbody></table></div></details>')
    parts.append('<p>Le 24 contribuzioni orarie originarie di ogni massimo non sono ricostruite indipendentemente. ')
    parts.append('<a href="' + escape(report['unit_basis_url'], quote=True) + '">Specifiche Copernicus CDS</a>.</p>')
    return ''.join(parts)
