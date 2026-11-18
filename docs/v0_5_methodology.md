# v0.5: metodologia e indicatori candidati EPAH

Stato: proposta tecnica da revisionare, non nuova diagnosi approvata.
Questo documento prepara l'estensione successiva alla
[v0.4 tecnica parziale](v0_4_technical_closeout.md). Non aggiunge osservazioni
municipali e non cambia formule, periodi o denominatori esistenti.

## Fonti e distinzione fra novità e lavoro già inventariato

Fonti consultate il 18 novembre 2026:

- [EPAH, Expanding Energy Poverty Measurement in the EU (2026)](https://energy-poverty.ec.europa.eu/observatory/publications/expanding-energy-poverty-measurement-eu-integrating-new-climate-health-and),
  DOI [10.2833/9292592](https://data.europa.eu/doi/10.2833/9292592).
  PDF fornito: 145 pagine, SHA-256
  `5f4605f253e747d23576bf7dea8bd06179fd70f157775c0817ef7ae95e2fb08b`.
  Il colophon riporta giugno 2026; la pagina EPAH riporta 14 luglio 2026.
- [Dashboard EPAH](https://energy-poverty.ec.europa.eu/epah-indicators),
  con schede delle definizioni e limiti.
- [EPAH Handbook 1, A Guide to Energy Poverty Diagnosis (2023)](https://energy-poverty.ec.europa.eu/system/files/2024-05/EPAHhandbook_diagnosis_finalpdf.pdf),
  in particolare selezione degli indicatori rilevanti per il contesto locale.
- [EU Covenant of Mayors, Reporting Guidelines on Energy Poverty, settembre 2026](https://eu-mayors.ec.europa.eu/sites/default/files/2026-09/Covenant-reporting-guidelines-energy%20poverty-2026.pdf),
  edizione attualmente pubblicata dal canale richiamato dall'Osservatorio EPAH.
  È distinta dall'edizione 2025 citata nel rapporto: non aggiorna lo storico.

Il rapporto 2026 aggiorna **cinque** indicatori e ne introduce **nove** nel
dashboard nazionale (pp.16 e 31-33). Novità EPAH non significa novità rispetto
all'inventario locale H01-H56: AROP era già H41; discomfort, arretrati e indicatori
di spesa erano già identificati ma non implementati. Gli ID `V05-01`–`V05-18`
sono locali a questa proposta, non codici ufficiali EPAH o nuovi ID canonici.

## Catalogo verificabile delle proposte

Il [catalogo JSON](v0_5_indicator_contracts.json) comprende nove novità, cinque
aggiornamenti e quattro priorità già presenti nelle fonti EPAH. Ogni scheda
esplicita fonte/localizzatore, dataset, ruolo, unità statistica, universo,
numeratore, denominatore, periodo, geografia, limiti e decisioni pendenti.

| ID | Indicatore | Fonte/localizzatore | Uso da valutare |
| --- | --- | --- | --- |
| V05-01 | Eccesso di mortalità estivo | Rapporto §4.1 pp.34-37, EUROMOMO | Contesto nazionale, non attribuzione causale alla PE |
| V05-02 | Giorni di stress da freddo | §4.2 pp.38-42, Copernicus/Thermal Trace | Esposizione; adattamento grigliato separato |
| V05-03 | Giorni di stress da caldo | §4.3 pp.43-47, Copernicus/Thermal Trace | Esposizione, non ondate di calore o discomfort indoor |
| V05-04 | Persone 16+ in abitazioni migliorate negli ultimi cinque anni | §4.4 pp.48-52, `ilc_lvhe08` | Campo/benchmark; non edifici ristrutturati all'anno |
| V05-05 | Rischio di povertà AROP | §4.5 pp.53-56, `ilc_li02` | Contesto reddituale; non proxy IRPEF né AROPE |
| V05-06 | Deprivazione materiale/sociale e possesso dell'auto | §4.6 pp.57-60, DG EMPL/Oeko-Institut | Intersezione da osservare, non prodotto di margini |
| V05-07 | Quota della spesa di consumo destinata ai trasporti | §4.7 pp.61-65, `nama_10_cp18` | Benchmark; denominatore spesa, non reddito |
| V05-08 | Impossibilità economica di possedere un'auto | §4.8 pp.66-69, `ilc_mddu05` | Domanda di campo distinta dal semplice non possesso |
| V05-09 | Frequenza di utilizzo del trasporto pubblico | §4.9 pp.70-73, `ilc_atst01` | Domanda di campo distinta da frequenza delle corse |
| V05-10 | Eccesso di mortalità invernale aggiornato | §3.1 pp.17-19, EUROMOMO | Z-score; non vecchio indice percentuale |
| V05-11 | Tipo di riscaldamento usato nell'abitazione | §3.2 pp.20-21, modulo EU-SILC 2023 | Dotazione/uso; unità da verificare, non generatori CIT |
| V05-12 | Abitazione non confortevolmente calda in inverno | §3.3 pp.22-24, EU-SILC 2023 | Comfort fisico distinto da affordability |
| V05-13 | Famiglie senza comfort estivo | §3.4 pp.25-27, `ilc_hcmp03` | Famiglie, non persone della serie precedente |
| V05-14 | Spesa per finalità COICOP 2018 | §3.5 pp.28-30, `nama_10_cp18` | Distribuzione dei consumi nazionali |
| V05-15 | Incapacità economica di riscaldare adeguatamente | Scheda EPAH; inventario H34 | Prima raccolta locale proposta |
| V05-16 | Arretrati sulle utenze | Scheda EPAH; H33 | Prima raccolta locale proposta, inclusa acqua se nella domanda |
| V05-17 | Rapporto spesa energetica/reddito oltre 2M | Scheda EPAH; H36 | Richiede microdati, pesi e mediana nazionale coerente |
| V05-18 | Spesa energetica assoluta sotto M/2 | Scheda EPAH; H18 | Richiede microdati e soglia nazionale; non consumo medio |

Nessuna serie nazionale è una stima dei 27 Comuni. Una successiva elaborazione
locale avrà un contratto distinto e una decisione metodologica, anche quando
riusa la stessa domanda. Gli anni nel catalogo descrivono l'edizione consultata,
non un'acquisizione effettuata o un periodo automaticamente scelto per la diagnosi.

```powershell
uv run --locked epah methodology check --catalog docs/v0_5_indicator_contracts.json
```

Il comando controlla il contratto dei metadati: restituisce esplicitamente
`municipal_series_added: 0` e approvazioni false. Non verifica dati non acquisiti,
non esegue formule e non approva il metodo. Il workflow completo richiede ancora
il checkout dei sorgenti.

## Standard comune da applicare alla v0.5

1. **Contesto e ipotesi.** Collegare ogni indicatore a una domanda diagnostica
   e al lavoro sul campo. Separare esito dichiarato, esposizione, contesto e
   misura di servizio; nessun punteggio composito o graduatoria implicita.
2. **Identità statistica.** Definire unità (persone, famiglie, edifici, impianti,
   contribuenti, celle), universo, numeratore, denominatore, pesi e filtro di
   eleggibilità. Dichiarare esplicitamente gli elementi non applicabili.
3. **Tempo e geografia.** Separare anno dell'indagine, del reddito, del fenomeno
   e dell'acquisizione. Legare i codici ISTAT a versione del registro e confini;
   non trasferire benchmark nazionali o regionali alle osservazioni comunali.
4. **Tracciabilità.** Conservare originale/versione/licenza, hash, dizionario,
   trasformazioni e normalizzati. Metadati e approvazioni devono riferirsi
   allo snapshot esatto, non a un nome generico di cartella.
5. **Assenze e controlli.** Zero resta zero; assenza, non risposta, non applicabilità
   e soppressione non vanno imputate. Le categorie future richiedono estensione
   esplicita del contratto: la v0.4 conserva il suo `not_acquired`.
6. **Comparabilità.** Documentare rotture di serie, soglie, COICOP e cambi di unità.
   Una corrispondenza tematica nell'inventario non è equivalenza statistica.
7. **Revisione.** Tenere distinti integrità/replay, revisione tecnica del revisore,
   evidenza raccolta con stakeholder/famiglie e autorizzazione alla diffusione.
   Nessun PASS software promuove gli stati successivi.

## Protocollo locale da deliberare prima delle nuove osservazioni

Per iniziare dalle fonti climatiche e abitative seguire il
[primo workflow v0.5](v0_5_local_collection_workflow.md). `epah methodology prepare`
prepara un dossier da compilare, preservando il contratto nazionale e lasciando
aperte le decisioni locali. Non autorizza raccolta, calcolo o pubblicazione.

Per la rendicontazione, le linee CoM 2026 (p.3) richiedono di esplicitare persone
o famiglie quando applicabile, anno base e livello corrente. Il monitoraggio
aggiunge periodi e obiettivi dichiarati. La notazione `NE` (non stimato) è un
vocabolario della rendicontazione, distinto dal `not_acquired` dello snapshot:
servirà un raccordo esplicito, senza convertire assenze in zero o inventare target.
Il presente catalogo non dichiara conformità automatica a MyCovenant.

Per la prima iterazione proporre V05-15/V05-16, comfort inverno/estate
(V05-12/V05-13) e mobilità (V05-08/V05-09). Il questionario deve separare
capacità economica, comfort fisico, disponibilità e uso dei servizi.

Prima della raccolta fissare: unità intervistata, periodo di richiamo,
formulazione/versione della domanda, risposte possibili incluse non risposte,
campione e canale di reclutamento, copertura geografica, conteggi eleggibili,
contattati, rispondenti e risposte valide. Eventuali pesi e criteri di divulgazione
richiedono una decisione esplicita. Conservare soltanto aggregati autorizzati
nel progetto; nessun dato personale nel repository.

Interviste agli stakeholder e indagini di prossimità producono evidenze locali
utili, ma senza disegno rappresentativo descrivono i partecipanti: non stimano
prevalenze comunali. Registri CISS/servizi descrivono utenti, non tutti i residenti.
Validazione dell'interpretazione e verifica numerica sono ricevute distinte.

## Decisioni scientifiche aperte, con evidenza richiesta

- **Mortalità, p.17:** la descrizione di x/mu appare invertita rispetto alla
  convenzione dello z-score. Usare solo serie pubblicate come benchmark;
  prima di ricalcolare ottenere definizione/modello EUROMOMO e chiarimento.
- **UTCI, pp.38/43:** il testo alterna wording su temperature min/max e indice
  bioclimatico. Acquisire specifiche della variabile/prodotto, classi, calendario,
  maschera e metodo spaziale. Non usare i soli Tmin/Tmax del dossier H03/H04.
- **Spesa, pp.28/61/63:** compare wording sul reddito ma il dataset è presentato
  come quota dei consumi totali. Confermare unità/codici nell'export Eurostat;
  nessuna sostituzione silenziosa del denominatore.
- **Persone/famiglie:** le schede di affordability usano wording e label non
  sempre uniformi; p.25 esplicita invece il passaggio alle famiglie per il comfort
  estivo. Verificare metadati e pesi dell'edizione concreta, senza fusioni o `100-x`
  automatici tra serie 2007/2012 e 2023.
- **MSD e auto, pp.57-58:** confermare il denominatore del dato congiunto e la
  definizione MSD precedente al 2020 prima di un adattamento locale.

## Sequenza di implementazione

Pista complementare già collegata dall'[Osservatorio EPAH](https://energy-poverty.ec.europa.eu/observatory):
il [Transport Poverty Hub del JRC](https://regions-and-cities.ec.europa.eu/cities-portal/eu-initiatives-cities/transport-poverty-hub_en)
descrive accessibilità multimodale e l'Osservatorio indica anche aggregazioni LAU.
È una pista per H26/H27/H28, non una serie comunale già acquisita. Il tentativo
di accesso al dashboard del 18 novembre ha richiesto EU Login: nessun accesso
aggirato o dato scaricato. Prima dell'uso servono export autorizzato, versione
LAU, raccordo ISTAT dei 27, modalità, periodi, servizi e denominatori. Non
confondere queste misure con la frequenza d'uso dichiarata V05-09.

Prima: protocollo e campione per le misure dichiarate di comfort/affordability
e mobilità, con tua revisione documentata. Poi: eventuale estrazione grigliata
UTCI e dati sulle riqualificazioni, ognuno con replay indipendente. A seguire:
benchmark AROP/2M/M2 e mortalità con limiti espliciti. Estendere catalogo,
contratti e audit della v0.5 insieme, mantenendo intatti i 16 slot storici della
v0.4. Questa proposta non dichiara la v0.5 completata.
