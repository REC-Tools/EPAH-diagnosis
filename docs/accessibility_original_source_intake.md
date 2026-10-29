# PR-10 — Acquisizione degli originali per i tre indicatori di accessibilità

**Ambito:** 27 Comuni × 3 indicatori = 81 osservazioni da
completare: accesso DEA I/II, poli della scuola secondaria superiore
e gateway ferroviari attivi.

## Fonti e annualità (non intercambiabili)

| Sorgente | Documento originale | Periodo | Verifica |
| --- | --- | --- | --- |
| Strada | [ISTAT matrici distanza/tempo](https://www.istat.it/notizia/matrici-di-contiguita-distanza-e-pendolarismo/), \`Piemonte.zip\` | Comuni 2021, grafo 2020 | \`OR_PROCOM\`, \`DEST_PROCOM\`, \`TEP_TOT\` |
| Confini | ISTAT \`Limiti01012026_g.zip\` | Comuni 2026 | archivi \`.shp/.dbf/.shx\` + join codici |
| DEA | [Ministero della Salute, rete emergenza](https://www.salute.gov.it/new/it/banche-dati/elenco-strutture-della-rete-dellemergenza-ospedaliera/) | strutture attive 31/12/2025 | livelli DEA I/II nazionali |
| Scuole | [MIM, anagrafe scuole statali](https://dati.istruzione.it/opendata/ricerca/?searchinput=SCUANAGRAFESTAT) | disponibile fino 2026/27 | codici, sedi, stato |
| Percorsi | [MIM, indirizzi scuole secondarie](https://dati.istruzione.it/opendata/opendata/catalog/ALUSECGRADOINDSTA) | ultima distribuzione visualizzata 2024/25 | liceo classico/scientifico + tecnico/professionale |
| Ferrovia | [SFM1](https://www.sfmtorino.it/le-linee-sfm/sfm1-pont-rivarolo-chieri/) e RFI | operatività da controllare 2026 | verificare bus sostitutivi e stazioni realmente attive |

È scorretto incrociare il solo **registro MIM 2026/27** con
**percorsi attivi 2024/25** e definirli "offerta scolastica 2026/27".
Per una proxy 2024/25 si conserva una coppia di file originali
dello stesso anno; il registro più recente è materiale per
un ulteriore controllo storico, non una correzione tacita.

La rete di destinazioni DEA attualmente usata dalla pipeline è
limitata al Piemonte ed è uno snapshot locale 2023/2025;
prima della promozione occorre confrontarla con l'elenco nazionale
del Ministero per l'anno **2025**. Anche una struttura fuori regione
può essere più vicina. Per la ferrovia il riferimento
\`canavese_active_rail_gateways.csv\` è curato: non garantisce copertura
di tutte le stazioni ammissibili.

## Fase A — scaricare gli originali stradali e geografici

Dopo il merge della PR e aggiornamento della copia Windows:

\`\`\`bat
git pull origin main
python scripts/acquire_accessibility_inputs.py --download --sources road,boundaries --out-dir outputs\quality\access_inputs_road_20261029 --strict
\`\`\`

Il programma:
1. scarica in modalità streaming i documenti originali da URL fissi
   e rifiuta redirect fuori dal provider HTTPS previsto;
2. controlla la presenza di un vero ZIP invece di una pagina HTML;
3. verifica che un CSV della matrice abbia almeno
   \`OR_PROCOM\`, \`DEST_PROCOM\`, \`TEP_TOT\` e che il confine comunale
   abbia \`.shp/.dbf/.shx\`;
4. registra file, URL, checksum SHA-256, dimensioni, anno del dato e
   \`technical_preflight_pass\` in \`audit.json\`;
5. mantiene tutti i dati nel percorso escluso da Git
   \`outputs/quality/\`, senza promuovere righe in matrice.

Se ISTAT non permette il download automatico, scaricare
\`Piemonte.zip\` e \`Limiti01012026_g.zip\` dai portali ufficiali,
salvarli localmente e verificare i file con:

\`\`\`bat
python scripts/acquire_accessibility_inputs.py --road-zip "C:\Dati\Piemonte.zip" --boundaries-zip "C:\Dati\Limiti01012026_g.zip" --out-dir "outputs\quality\access_inputs_manual" --strict
\`\`\`

Non rinominare un HTML o un documento non originale con estensione ZIP.

## Fase B — originali per la scuola secondaria

Il comando scarica solo l'anno coerente **2024/25** per
registro e percorsi:

\`\`\`bat
python scripts/acquire_accessibility_inputs.py --download --sources school_registry,school_pathways --out-dir outputs\quality\access_inputs_mim_202425 --strict
\`\`\`

Se MIM restituisce HTML, scaricare i due **CSV originali** dell'anno
scolastico 2024/25 dal browser, quindi ripetere l'audit locale
con \`--school-registry\` e \`--school-pathways\`.

Il dataset ministeriale sulle strutture DEA 2025 è reperibile
direttamente alla pagina istituzionale: salvarne l'XLSX
originale e il dizionario dati, poi confrontarlo al
file \`data/reference/piemonte_dea_hospitals.csv\`.
Lo script di acquisizione non deduce automaticamente livelli DEA
da nomi ospedalieri: tale review è ancora indipendente.

## Fase C — produrre bozze, non dati validati

Con gli originali locali disponibili:

\`\`\`bat
python scripts/prepare_dea_accessibility.py --road-zip "outputs\quality\access_inputs_road_20261029\raw\Piemonte.zip" --boundaries-zip "outputs\quality\access_inputs_road_20261029\raw\Limiti01012026_g.zip" --out-dir outputs\quality\dea_accessibility
python scripts/prepare_education_rail_access.py --indicator rail_accessibility --road-zip "outputs\quality\access_inputs_road_20261029\raw\Piemonte.zip" --boundaries-zip "outputs\quality\access_inputs_road_20261029\raw\Limiti01012026_g.zip" --out-dir outputs\quality\rail_accessibility
python scripts/prepare_education_rail_access.py --indicator upper_secondary_accessibility --road-zip "outputs\quality\access_inputs_road_20261029\raw\Piemonte.zip" --boundaries-zip "outputs\quality\access_inputs_road_20261029\raw\Limiti01012026_g.zip" --school-registry "outputs\quality\access_inputs_mim_202425\raw\SCUANAGRAFESTAT20242520250831.csv" --school-pathways "outputs\quality\access_inputs_mim_202425\raw\ALUSECGRADOINDSTA20242520250831.csv" --out-dir outputs\quality\upper_secondary_accessibility
\`\`\`

**Nota:** i file \`source_audit_manifest.json\` ed \`audit.json\`
sono controlli di *ingresso*, non calcoli delle 27 misure.
Le tre procedure successive verificano invece tutte le 27×N rotte,
le distanze e l'idoneità delle destinazioni, ma non la realtà operativa
dei servizi nel 2026 o le licenze, che richiedono verifiche umane.

## Prima della promozione delle ultime 81 righe

- Documentare SHA e fonte ministeriale/rfi/sfm/mim per ogni servizio.
- Ricontrollare stati DEA 2025, licei e indirizzi e tratte ferroviarie
  attive (Rivarolo–Pont Canavese gestita con bus quando questa pagina
  è stata consultata: non conteggiare Pont come stazione con treni).
- Confrontare un campione di almeno tre rotte ISTAT per indicatore,
  valutare Comuni servizi fuori Piemonte.
- Registrare approvazione umana effettiva; usare solo i finalizzatori
  review-gated già presenti, mai cambiare status a mano.
- La v0.1 resta \`NOT READY\` fino a dati completi e review metodologiche.


## Troubleshooting Windows: timeout WinError 10060 e SSL unexpected EOF

I due errori indicano una connessione HTTPS non completata o interrotta,
**non** un'incongruenza delle matrici ISTAT o dei confini. Gli URL sono
confermati dalle pagine ufficiali ISTAT. Non cambiare l'origine ufficiale
con copie non tracciabili, e non disabilitare la validazione SSL.

Dopo la PR di gestione retry, il downloader:
- riprova \`URLError\`, \`WinError 10060\`, EOF/TLS e \`IncompleteRead\`
  con un backoff limitato;
- mantiene l'originale temporaneo fra tentativi nello stesso processo,
  usando HTTP \`Range\` **solo** se il server fornisce un ETag forte
  o un \`Last-Modified\`; confronta \`Content-Range\`, lunghezza e
  versione; se il server ignora la richiesta range, ricomincia da zero;
- conserva in \`raw/\` **solo** gli originali che superano la verifica ZIP
  e lo schema; elimina sempre i \`.partial\` non validi;
- lascia \`outputs/quality/access_inputs_road/audit.json\` originale
  come evidenza del primo tentativo (0/2).

### Opzione consigliata: due download dal browser

1. Aprire la pagina [ISTAT Matrici delle distanze](https://www.istat.it/notizia/matrici-di-contiguita-distanza-e-pendolarismo/),
   scorrere fino a **Matrici delle distanze**, scegliere **Piemonte**:
   scaricare \`Piemonte.zip\`, senza estrarre.
2. Aprire [ISTAT Confini amministrativi](https://www.istat.it/notizia/confini-delle-unita-amministrative-a-fini-statistici-al-1-gennaio-2018-2/),
   tabella **2026**, colonna *Versione generalizzata (WGS84 UTM32N)*:
   scaricare \`Limiti01012026_g.zip\`, senza estrarre.
3. Conservare i file byte-identici in una cartella separata
   (es. \`C:\Dati\EPAH\`).
4. Dalla root della repo, con un **nuovo** percorso di output:

\`\`\`bat
python scripts/acquire_accessibility_inputs.py --sources road,boundaries --road-zip "C:\Dati\EPAH\Piemonte.zip" --boundaries-zip "C:\Dati\EPAH\Limiti01012026_g.zip" --out-dir "outputs\quality\access_inputs_road_manual" --strict
\`\`\`

Il verificatore calcola SHA-256 e controlla formato, schema e
integrità minima; non promuove valori. I due input restano nel percorso
\`C:\Dati\EPAH\`, non vengono copiati o rinominati automaticamente.

### Opzione automatica: retry limitato

Se si vuole riprovare la connessione Python dopo il merge:

\`\`\`bat
git pull origin main
python scripts/acquire_accessibility_inputs.py --download --sources road,boundaries --out-dir "outputs\quality\access_inputs_road_v2" --attempts 3 --timeout 45 --backoff 2 --strict
\`\`\`

Il timeout si applica a connessione / lettura, non alla durata
complessiva dello ZIP. Non aumentare indiscriminatamente tentativi
e timeout se la rete/il proxy non consente connessioni a
\`www.istat.it\`: il browser è preferibile. Provare anche una rete
differente o verificare il proxy aziendale, senza disabilitare TLS.

### Dopo un audit 2/2

Dopo avere verificato il report \`audit.json\` (e l'assenza di errori):

\`\`\`bat
python scripts/prepare_dea_accessibility.py --road-zip "C:\Dati\EPAH\Piemonte.zip" --boundaries-zip "C:\Dati\EPAH\Limiti01012026_g.zip" --out-dir "outputs\quality\dea_accessibility"
python scripts/prepare_education_rail_access.py --indicator rail_accessibility --road-zip "C:\Dati\EPAH\Piemonte.zip" --boundaries-zip "C:\Dati\EPAH\Limiti01012026_g.zip" --out-dir "outputs\quality\rail_accessibility"
\`\`\`

La scuola richiede separatamente i due CSV MIM 2024/25.
Le destinazioni DEA e ferroviarie in Piemonte richiedono revisione
scientifica indipendente (operatività delle strutture, eventuale
servizio fuori regione). La matrice \`data/verification_matrix.csv\`
rimane invariata fino ai finalizzatori umanamente approvati.

