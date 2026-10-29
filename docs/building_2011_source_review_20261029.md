# CPA 2011 — verifica originale, 27 osservazioni pronte per review

**Stato:** proposta dati in PR draft, **non ancora approvata per merge**.

I dati provengono dall'archivio ZIP di variabili censuarie ISTAT 2011
fornito nel contesto EPAH il 29 ottobre 2026; i byte dell'originale
sono stati riaperti e confrontati autonomamente con i quattro report.
URL ISTAT: https://www.istat.it/notizia/basi-territoriali-e-variabili-censuarie/
Originale: https://www.istat.it/storage/cartografia/variabili-censuarie/dati-cpa_2011.zip
Condizioni di riutilizzo: https://www.istat.it/note-legali/

## Dati verificati

- SHA-256 dell'archivio originale: \`c62af5f6cddf59623e59a4cc44b8df7e39e3f729cc19b2d720c2596886af9bcd\`.
- 52.442.848 byte di ZIP ufficiale, **20 CSV di sezione** regionali.
- 366.863 sezioni censuarie (record validi di codice), **688** nei 27 Comuni.
- 27/27 codici ISTAT, nomi comunali e tutti i campi E3 ed E8–E16
  ricontrollati in una seconda lettura indipendente.
- **0 discrepanze** fra 27 CSV comunali, aggregazioni delle sezioni e
  report della pipeline.
- Green Community: **16.218 / 18.272 = 88,76%** edifici ante 1981.
- Piemonte: **780.465 / 944.690 = 82,62%**.
- Italia: **9.028.831 / 12.187.698 = 74,08%**.
- Il rapporto regionale/nazionale qui e calcolato dalla versione
  dell'archivio sezionale indicato; verificare il vintage rispetto ad
  eventuali tavole ISTAT aggiornate o provvisorie pubblicate altrove.

## Coerenza e limiti

- Edifici censiti, non unità abitative: denominatore E3.
- La percentuale media GC è *ponderata sui numeri di edifici*,
  non la media aritmetica dei 27 tassi comunali.
- L'anno **2011** non dice nulla su riqualificazioni dal 2012 al 2026,
  classe energetica, consumi o condizioni di disagio.
- Massimi osservati (da interpretare con cautela): Ronco Canavese
  99,63%, Pertusio 99,45%, Ingria 99,23%. Tutti corrispondono
  esattamente al numero di edifici delle sezioni censuarie originali,
  ma l'elevato valore non dimostra povertà energetica.
- Nessuna percentuale dei singoli Comuni è stata stimata o interpolata.
- Il crosswalk 2011-2026 e verificato per presenza e corrispondenza
  dei codici degli attuali 27 Comuni; la revisione storica dei confini
  amministrativi richiede comunque conferma umana.

## Integrità e revisione

\`data/quality/building_stock_2011_source_evidence.json\`
contiene SHA dell'originale, SHA-256 esatti delle due elaborazioni,
copertura territoriale, controlli e un campo
\`approved_for_merge: false\`.

La richiesta di caricamento ZIP **non era un'autorizzazione alla
promozione formale**. Perciò questa PR è intenzionalmente *draft*:
le 27 righe \`Dato validato\` sono **solo una proposta di diff**, non
sono ancora state unite a \`main\`.

Prima di unire:
1. verificare la pagina ISTAT e le condizioni CC BY 4.0;
2. confermare campione grezzo di almeno tre Comuni (suggeriti
   Alpette, Castellamonte e Ronco Canavese) e limiti metodologici;
3. lasciare un commento di approvazione personale e permanente
   nella PR GitHub;
4. attendere il merge della PR di ripristino **#86**;
5. solo dopo, unire questa PR a \`main\`.

La PR di dati è **stacked** sulla #86 per evitare di riportare
per errore lo stato precedente da 54/243. Dopo entrambe le PR
approvate e unite: 162/243 osservazioni; mancano le 81
osservazioni di accessibilità DEA, scuole e ferrovia.
Le review delle metodologie v0.1 rimangono un gate a parte.


## Conservazione delle 81 righe del primo blocco

Nella struttura canonica, le prime 81 righe comprendono i tre indicatori
\`population_65_plus\`, \`income_vulnerability\` e
\`old_building_stock\`. La promozione del patrimonio edilizio modifica
**soltanto 27 righe all'interno di questo blocco**. Le altre
**54 righe** iniziali (popolazione e reddito) restano identiche;
le 162 righe successive devono mantenere il loro ordine e i valori
precedentemente verificati. Il test di conservazione e stato
aggiornato per distinguere una modifica autorizzabile dei record
edilizi da qualunque regressione dei dati socioeconomici.
