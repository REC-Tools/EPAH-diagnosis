# Verifica pilota delle nove rotte campione (v0.1, 27 Comuni)

Per la v0.1 non eseguire l'audit nazionale DEA come prerequisito.

Dopo l'aggiornamento del repository e con le tre bozze locali già
calcolate, usare:

    python scripts/audit_v0_1_pilot_route_samples.py --road-zip data/downloads/Piemonte.zip --dea-draft outputs/quality/dea_accessibility_2025_v03 --rail-draft outputs/quality/rail_accessibility_v01 --school-draft outputs/quality/upper_secondary_accessibility_v01 --out-dir outputs/quality/v0_1_pilot_route_samples_v01 --strict

Il risultato è outputs/quality/v0_1_pilot_route_samples_v01/samples.json,
con nove coppie origine-destinazione, tre per ciascun indicatore e
riferimento al membro/riga CSV originale ISTAT. I codici origine campione
sono Ceresole Reale (001073), Ronco Canavese (001224) e Castellamonte
(001066). SHA-256 dei tre draft e dello ZIP originale sono controllati.

Questa verifica automatica è una PROVA TECNICA per il fascicolo; il
revisore deve verificarne almeno i riscontri campione e attestare
l'eventuale firma reale. Non controlla licenze, attualità della rete
ferroviaria o offerta scolastica, né dimostra una copertura nazionale
dei servizi.

La validazione dei nove indicatori resta necessaria per il release gate;
non creare approvazioni false o spostare la review istituzionale
dell'Unione Montana a nome del revisore tecnico.
