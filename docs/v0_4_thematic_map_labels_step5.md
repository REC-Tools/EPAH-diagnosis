# EPAH v0.4 — Step 5: mappe con etichette selettive

**Decisione:** evitare 27 nomi sovrapposti sulle mappe tematiche. Per mappe PNG/SVG dell'atlante v0.4, visualizzare **al massimo cinque** etichette neutre, selezionate dalla **superficie geometrica** del poligono comunale proiettato EPSG:32632, non dai valori degli indicatori o dalla popolazione. La selezione è la stessa per ogni indicatore.

La posizione dell'etichetta è cercata all'interno del poligono, gestendo buchi e parti separate (multipoligoni). Se una scritta si sovrappone a un'altra o fuoriesce dall'area grafica, viene **omessa anziché sovrapposta**. I nomi sono in blu scuro con sfondo bianco leggero; non riflettono valori, priorità, ranking o stato di vulnerabilità. Questa superficie **non è una nuova superficie ufficiale ISTAT**: è calcolata soltanto dalla geometria usata dal rendering.

## Dove leggere gli altri Comuni

- **Atlante HTML:** tabella filtrabile con tutti i 27 Comuni (nome, ISTAT, anno, valore) per ogni indicatore.
- **Dot plot di distribuzione:** mantiene i nomi sulle 27 righe del grafico, dove sono funzionali al confronto anziché disposti dentro aree ristrette.
- **Tavola di orientamento A4:** rimane disponibile separatamente, con numeri in mappa e indice completo dei 27 nomi/codici.
- **Schede comunali e CSV:** continuano a mostrare la stessa copertura e i medesimi valori.

Non modificare la pipeline e le mappe storiche **v0.3**. Il builder v0.4 rigenera solo le proprie copie delle mappe disponibili (comprese quelle dei nove indicatori del pilota) e ricalcola gli SHA-256 delle mappe in `atlas_manifest.json`. Gli indicatori non disponibili non ricevono mappe. I dati numerici, le scale cividis assolute e la legenda SNAI A–F restano immutati.

`atlas_data.json` registra `map_label_policy` con criterio di selezione, codici/nome dei candidati, e codici effettivamente stampati nelle mappe PNG e SVG; l'ordine è deterministico e risolve i pari merito per codice ISTAT. L'HTML spiega esplicitamente che le etichette non sono una selezione di priorità.

## Verifica

```powershell
uv run --locked pytest -q tests/test_thematic_map_labels_v0_4.py
uv run --locked pytest -q
uv run --locked python scripts/check_documentation.py
```

È ancora necessario il **controllo visivo umano** sul bundle dei 27 Comuni reali, sia PNG sia SVG, e la revisione delle geometrie. Tutti gli output rimangono `technical_draft_do_not_publish`, con `publication_allowed=false`; questa PR non valida scientificamente né pubblica dati territoriali.

**Data-change: no.** Nessuna modifica ai dati, agli originali, alle valutazioni, al catalogo canonico o alle versioni di release.
