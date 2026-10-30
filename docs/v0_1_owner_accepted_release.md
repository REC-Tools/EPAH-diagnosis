# Un comando per la v0.1.0 tecnica — senza nuove firme

L'esperto ha approvato la v0.1.0 **come release pilota territoriale**
dei 27 Comuni. L'approvazione dell'Unione Montana arriverà separatamente.

Il generatore `scripts/build_v0_1_owner_accepted.py` unisce in un'area
temporanea i 162 valori canonici già presenti e le 81 righe delle
tre bozze di accessibilità già sottoposte a QA. Verifica integrità degli
SHA, matrice 27×9 e il rapporto 9/9 dall'originale ISTAT, prepara le
nove approvazioni *per la sola build pilota* con il riferimento alla
decisione dell'esperto e usa il builder ufficiale per produrre CSV,
GeoJSON, Excel, PDF, nove mappe, manifest e readiness.

Dalla root della repository aggiornata:

```powershell
python scripts/build_v0_1_owner_accepted.py
```

Output:
- `outputs/v0.1.0-pilot/`
- `outputs/epah_diagnosis_v0.1.0_pilot.zip`

Prende le bozze già disponibili:
- `outputs/quality/dea_accessibility_2025_v03`
- `outputs/quality/rail_accessibility_v01`
- `outputs/quality/upper_secondary_accessibility_v01`
- `outputs/quality/v0_1_pilot_route_samples_v01/samples.json`

Richiede anche `data/downloads/Limiti01012026_g.zip`, già presente
localmente, per la geometria ufficiale. Non serve ripetere i controlli.

**Non modifica** `data/verification_matrix.csv` o
`config/indicators.json` / `config/release_reviews_v0_1.json`,
non falsifica attestazioni di verifica indipendente e non elimina
altre cartelle. Se esiste già un bundle, usa nomi diversi per
`--output-dir` e `--archive`. Verifica il bundle con il gate del
builder originale prima della produzione dello ZIP.

Il risultato è una release pilota tecnicamente accettata
dall'esperto, non una release istituzionale certificata.
