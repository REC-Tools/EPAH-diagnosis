# PR-09b | ISTAT CPA 2011 — acquisizione, ricontrollo indipendente e QA

**Obiettivo:** 27 Comuni della Green Community Sinergie in Canavese,
indicatore \`old_building_stock\`. Il Censimento **2011** misura una
dimensione storica, non la prestazione energetica degli edifici nel 2026.

## Fonte e metodo

- ISTAT (autore ufficiale):
  https://www.istat.it/notizia/basi-territoriali-e-variabili-censuarie/
- Archivio delle variabili sezionali CPA 2011:
  https://www.istat.it/storage/cartografia/variabili-censuarie/dati-cpa_2011.zip
- Documentazione ISTAT edifici 2011:
  https://www.istat.it/comunicato-stampa/edifici-e-abitazioni-nuovi-dati-del-15-censimento-generale-della-popolazione-e-delle-abitazioni-anno-2011/

Formula **edifici residenziali pre-1981** = \`(E8+E9+E10+E11+E12)/E3*100\`.
L'E3 e il numero degli edifici residenziali, gli E8-E12 sono le cinque
classi di costruzione ante 1981. I benchmark per Green Community,
Piemonte e Italia **non** sono medie semplici dei rapporti comunali, ma
\`somma_numeratori / somma_denominatori\`.

**Avvertenze metodologiche:** immobili che hanno subito riqualificazioni
dopo il 2011 non vengono riconosciuti. E3 e il numero di edifici
residenziali, non di alloggi o famiglie. I codici ISTAT al 2011
richiedono crosswalk e revisione per il perimetro attuale, senza inferire
che l'assenza di un cambio amministrativo equivalga ad aggiornamento edilizio.

## Come usare su Windows

Dopo il merge di questa PR e l'aggiornamento della cartella locale,
dal prompt nella root di EPAH-diagnosis:

\`\`\`bat
git pull origin main
python scripts/audit_building_stock_source.py --download
\`\`\`

Lo script scarica in:
\`outputs\\quality\\istat_building_stock_2011_original\\dati-cpa_2011.zip\`.

Il download segue solo URL \`https://*.istat.it\`, rifiuta redirect
a un altro dominio, HTML al posto dello ZIP, archivi senza R01,
oltre 900 MiB e file gia presenti. Registra il checksum SHA-256,
senza ricreare o sovrascrivere l'originale.

**Se il portale ISTAT blocca il download automatico:**
aprire la pagina ufficiale nel browser, scaricare e salvare lo ZIP
originale senza modificarlo. Poi:

\`\`\`bat
python scripts/audit_building_stock_source.py --source-zip "C:\\Dati\\dati-cpa_2011.zip" --out-dir "outputs\\quality\\istat_building_stock_2011_manual"
\`\`\`

Il secondo metodo esegue esattamente i medesimi controlli.

## Output e prove

In \`outputs/quality/istat_building_stock_2011/\`:

- \`building_stock_2011.csv\` — 27 numeratori, denominatori,
  epoche, percentuali e codice ISTAT;
- \`building_stock_benchmarks_2011.csv\` — GC/Piemonte/Italia,
  benchmark ponderati;
- \`building_stock_qa.json\` — QA originale e SHA-256;
- \`independent_raw_r01_audit.json\` — ricalcolo per ogni Comune
  a partire dalle **righe grezze** R01 del censimento;
- \`source_audit_manifest.json\` — manifest con hash degli output,
  periodo e indicatori espliciti di review ancora mancanti.

L'analisi numerica indipendente **non riutilizza** il parser di
aggregazione CPA del progetto: rilegge i campi E3 e E8-E16 del CSV
regionale, per ogni sezione e codice ISTAT. Rifiuta \`..\`, vuoti,
valori non interi, negativi o inesistenti per uno dei 27 Comuni.
Confronta l'intera sequenza delle epoche costruttive e i benchmark,
segnalando ogni differenza.

**Niente fallback statistico:** non imputare 0 in presenza di valori
soppressi, non utilizzare percentuali regionali per colmare Comuni
mancanti e non prendere i file di fixture sintetici come dati reali.

## Gate per approvazione umana

Un \`technical_pass\` del nuovo audit non equivale a \`Dato validato\`.
Prima della promozione occorre che un revisore:

1. verifichi URL istituzionale, formato del file, hash, data di acquisizione
   e condizioni di riutilizzo delle variabili censuarie;
2. verifichi il crosswalk fra il codice ISTAT dei 27 Comuni nel 2011 e il
   registro 2026;
3. confronti E3 e E8-E12 su un campione indipendente di almeno tre Comuni
   nell'originale ZIP;
4. confronti i benchmark GC/Piemonte/Italia e annoti le limitazioni
   della datazione 2011;
5. documenti nome del revisore, data, decisione e link HTTPS persistente
   alla sua approvazione.

**Solo dopo** usare il finalizzatore gia presente:

\`\`\`bat
python scripts/finalize_building_stock_single_source.py --source-zip "outputs\\quality\\istat_building_stock_2011_original\\dati-cpa_2011.zip" --draft-dir "outputs\\quality\\istat_building_stock_2011" --approval "C:\\Dati\\building_stock_approval.json"
\`\`\`

Il finalizzatore controlla esattamente gli hash dell'originale,
del draft e del registry, non solo una casella \`decision: approved\`.

## Stato corrente dopo PR-09a

- 135/243 osservazioni già validate e promosse nella matrice \`main\`.
- Queste 27 osservazioni **restano Da verificare** finché non siano
  stati analizzati i byte reali e completata la revisione umana.
- La v0.1 resta \`NOT READY\`: dopo il patrimonio edilizio, i tre
  indicatori di accessibilità DEA, scuole superiori e ferrovia
  richiedono ancora 27 confronti ciascuno.

Il file ZIP ufficiale non e stato scaricato dal container durante
questa PR; nessun dato comunale del 2011 e inventato o committato.
