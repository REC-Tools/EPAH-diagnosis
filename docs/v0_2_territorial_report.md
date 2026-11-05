# V0.2 territoriale - rapporto tecnico separato dal CIT

La versione 0.2 può ora fare un passo avanti **senza attendere**
il chiarimento CIT: genera un rapporto più leggibile sul patrimonio
edilizio, sulle condizioni socioeconomiche e sull'accessibilità,
utilizzando i **nove indicatori già presenti nel bundle pilota
tecnicamente accettato v0.1**.

Non è una release istituzionalmente approvata: il documento,
il JSON dei risultati e il manifest riportano obbligatoriamente
`technical_draft_do_not_publish`. Non si inseriscono valori CIT
incompleti e non si modifica la matrice canonica.

## Prima esecuzione su Windows

Preparare il bundle v0.1 con i controlli già documentati, se
non è già presente. Dal repository principale:

~~~powershell
git pull --ff-only origin main
uv sync --python 3.11 --locked --group dev
uv run --locked epah report v0.2 --bundle outputs/v0.1.0-pilot --out-dir outputs/v0.2-territorial-technical
~~~

L'output deve essere una **nuova** cartella: non viene
sovrascritto un rapporto esistente.

Il comando controlla la copertura 27 Comuni × 9 indicatori,
le geometrie, il PDF e il workbook v0.1 e gli hash degli
artefatti presenti nel manifest di origine, prima di creare
il nuovo report. Se un input è stato modificato, manca o
non corrisponde al registro comunale, **si ferma**.

## Tre output

| Percorso | Contenuto |
| --- | --- |
| `diagnostic_report_v0_2_technical.pdf` | Rapporto italiano di circa nove pagine, con executive summary, ipotesi, due mappe già calcolate, variabilità tra Comuni, lettura incrociata, limiti e azioni. |
| `diagnostic_facts_v0_2.json` | Statistiche effettivamente ricalcolate dai 27 profili, anni, unità, mediane e conteggi descrittivi. |
| `report_manifest_v0_2.json` | Hash SHA-256 del manifest v0.1, del CSV di origine, delle mappe e dei nuovi artefatti; indicazione esplicita dello status editoriale. |

La lettura incrociata conta Comuni al di sopra delle
rispettive **mediane comunali**, senza trasformarle
in un indice composito, un ranking di rischio o
una stima di famiglie in povertà energetica.

Le mappe restano quelle del pilota v0.1 e conservano
anni, legenda e limitazioni. Gli originali e le
altre sette mappe rimangono nel bundle di partenza.

## Limiti e controlli successivi

- La v0.2 non produce **nuovi dati osservati** e non
  attesta una validazione scientifica aggiuntiva.
- Il rapporto comprende i soli indicatori pilota:
  nessun dato CIT quarantinato né inferenza su
  consumi o spesa energetica domestica.
- Il documento usa testo di riconoscimento EPAH TA
  senza importare loghi originali non ancora verificati.
  Il nametag autorizzato andrà integrato in una fase
  editoriale successiva con proporzioni invarianti.
- L'output PDF deve essere anche controllato
  **visivamente** su Windows prima di qualunque
  condivisione esterna; i test CI verificano struttura,
  testo, paginazione e provenienza, non la resa grafica
  di ogni pagina.

Per una versione pubblicabile servono revisioni
scientifica, istituzionale e comunicativa indipendenti.
La precedente v0.1 resta immutata.
