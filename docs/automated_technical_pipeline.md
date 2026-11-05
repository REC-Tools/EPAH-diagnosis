# PR #120 — Pipeline tecnica automatizzata (senza promozione dati)

Il comando `epah pipeline` orchestra **soltanto** gli script esistenti
in due profili esplicitamente consentiti. Non esegue finalizer, scrittura
nella matrice canonica, pubblicazione, mappe o PDF.

**Prima eseguire `plan`**: controlla presenza degli input, hash SHA-256
dove disponibili, compatibilità dei parametri e disponibilità della
destinazione. Non scrive file, non chiama la rete e non crea la cartella.

La modalità `run` richiede la scelta di una cartella di output **nuova**
sotto `outputs/quality/`; non sono previsti `--replace` o aggiornamenti
automatici di evidenze storiche. Il risultato è
`pipeline_run_report.json`, anche quando un passaggio fallisce.
L'output mantiene il blocco editoriale `publication_allowed: false`.

## Profilo 1: CIT Piemonte — quarantena tecnica v0.2

Richiede localmente i due CSV ufficiali Regione Piemonte già
identificati e verificati (combustibili ed età generatori). Gli hash
originali devono corrispondere **esattamente** a quelli degli script
CIT già presenti nella repository. La data `--as-of` è un riferimento
di analisi, **non** una data di aggiornamento certificata delle fonti.

Esempio PowerShell, personalizzando il percorso del secondo CSV:

~~~powershell
uv run --locked epah pipeline plan --profile cit-quarantine --fuel-source data/downloads/CIT_combustibili.csv --age-source data/downloads/CIT_eta_generatori.csv --as-of 2026-10-30 --out-dir outputs/quality/cit_pipeline_20261105_a

uv run --locked epah pipeline run --profile cit-quarantine --fuel-source data/downloads/CIT_combustibili.csv --age-source data/downloads/CIT_eta_generatori.csv --as-of 2026-10-30 --out-dir outputs/quality/cit_pipeline_20261105_a
~~~

Passaggi eseguiti in sequenza:

1. **Preflight degli originali**: esistenza, hash SHA-256 e registro dei
   Comuni (tutti prima di creare output).
2. **Preparazione tecnica** dei due CSV, con
   `--quarantine-conflicts`, in cartelle figlie distinte.
3. **QA incrociata** con `build_v0_2_cit_quarantine_comparison.py`:
   allineamento fonti, 26 Comuni coerenti, Pont Canavese (ISTAT 001199)
   escluso esplicitamente e intervalli di età min/max.
4. **Resoconto di esecuzione** JSON nel percorso scelto.

Il risultato `cit_review/cit_26_qa_summary.json` e il CSV di confronto
sono **solo materiali di revisione interna**. La procedura non produce
mappe o report PDF, non assimila i gruppi generatori a famiglie e non
attribuisce a Pont un valore zero. Prima di qualsiasi rilascio v0.2
servono chiarimenti ufficiali sui conteggi discordanti e review umana.

## Profilo 2: accessibilità — acquisizione e audit degli originali

Per usare originali **già scaricati**, indicare esplicitamente gli input:

~~~powershell
uv run --locked epah pipeline plan --profile accessibility-intake --sources road,boundaries --road-zip data/downloads/Piemonte.zip --boundaries-zip data/downloads/Limiti01012026_g.zip --out-dir outputs/quality/access_intake_20261105_a

uv run --locked epah pipeline run --profile accessibility-intake --sources road,boundaries --road-zip data/downloads/Piemonte.zip --boundaries-zip data/downloads/Limiti01012026_g.zip --out-dir outputs/quality/access_intake_20261105_a
~~~

Solo per chiedere **esplicitamente** download HTTPS delle fonti
ufficiali, omettere i file locali e aggiungere `--download`:

~~~powershell
uv run --locked epah pipeline plan --profile accessibility-intake --sources road,boundaries --download --out-dir outputs/quality/access_download_20261105_a

uv run --locked epah pipeline run --profile accessibility-intake --sources road,boundaries --download --out-dir outputs/quality/access_download_20261105_a
~~~

Fonti ammesse: `road`, `boundaries`, `school_registry`,
`school_pathways`. Con `--download` il programma può effettuare
richieste di rete **solo in modalità run**. La rete può essere bloccata
o i server possono cambiare: ogni fallimento è registrato, senza
proseguire automaticamente ad altri passaggi.

Questo secondo profilo si ferma all'**intake degli originali**:
non rigenera tempi DEA, scuole o ferrovia e non approva liste servizi,
distanze, licenze o copertura interregionale. Tali preparazioni e
audit richiedono procedure e controlli specifici.

## Failure policy

- Dati originali assenti, hash errati, cartella output esistente o
  esterna a `outputs/quality/`: **blocco prima dell'esecuzione**.
- Uno script fallisce: **interruzione immediata**, niente fasi
  successive; se il run era iniziato, conserva report e bozze
  già prodotte per analisi, senza sovrascriverle.
- I codici di uscita dei sottoprocessi e il report QA sono registrati.
- La CI prova l'orchestratore con dati sintetici e subprocess simulati.
  **Non** scarica i CSV Piemonte reali e **non** certifica una nuova
  analisi su fonti aggiornate.

Non schedulare questa pipeline in produzione finché l'approvvigionamento,
la licenza e i passaggi di review umana non saranno documentati.
