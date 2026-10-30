# Verbale di revisione umana — Accessibilità stradale ai DEA I/II

**Data della ricognizione:** 30 ottobre 2026  
**Stato del verbale:** sottoscrizione tecnica personale dichiarata da Tommaso Ferrucci (firma testuale `TomFer`) in data 30 ottobre 2026.  
**Decisione tecnica personale:** APPROVATO CON LIMITI DOCUMENTATI **per l'uso come proxy di screening territoriale Piemonte-only**; non è una certificazione di completezza della rete nazionale, né un'autorizzazione alla promozione canonica.  
**Stato per la promozione canonica v0.1:** SOSPESO in attesa delle verifiche residue elencate alla sezione 3. L'eventuale validazione istituzionale dell'Unione Montana è successiva e distinta.

## 1. Oggetto e criteri di lettura

Minimo TEP_TOT tra Comune origine e Comune sede di un DEA I/II presente nell’elenco piemontese 2025.

Il dataset ufficiale contiene 605 record nazionali; il Piemonte ne registra 44, di cui 30 DEA I/II in 23 Comuni. La correzione ministeriale (Ponderano al posto di Biella) non modifica i minimi dei 27 Comuni rispetto alla bozza precedente.

- **Origini:** 27 Comuni; **Comuni sede dei servizi candidati:** 23; **coppie stradali sottoposte a QA:** 621.
- **Vintage strade ISTAT:** geografia 2021, rete viaria 2020; **vintage servizio:** Ministero della Salute, rete emergenza ospedaliera 2025.
- **SHA-256 CSV osservazioni:** `917972ac6adedddf06a94db5b9f3499eda0b5a42244673ae7ac377309bd812e2`.
- **SHA-256 ZIP stradale dichiarato dal QA:** `e68fca8b6cf383d1bfdc4b51d1421b5ca51739b03f409c4eb9e7b3debd8e7987`.
- **SHA-256 confini ISTAT dichiarato dal QA:** `b011a590656c3a3ebc297fba80726a376aa843b6f164641cf6a4a990021a81d6`.
- **SHA-256 registry dei 27 Comuni:** `e7af9959a64200e2278f3c48c48a417aff8d09aea018622ed6b59a6c85505d27`.
- Originale XLSX 2025 SHA-256: `1598e1358872f8be49006066d83bc8687f2af6a21eabfad28f82d674e0bcae6e`; candidato CSV LF: `eedd2806ced98981311656def6e2c375dc7b7d0ce1cebf4a10f2722630963f95`.

## 2. Riscontri acquisiti e verificabili

*Questi sono risultati documentali o QA già disponibili; non attribuiscono automaticamente una firma umana.*

- [x] **Evidenza disponibile:** 30 strutture DEA I/II piemontesi, 23 Comuni, estratte dall’originale ministeriale 2025; 13 PS esclusi.
- [x] **Evidenza disponibile:** Confronto tecnico della bozza v01 con v03: 27 righe, 0 cambi di destinazione, 0 differenze in minuti e km.
- [x] **Evidenza disponibile:** Verificata l’esistenza dei 23 Comuni sede dei DEA nei confini ISTAT 2026 (riscontro di codici e denominazioni, non geolocalizzazione degli ingressi).

### Fonti da citare

