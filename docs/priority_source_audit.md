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
