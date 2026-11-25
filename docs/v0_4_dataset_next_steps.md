# Prossimi passi per completare i dataset territoriali

Piano operativo del 25 novembre 2026 per il tecnico incaricato e i referenti
dei 27 Comuni. Stato: `technical_draft_do_not_publish`.
Il piano distingue fonti disponibili, verifiche da completare e acquisizioni
esterne. Non modifica indicatori, anni, denominatori o approvazioni.

## Sequenza e criteri di uscita

| Priorità | Dataset | Prossimo passo | Criterio di uscita |
| --- | --- | --- | --- |
| 1 | ERP, V05-21/V05-22 | Chiedere tramite Unione Montana gli estratti ERPS 2025 già trasmessi; integrare da ATC/Comuni le cause dello sfitto assenti | Data, perimetro, dizionario e copertura verificati; proprietà e gestione senza doppi conteggi |
| 2 | Stress da caldo UTCI, V05-03 | Riprodurre il controllo dei massimi giornalieri e degli annuali già acquisiti; revisionare il protocollo comunale | Conteggi per soglia verificabili, copertura completa delle celle contribuenti e metodo spaziale deliberato |
| 3 | APE residenziali, H05 | Ottenere l'export ufficiale comunale con classi A4–G e totale | Filtri di residenzialità, validità, deduplicazione e periodo verificati; classi riconciliate |
| 4 | ISAC, V05-20 | Verificare con ISTAT la disponibilità di una tavola comunale | Numeratore, denominatore, soglia nazionale, anno e flag documentati per il perimetro disponibile |
| 5 | Prezzo/reddito, V05-23 | Reperire un export Mapadomo Italia e la relativa metodologia | Geografia, copertura di Torino, anni e unità verificati; eventuale benchmark provinciale conservato alla sua scala |

Le richieste esterne possono essere preparate mentre si riproducono i controlli
climatici. L'invio e la ricezione restano da documentare: questo piano non
attesta contatti con enti o dataset ricevuti.

## ERP: riutilizzare il percorso esistente

Seguire la [nota di acquisizione tramite Unione Montana](v0_4_erp_acquisition_status.md)
e il [pacchetto di richiesta/importazione](v0_5_erp_request_packet.md).
Le sei risposte pubbliche ATC non costituiscono uno stock completo datato.
Le cause manutentive richiedono un aggregato specifico se non presenti in ERPS.
Per V05-21 serve inoltre un denominatore di famiglie temporalmente coerente;
per V05-22 numeratore e totale devono descrivere lo stesso perimetro.

## Caldo UTCI: verificare prima di aggiungere osservazioni

La ricognizione locale ha identificato nell'originale annuale già acquisito
i campi `utci_days_above_{26,32,38,46}_daily_max`; l'archivio giornaliero
contiene anche `utci_daily_max`. Non riacquisire automaticamente gli originali.
La [specifica CDS](https://cds.climate.copernicus.eu/datasets/derived-utci-historical?tab=overview)
distingue statistiche giornaliere in Kelvin e conteggi annuali in giorni.

La verifica esplorativa locale ha confrontato le quattro soglie con i massimi
giornalieri 2025. Le sue evidenze rimangono nell'archivio locale: questa nota
non è una ricevuta di audit né un'attestazione della CI. Prima dell'integrazione:

- riprodurre date uniche, calendario, coordinate, maschere, unità e contributi
  validi per ciascuna cella, conservando originali e hash;
- verificare gli operatori delle soglie: conteggi uguali con `>` e `>=`
  non distinguono gli estremi se non ci sono valori sul confine;
- mantenere separate le quattro classi cumulative, senza sommarle;
- revisionare copertura, pesi per superficie e limiti della griglia montana;
- distinguere il replay dei massimi giornalieri dalla ricostruzione delle
  24 contribuzioni orarie originarie, non eseguita nella ricognizione;
- sottoporre il protocollo locale a una decisione specifica, senza estendere
  l'approvazione dell'affitto o cambiare il contratto del benchmark nazionale.

Il piano non aggiunge medie comunali del caldo alla dashboard. UTCI non
sostituisce H03/H04: unità e allineamento della griglia NWIOI restano nei
[quesiti scientifici v0.4](v0_4_scientific_decisions.md).

## APE: contenuto minimo dell'estrazione

Il [servizio SIPEE per gli enti](https://servizi.regione.piemonte.it/catalogo/sistema-informativo-per-prestazione-energetica-degli-edifici-sipee)
prevede estrazioni con accesso riservato. Chiedere aggregati anonimi per i
27 codici ISTAT, classi A4–G e totale, con dizionario, ricevuta dei filtri,
data effettiva dello stock e periodo delle emissioni. Verificare attestati
annullati/sostituiti, validità e deduplicazione; il filtro E1 non attesta
da solo il sottoinsieme residenziale previsto. Tenere distinte vecchie e nuove
scale energetiche. La distribuzione degli APE non descrive tutto lo stock.

Se una fotografia storica 2025 non è disponibile, dichiarare il periodo
effettivamente ottenuto. Il dato comunale già presente per tutti gli usi
non soddisfa automaticamente il requisito H05.

## ISAC e prezzo/reddito: verificare la disponibilità

Per ISAC, gli originali di sezione già inventariati non contengono superfici
o aggregati ISAC. Il [dossier ISTAT](v0_5_istat_section_review.md) distingue
questa lacuna dalla disponibilità delle sezioni comunali. Non ricostruire
la distribuzione congiunta da conteggi separati né usare un percentile locale.

Per Mapadomo, la [pagina JRC](https://joint-research-centre.ec.europa.eu/scientific-activities/mapadomo_en)
descrive un rilascio progressivo a livello NUTS3. Errori o caricamenti incompleti
del catalogo non dimostrano assenza del dataset. Verificare l'export effettivo
prima di dichiararlo acquisito; un dato provinciale non diventa 27 stime comunali.

## Chiusura di ogni attività

Registrare originale, provenienza, versione, licenza/condizioni d'uso, periodo,
hash, mapping e QA. Distinguere acquisito, normalizzato, verificato e approvato;
assenza, soppressione, non applicabilità e zero verificato restano separati.
Conservare i dati privati e le evidenze locali fuori da Git.
Revisione scientifica e autorizzazione alla diffusione richiedono decisioni
distinte. Nessun blocco viene chiuso dalla sola disponibilità di un renderer.
