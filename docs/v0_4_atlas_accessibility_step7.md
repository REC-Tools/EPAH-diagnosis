# EPAH v0.4 — Step 7: ricerca, tastiera e consultazione mobile

**Decisione:** l'atlante HTML offline resta il punto d'ingresso principale per **tecnici e amministratori locali**. È navigabile con i controlli nativi del browser, presenta tutti i 27 Comuni in tabella e non introduce nuove misure o classificazioni.

## Modifiche dell'interfaccia

- **Ricerca più tollerante:** testo per nome (maiuscole/minuscole e accenti ignorati) o codice ISTAT. Non viene effettuata alcuna ricerca online.
- **Vai a un Comune:** secondo menu con 27 nomi e codici ISTAT, in ordine alfabetico. Dopo la scelta la tabella viene filtrata e viene posto il focus sulla riga corrispondente.
- **Ripristina:** pulsante `Mostra tutti i Comuni`, accessibile da tastiera, che azzera i filtri e riporta il focus al campo di ricerca.
- **Conteggio risultati:** aggiornamento testuale `X Comuni su 27` in una regione `aria-live`. In assenza di risultati viene mostrata una riga informativa, non un grafico vuoto né uno zero inventato.
- **Tabella semantica:** caption per screen reader, intestazioni `scope="col"`, contenitore orizzontalmente scorrevole e focalizzabile su schermi stretti. Ogni riga può essere raggiunta direttamente dal selettore.
- **Navigazione e grafici:** link rapido ai filtri, contorni di focus visibili, testi alternativi che rimandano alla tabella, PNG caricati in modo lazy, visualizzazione a colonna singola per la navigazione mobile. Rispetto di `prefers-reduced-motion`.
- **Dati mancanti:** la dicitura diventa **Non acquisito** invece di `n.d.`, senza trasformare l'assenza in zero.

## Compatibilità e verifiche

La trasformazione è implementata nel modulo `src/epah_diagnosis/atlas_accessibility_v0_4.py` e viene applicata **solo** dall'export `scripts/build_v0_4_visual_atlas.py`, dopo che l'HTML v0.4 è stato preparato. Il codice rifiuta modifiche non riconosciute al template (fail-closed). Non cambia l'HTML prodotto dal builder v0.3, gli indicatori, i 27 record, i periodi, le etichette del catalogo, le mappe o gli SHA degli originali. Il manifest v0.4 registra l'HTML aggiornato con il suo nuovo SHA.

```powershell
uv run --locked pytest -q tests/test_atlas_accessibility_v0_4.py
uv run --locked pytest -q
uv run --locked python scripts/check_documentation.py
```

I test verificano il contratto HTML, gli attributi semantici, la preservazione **byte-per-byte del payload JSON**, l'escaping di nomi potenzialmente malevoli e la presenza del nuovo controllo nel builder. Non equivalgono a un audit completo WCAG.

## Revisione manuale obbligatoria prima di diffusione

Aprire **una nuova cartella** di output v0.4 con la geometria e i dati reali locali. A larghezze 390 px, 768 px e desktop, verificare: tabulazione senza mouse, visibilità del focus, selezione di un Comune con nome lungo, ricerca con/senza accenti, messaggio senza risultati, reset dei filtri, lettura delle intestazioni con tecnologia assistiva e scorrimento della tabella senza perdere il contesto. Confrontare inoltre le osservazioni con il CSV e controllare il portale offline e il PDF stampato.

**Limitazione:** controlli statici e unit test non dimostrano conformità WCAG, navigazione assistiva corretta su ogni piattaforma o approvazione scientifica. Gli output mantengono `technical_draft_do_not_publish`, `scientific_approval=false`, `publication_allowed=false`. Nessun dato canonico, test storico v0.3 o processo di rilascio è stato alterato.

**Step 8:** revisione trasversale di provenienza, motivi di assenza, periodi e denominatori tra HTML, CSV, PDF e schede comunali.