- [Ministero della Salute — elenco 2025](https://www.salute.gov.it/new/it/banche-dati/elenco-strutture-della-rete-dellemergenza-ospedaliera/)
- [ISTAT — matrice delle distanze](https://www.istat.it/notizia/matrici-di-contiguita-distanza-e-pendolarismo/)
- [Ministero della Salute — condizioni di riuso](https://www.salute.gov.it/new/it/altro/note-legali-2/)
- [ISTAT — condizioni di riuso](https://www.istat.it/note-legali/)

## 3. Verifiche obbligatorie ancora da attestare personalmente

- [ ] Ricalcolare o motivare quantitativamente le alternative DEA fuori Piemonte, a partire da Aosta e dalla Lombardia.
- [ ] Riscontrare tre coppie OR_PROCOM/DEST_PROCOM e i valori TEP_TOT/KM_TOT nell’originale Piemonte.zip.
- [ ] Convalidare esplicitamente la compatibilità amministrativa 2021/2026 sul lato matrice e l’assenza di destinazioni omesse nel perimetro scelto.
- [ ] Confermare che le condizioni generali di riuso delle fonti si applichino senza eccezioni ai singoli archivi.
- [ ] Collegare evidenze persistenti alle verifiche svolte (file, data, riga CSV, URL consultato).
- [x] Espressa decisione personale di approvazione del **solo impiego metodologico del proxy** con limiti documentati; data e firma testuale fornite direttamente dal revisore (non firma digitale qualificata).
- [ ] **Solo per PR che promuovono dati protetti:** review GitHub indipendente di altro account sull'ultimo commit, richiesta dalla protezione attuale della repository. Questo controllo non è necessario per archiviare il presente verbale solo documentale in una PR che modifica esclusivamente `docs/`. L'approvazione istituzionale dell'Unione Montana potrà seguire in una fase successiva.

## 4. Tre percorsi campione — valori attesi dalla bozza

| Comune origine | Codice origine | Comune destinazione | Codice destinazione | TEP_TOT atteso (min) | KM_TOT atteso (km) | Riscontro sul CSV ISTAT originale |
| --- | --- | --- | --- | ---: | ---: | --- |
| Ceresole Reale | `001073` | Ciriè | `001086` | 71.00 | 64.10 | **DA VERIFICARE**: ZIP/membro/riga |
| Ronco Canavese | `001224` | Ciriè | `001086` | 55.00 | 45.90 | **DA VERIFICARE**: ZIP/membro/riga |
| Castellamonte | `001066` | Ivrea | `001125` | 24.00 | 17.90 | **DA VERIFICARE**: ZIP/membro/riga |

Il controllo tecnico del software NON sostituisce il riscontro manuale di tre righe sull’archivio `Piemonte.zip`.

## 5. Limitazioni e interpretazione scientifica

Non è una stima di accesso casa–ospedale, tempo ambulanza, percorrenza reale 2026, traffico o ingresso del DEA. La selezione è limitata al Piemonte. Un DEA fuori regione potrebbe risultare più vicino.

L’indicatore costituisce un **elemento di screening territoriale EPAH**, non una misura diretta della povertà energetica né dell’accessibilità effettiva delle persone vulnerabili.

## 6. Decisione tecnica personale e sottoscrizione

**Oggetto esatto dell'approvazione:** impiego del tempo stradale minimo ISTAT verso il **Comune sede di un DEA I/II presente nell'elenco piemontese 2025** come proxy comparativo preliminare per i 27 Comuni della Green Community. La decisione attesta l'accettazione *metodologica* dei limiti dichiarati e dei risultati tecnici disponibili; **non attesta** che siano state completate le verifiche ancora contrassegnate `[ ]`.

> Dichiaro, in qualità di esperto, di approvare con limiti documentati l'utilizzo **tecnico e preliminare** del proxy di accessibilità DEA Piemonte-only per lo screening territoriale EPAH. Sono consapevole che non misura i tempi di ambulanza, l'accesso casa-ospedale, il traffico attuale, né necessariamente il DEA più vicino sull'intera rete nazionale. Prendo atto che restano da completare i riscontri sui percorsi campione nell'originale ISTAT, la verifica dei DEA fuori regione, la compatibilità amministrativa della matrice stradale e le condizioni specifiche di riuso. La presente sottoscrizione non comporta la promozione automatica delle 27 osservazioni a `Dato validato` né costituisce approvazione istituzionale dell'Unione Montana.

- **Decisione di perimetro dichiarata dal revisore:** `piemonte_dea_proxy_approved_with_limits`, **limitatamente all'impiego metodologico preliminare**.
- **Decisione:** [x] approvato con limiti documentati (uso metodologico preliminare)  [ ] non approvato  [ ] rinviato
- **Revisore (nome e cognome):** Tommaso Ferrucci
- **Ruolo/organizzazione:** Esperto (organizzazione non indicata)
- **Data di sottoscrizione:** 30/10/2026
- **Luogo di sottoscrizione:** non indicato
- **Firma personale dichiarata:** `TomFer` (firma testuale fornita dal revisore; non verificata come firma elettronica qualificata)
- **Evidenza pubblicata (URL HTTPS del commit/PR):** il permalink al commit GitHub che contiene il presente file è l'evidenza verificabile della versione pubblicata; non è una prova d'identità o firma digitale qualificata. Vedere la PR di archiviazione del verbale e il commit immutabile.
- **Secondo revisore:** non richiesto per il deposito di questo verbale documentale. La verifica **indipendente di una futura PR che modifica dati protetti** resta richiesta dal controllo CI attuale; **approvazione istituzionale dell'Unione Montana rinviata** a una fase successiva.

### Distinzione tra firma tecnica, approvazione dei dati e approvazione istituzionale

1. **Firmato per lo screening preliminare:** la presente scelta metodologica esplicita e i suoi limiti.
2. **Non ancora attestato:** i singoli controlli della sezione 3, con prove e firme sulle verifiche residue. `dea_approval.pending.json` resta pertanto `pending`, con i flag non verificati a `false`.
3. **Non ancora autorizzato:** esecuzione del finalizzatore per contrassegnare le 27 righe DEA come `Dato validato`, fino al completamento delle verifiche e al rispetto del gate GitHub.
4. **Successivamente:** eventuale approvazione istituzionale dell'Unione Montana, distinta dalla valutazione tecnica dell'esperto.

**Integrità:** questa versione del testo è attribuita tramite il commit Git; la stringa `TomFer` è una sottoscrizione testuale inserita su indicazione del revisore, non autentica da sola la sua identità.