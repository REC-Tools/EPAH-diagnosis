# V0.2 | Dashboard locale (offline)

La dashboard nasce dai **27 profili comunali** e dalle
**28 co-occorrenze** verificate del modulo multidimensionale.
Non richiede hosting, login, connessioni esterne né dati personali.

~~~powershell
uv run --locked epah dashboard v0.2 --analysis-dir outputs/v0.2-multidimensional-analysis --bundle outputs/v0.1.0-pilot --out-dir outputs/v0.2-offline-dashboard
~~~

Aprire `outputs/v0.2-offline-dashboard/index.html` nel browser:
è un file HTML statico e indipendente. Offre ricerca Comune,
filtro classe SNAI, scelta dell'indicatore, ordinamento
descrittivo e lettura delle intersezioni di due proxy.

La dashboard non utilizza richieste di rete, CDN, cookie,
metriche d'uso o servizi remoti. I valori visualizzati
derivano dai CSV QA verificati e dai medesimi hash del
bundle v0.1. `dashboard_data_v0_2.json` documenta i dati
effettivamente integrati; `dashboard_manifest_v0_2.json`
registra le impronte dei file.

**Non pubblicare** come strumento istituzionalmente
validato. Un Comune sopra la mediana non è automaticamente
più vulnerabile; l'intersezione di due dimensioni non è
un indice causale o di povertà energetica.
Nessun risultato CIT quarantinato viene importato.

La dashboard è un ausilio consultivo per FERVORES e Unione Montana,
non uno strumento per selezionare beneficiari o attribuire
condizioni individuali.
