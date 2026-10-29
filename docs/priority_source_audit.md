# Audit delle tre fonti prioritarie (prima della release v0.1)

**Ambito:** 27 Comuni × 3 indicatori = 81 osservazioni da verificare:
\`heating_degree_days\`, \`mean_altitude\`, \`snai_classification\`.

## Fonti istituzionali e anni distinti

| Indicatore | Autorità | Originale | Periodo del dato |
| --- | --- | --- | --- |
| Gradi-giorno | Dipartimento delle Finanze | DPR 412/1993, Allegato A consolidato | In vigore dal 09/08/2016 |
| Altitudine media | ISTAT | \`Altimetria_Comuni-al-31_12_2021.xlsx\` | Geografia al 31/12/2021; pubblicato 15/04/2026 |
| SNAI A–F | Dipartimento Politiche di Coesione | Mappa Aree Interne 2020, elenco Comuni | Classificazione 2020, ciclo 2021–2027 |

Link alle **pagine istituzionali**, più affidabili dei permalink
del singolo allegato perché le cartelle di pubblicazione possono cambiare:

- [DPR 412/1993 Allegato A](https://def.finanze.it/DocTribFrontend/getAttoNormativoDetail.do?ACTION=getArticolo&articolo=Allegato+A&codiceOrdinamento=60A+++++0000000&id=%7B0E4DC3BD-3B00-45E2-9CA6-B4DECB631C36%7D)
- [ISTAT statistiche geografiche comunali](https://www.istat.it/classificazione/principali-statistiche-geografiche-sui-comuni/)
- [Mappa Aree Interne 2020](https://politichecoesione.governo.it/it/politica-di-coesione/strategie-tematiche-e-territoriali/strategie-territoriali/strategia-nazionale-aree-interne-snai/le-aree-interne-2021-2027/mappa-aree-interne-2020/)

ISTAT altimetria deriva dal DEM e dalle basi territoriali 2021.
**Non** usare come sostituto l'altitudine del Municipio: sono variabili
diverse. Per SNAI mantenere la classe A-F, senza attribuirle un
punteggio numerico.

## Esecuzione su Windows (dalla cartella della repository)

### Opzione 1 — Download diretto dei file istituzionali

```bat
python scripts/audit_priority_sources.py --download --out-dir outputs\quality\priority_audit_20261029
```

Il comando tenta il download dai tre indirizzi ufficiali registrati e
controlla formato, copertura comunale, valori e checksum.
Se un portale risponde con HTML di login, blocco o errore, lo
segnala come **download_failed** o **blocked**. Non aggira CAPTCHA
o sistemi di protezione e non inventa dati.
Un blocco può essere risolto con i file scaricati manualmente
dal browser.

### Opzione 2 — Originali già scaricati (consigliata se il portale blocca gli script)

Salvare il file XLSX ISTAT e il file XLSX SNAI, mantenendo i nomi
originali e la data di download. Per l'Allegato A aprire la pagina
ufficiale, scegliere la versione **in vigore dal 09/08/2016**
e salvare la **pagina HTML completa** (non un PDF scansionato
o una schermata). Il parser richiede il testo in chiaro:
\`TO F 3270 611 PRATIGLIONE\` è un esempio reale della versione consolidata.

```bat
python scripts/audit_priority_sources.py --altitude-xlsx "C:\Dati\Altimetria_Comuni-al-31_12_2021.xlsx" --snai-xlsx "C:\Dati\20220214-mappa-ai-2020-elenco-e-classificazione-comuni.xlsx" --annex-html "C:\Dati\AllegatoA2016.html" --out-dir outputs\quality\priority_audit_manual --strict
```

Il report \`audit.json\` distingue:
- \`technical_pass\`: file coerente, copertura 27/27, dati parsabili;
- \`blocked\`: mancata coincidenza o anomalia;
- \`download_failed\`: non è stato possibile acquisire l'originale;
- \`not_acquired\`: nessun file fornito.

Ogni output viene scritto in \`outputs/quality/\`, escluso dal Git.
Nessuna modifica automatica a \`verification_matrix.csv\`,
nessun file di review approvato artificialmente.

## Regole per passare da QA tecnica a valore validato

1. Conservare il **file originale** con URL ufficiale, data, licenza
   e SHA-256; documentare chi l'ha scaricato e il periodo del dato.
2. Confermare l'identità dei 27 Comuni e confrontare i **codici
   ISTAT del periodo storico** con l'anagrafe 2026. Una coincidenza
   automatica non prova che il crosswalk sia stato verificato.
3. Per **altitudine** confrontare almeno tre righe raw e i relativi
   min/media/max; per **SNAI** tre classi A-F e la definizione
   ufficiale, senza numerizzarle.
4. Per **gradi-giorno** confrontare *tutte le 27 righe* nel testo
   consolidato ufficiale 2016. Controllare quota, zona, GG e
   la data di entrata in vigore.
5. Registrare reviewer reale, data, fonte di evidenza persistente
   e decisione motivata. La stringa "approved" in un JSON
   non costituisce di per sé un controllo scientifico.
6. Solo allora eseguire i **finalizzatori protetti** PR-03/PR-05,
   verificando il diff di esattamente 27 righe per indicatore.

La nuova finalizzazione dei gradi-giorno richiede ora
\`--official-html\` e l'evidenza
\`official_annex_sha256\` del file confrontato più
\`official_annex_rows_verified=27\`.

L'indicatore è corretto solo se passa entrambe le soglie:
**QA dei valori ufficiali e revisione metodologica indipendente**.

## Limiti dell'audit e stato iniziale

Il presente ambiente di sviluppo non può accedere direttamente ai
binari XLSX dei portali istituzionali: la verifica delle loro 54 righe
non è stata completata. La tabella HTML ufficiale dell'Allegato A
conferma la riga di Pratiglione con **quota 611 m**, mentre il
riferimento *storico* usato nella PR-03 riportava 711 m. Questa
osservazione non è sufficiente per approvare i 27 GG senza esaminare
l'intera pagina originale.

**Non promuovere alcuna riga** finché i report e l'approvazione
delle fonti reali non siano stati prodotti e controllati.

## Correzione parsing data del DPR (PR-08b)

Se il primo audit ha riportato:
`ValueError: Current consolidated Annex A version date 09/08/2016 not found`,
non significa che i gradi-giorno siano sbagliati. Il vecchio verificatore
usciva prima di tentare l'estrazione dei 27 Comuni. Il verificatore nuovo:
- accetta l'edizione esplicitamente indicata come *in vigore dal*
  `09/08/2016`, `09.08.2016`, `9 agosto 2016`
  o `2016-08-09` nei testi o negli attributi HTML;
- conta comunque righe della tabella e differenze di zona, GG e quota;
- mostra `blocking_reason=legal_edition_metadata_missing`
  se il testo contiene tutti i numeri ma non la prova della versione;
- mostra `blocking_reason=incomplete_official_table`
  se la pagina scaricata è solo un contenitore privo delle righe;
- **non** assume un'edizione solo dal dominio web o dall'URL;
- non promuove alcun dato senza la revisione umana.

Non sovrascrivere `audit.json` o gli originali già acquisiti.
Usare una directory nuova, riutilizzando i byte esatti dei tre input:

```bat
python scripts/audit_priority_sources.py --annex-html "outputs\quality\priority_source_audit\raw\dpr412_allegato_a_2016.html" --altitude-xlsx "outputs\quality\priority_source_audit\raw\istat_altimetria_comuni_2021.xlsx" --snai-xlsx "outputs\quality\priority_source_audit\raw\snai_mappa_aree_interne_2020.xlsx" --out-dir "outputs\quality\priority_source_audit_v2" --strict
```

Aprire poi `outputsqualitypriority_source_audit_v2audit.json`:
la sezione `indicator_results.heating_degree_days`
contiene ora `rows_examined`, `values_match_on_27_municipalities`,
`edition_marker_present`, `blocking_reason`,
`missing_municipalities` e `differences`.

Se `rows_examined=27` ma la data manca, la
versione può essere documentata separatamente dal portale ufficiale,
con evidenza reale di revisione: non va aggiunta arbitrariamente
al file originale e non si deve falsificare la sua provenienza.
Se `rows_examined=0`, salvare la versione HTML
del **testo completo**, non la pagina introduttiva o un iframe.


## PR-08c: scaricare il testo stampabile, non il guscio HTML del portale

L'audit reale su Windows ha confermato che l'URL del dettaglio articolo
\`getAttoNormativoDetail.do\` puo restituire una pagina HTML senza
**ne titolo, ne date, ne righe comunali** (\`rows_examined=0\`).
Le fonti ISTAT/SNAI sono invece state acquisite e hanno superato i
controlli tecnici. Non ripetere inutilmente quei download.

Il downloader HDD ora usa il **testo ufficiale stampabile** del
Dipartimento delle Finanze:
https://def.finanze.it/DocTribFrontend/executePrintArticolo.do?articolo=Allegato+A&codiceOrdinamento=60A+++++0000000&id=%7B0E4DC3BD-3B00-45E2-9CA6-B4DECB631C36%7D

La pagina di consultazione rimane l'evidenza della versione normativa:
https://def.finanze.it/DocTribFrontend/getAttoNormativoDetail.do?ACTION=getArticolo&articolo=Allegato+A&codiceOrdinamento=60A+++++0000000&id=%7B0E4DC3BD-3B00-45E2-9CA6-B4DECB631C36%7D

Se il portale ritorna ancora una pagina HTML senza il testo della
norma, il downloader la **rifiuta prima di salvarla**. Non assegna
automaticamente uno stato "validato" e non disattiva la verifica del
testo vigente (09/08/2016).

### Esempio Windows: riprovare soltanto l'Allegato A

Dopo il merge della PR e \`git pull origin main\`, dalla root repo:

\`\`\`bat
python scripts/audit_priority_sources.py --download --altitude-xlsx "outputs\quality\priority_source_audit\raw\istat_altimetria_comuni_2021.xlsx" --snai-xlsx "outputs\quality\priority_source_audit\raw\snai_mappa_aree_interne_2020.xlsx" --out-dir "outputs\quality\priority_source_audit_v3" --strict
\`\`\`

I due XLSX originali rimangono invariati. \`--download\` viene usato
soltanto per l'indicatore senza un file specificato, quindi unicamente
\`heating_degree_days\`. La vecchia pagina non valida rimane
nell'archivio del primo tentativo, a disposizione dell'audit.

Se anche la pagina stampabile non viene restituita correttamente da
Python, aprire il link del **testo stampabile** nel browser; controllare
che compaia la tabella (per esempio \`TO F 3270 611 PRATIGLIONE\`)
e salvare l'HTML completo in un file diverso. Passarlo esplicitamente
con \`--annex-html\` e una directory \`--out-dir\` nuova.
Se il testo stampabile appare solo come PDF, non rinominare il PDF in
HTML: il verificatore non accetta documenti di altro tipo.

Per completare l'audit, il report deve contenere per HDD:
\`rows_examined=27\`, \`missing_municipalities=[]\`,
\`differences=[]\`, \`edition_marker_present=true\`,
\`technical_comparison=true\`. Nessun dato viene promosso finché
non viene completata una vera revisione umana delle tre fonti.

