# Report automatico di completezza (offline)

```bash
python scripts/report_completeness.py --output outputs/quality/completeness.json
```

Il comando legge l'elenco dei 27 Comuni, il catalogo dei 9 indicatori e la matrice. Controlla la completezza strutturale delle 243 combinazioni, gli ID duplicati e i Comuni estranei. Produce un file JSON con conteggi per stato, Comune e indicatore.

**Non** aggiorna alcun dato, stato di validazione, fonte o manifest. Il campo `nonempty_values` indica solo valori presenti, non valori validati. `missing_or_unvalidated` include tutto ciò che non è `Dato validato`, compresi i valori acquisiti.

Il file in `outputs/quality/` è un risultato locale derivato, non un nuovo dataset fonte. Gli errori di schema interrompono la generazione anziché mascherare le anomalie.

Estensioni proposte: CSV tabellari pronti per Excel, report QA sui range e sulle annate, checksum/provenance e integrazione nei report territoriali.
