# Esportazione completezza in CSV ed Excel

```bash
python scripts/export_completeness.py
```

Genera quattro file sotto `outputs/quality/`:
- `completeness.xlsx` (schede Summary, Municipalities, Indicators);
- `completeness_summary.csv`;
- `completeness_municipalities.csv`;
- `completeness_indicators.csv`.

Il report è derivato da `scripts/report_completeness.py` e viene prodotto **offline**, senza modificare matrice, catalogo o stati. I CSV hanno intestazioni UTF-8 compatibili con Excel e il workbook presenta filtri e intestazioni leggibili.

`validated` conta esclusivamente `Dato validato`, mentre `acquired` indica `Dato acquisito`. `nonempty_values` indica valori non vuoti, **non** qualità scientifica. Le righe `missing_or_unvalidated` richiedono controlli prima del rapporto EPAH.

L'esportazione non sostituisce il tracciamento di fonte, checksum e licenza per ogni indicatore. Questi rimangono una prossima attività.
