# EPAH v0.4 — Step 6: grafici di confronto leggibili e non classificatori

**Decisione:** i grafici di distribuzione numerica mostrano i **27 nomi completi** su righe separate, in **ordine crescente di codice ISTAT** (lo stesso ordine per ogni indicatore), non in ordine di valore. Questo distingue il confronto descrittivo da una graduatoria di vulnerabilità. Le etichette restano solo **fino a cinque nelle mappe** come deciso allo Step 5: i grafici non sono mappe.

## Nuovo rendering v0.4

- **Numerici:** dot plot con 27 righe e bande alternate, nomi a grandezza leggibile, unità sull'asse orizzontale, una mediana comunale **non ponderata** come riferimento contestuale (non come soglia di rischio). Figura verticale più alta; scala determinata separatamente per ogni indicatore, senza confrontare implicitamente unità diverse.
- **SNAI:** barre delle sei classi A–F con conteggi esatti di Comuni (somma 27). Le classi sono categorie istituzionali, non punteggi energetici; zero sulla barra significa che non ci sono Comuni di quella classe nel campione completo.
- **Accessibilità:** il formato SVG conserva i testi in forma selezionabile e leggibile da software che supportano l'accessibilità SVG; la tabella HTML dell'atlante rimane il riferimento testuale accessibile.
- **Trasparenza:** `atlas_data.json` aggiunge `distribution_policy` con ordine ISTAT, conteggi SNAI e mediana, così da rendere verificabile la scelta grafica. `atlas_manifest.json` elenca i nuovi SHA-256.

Il builder `scripts/build_v0_4_visual_atlas.py` ora rigenera i grafici di distribuzione di **tutti gli indicatori disponibili** usando il nuovo renderer, ma lascia intatta la pipeline e le figure già prodotte dalla release **v0.3**. Indicatori non acquisiti non ricevono grafici; nessuno zero viene inventato.

## Verifica

```powershell
uv run --locked pytest -q tests/test_distribution_charts_v0_4.py
uv run --locked pytest -q
uv run --locked python scripts/check_documentation.py
```

I test sintetici verificano ordine per codice ISTAT anche quando i valori sono decrescenti, presenza dei 27 nomi nei SVG, testo vettoriale, mediana, categorie SNAI, zero e input incompleti. **Il controllo visivo resta necessario** su nomi comunali reali, stampa e browser a 390 px: un SVG leggibile non è automaticamente un'interfaccia completamente accessibile.

Stato: `technical_draft_do_not_publish`, `scientific_approval=false`, `publication_allowed=false`. Nessuna modifica a dati canonici, fonti, verifiche originali, matrice o release.
