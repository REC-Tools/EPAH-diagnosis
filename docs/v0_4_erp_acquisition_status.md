# ERP: acquisizione tramite Unione Montana

Aggiornamento del 25 novembre 2026 per il tecnico incaricato e il referente
dell'Unione Montana. Ambito: V05-21 (alloggi ERP ogni 100 famiglie) e V05-22
(quota ERP sfitto per manutenzione), sui 27 Comuni del registro di progetto.
Stato: `technical_draft_do_not_publish`.

## Decisione operativa e disponibilità

Il referente del progetto ha dichiarato in chat che chiederà all'Unione Montana
di far richiesta dei dati. Si registra un passaggio da avviare, non un invio
avvenuto, una risposta dell'Unione o un dataset acquisito.

Le sei risposte pubbliche ATC già conservate non costituiscono uno stock
completo datato dei 27 Comuni. Il totale ERP e gli sfitti per manutenzione
rimangono da acquisire e verificare. Nessun valore mancante diventa zero;
nessuna approvazione scientifica o autorizzazione alla pubblicazione deriva
da questa nota.

## Alternative pubbliche: verifica circoscritta

La consultazione del 25 novembre 2026 ha verificato:

- [ERPS regionale](https://servizi.regione.piemonte.it/catalogo/rilevazione-assegnazioni-disagio-abitativo-erps):
  raccolta annuale comunale, con accesso riservato ai funzionari abilitati.
- [Cruscotto Welfare Abitativo](https://servizi.regione.piemonte.it/catalogo/cruscotto-welfare-abitativo):
  accesso riservato ai referenti regionali; non è un export pubblico alternativo.
- [Patrimonio di edilizia sociale 2019–2024](https://www.regione.piemonte.it/web/media/51438/download):
  totali regionali e provinciali; non fornisce stock e cause dello sfitto per
  ciascuno dei 27 Comuni nel 2025.
- [Quadro regionale al 31 dicembre 2024](https://www.regione.piemonte.it/web/media/52917/download):
  statistiche aggregate di copertura e disagio; non colma gli input comunali
  richiesti per i due indicatori.

Non è stata individuata in questi controlli una fonte pubblica sufficiente
a sostituire la richiesta. Non si attesta l'assenza di ogni possibile fonte
pubblica. Gli aggregati provinciali non vengono ripartiti fra i Comuni e
non si tenta di superare l'autenticazione dei servizi riservati.

## Prossimo passo e requisiti di ingresso

1. Chiedere tramite Unione Montana gli estratti o le schede ERPS 2025 già
   trasmessi, con codice ISTAT, data effettiva, dizionario e perimetro degli enti.
2. Se le schede non contengono le cause dello sfitto, richiedere ad ATC/Comuni
   aggregati distinti per manutenzione, altre cause e causa ignota, riferiti
   allo stesso stock e alla stessa data. Verificare le sovrapposizioni.
3. Conservare originali ricevuti, provenienza, condizioni d'uso e hash;
   documentare il mapping sul modello ERP v2 già disponibile.
4. Usare l'importatore esistente per preparare la revisione, distinguendo
   dato fornito, zero dichiarato, territorio non gestito, indisponibilità e
   mancata risposta. Verificare proprietà/gestione per evitare doppi conteggi.
5. Prima di V05-21 acquisire un denominatore di famiglie coerente per territorio
   e periodo. Prima di V05-22 verificare cause e totale ERP dello stesso perimetro.

La [richiesta e l'importazione ERP](v0_5_erp_request_packet.md) e il
[dossier delle fonti abitative](v0_5_housing_source_feasibility.md) definiscono
il percorso esistente. Non occorre costruire un secondo importatore.
Eventuali risposte parziali restano consultabili come fonti, senza essere
presentate come indicatori completi. I dati privati ricevuti non vanno in Git.

Questa modifica documenta disponibilità, dipendenze e responsabilità del
prossimo passo; non modifica dati, formule, cataloghi o stati canonici.
