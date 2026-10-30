# QA delle bozze di accessibilita v0.1 - 30 ottobre 2026

## Ambito e stato

Controllo di integrita su quality.zip fornito per la Green Community Sinergie in Canavese: 27 Comuni, tre indicatori. **Solo controllo tecnico:** nessun valore e approvato metodologicamente da questo dossier. Non modificare la matrice con i risultati delle bozze.

| Indicatore | Comuni | Destinazioni candidate | Coppie ISTAT | SHA-256 delle 27 righe CSV |
| --- | ---: | ---: | ---: | --- |
| dea_accessibility | 27 | 23 | 621 | 7de576889ce5bf859e981e0ae905a6a54e83ec3327ad10fc34164ba2252c2df3 |
| rail_accessibility | 27 | 9 | 243 | f7677d2d0f5b91adc2e03169b0d31dc6c3d10142068cc35f70ca88f3c3c77db6 |
| upper_secondary_accessibility | 27 | 51 | 1377 | 94913640cc10ea1db138839f918d9d22ab259b754db5c52e70f7505aefef2ccc |

Le prove di integrita includono checksum di dati, summary e liste di destinazione, copertura dei 27 codici ISTAT e allineamento degli hash degli input tra intake e QA. Nessuna prova dimostra l'operativita dei servizi, la completezza geografica o la liceita del riuso.

Originali dichiarati negli audit di intake: Piemonte.zip SHA-256 e68fca8b6cf383d1bfdc4b51d1421b5ca51739b03f409c4eb9e7b3debd8e7987; Limiti01012026_g.zip SHA-256 b011a590656c3a3ebc297fba80726a376aa843b6f164641cf6a4a990021a81d6. Gli originali stradali non sono contenuti nel solo quality.zip; mantenere i byte locali sotto data/downloads/.

## Riscontro incrociato scuola-ferrovia

Per 27/27 Comuni coincidono il codice del Comune di destinazione, i minuti TEP_TOT e i chilometri KM_TOT. In 26 casi si raggiunge Rivarolo Canavese (001217), in un caso Cirie (001086). I due indicatori descrivono servizi diversi ma condividono le medesime distanze minime in questo snapshot: non si possono trattare come conferme indipendenti. Nessun indice composito viene prodotto.

## Verifiche esterne ancora necessarie

1. **DEA:** confrontare le 27 strutture candidate / 23 Comuni della lista locale con l'elenco nazionale delle strutture attive al 31/12/2025 pubblicato dal Ministero della Salute (https://www.salute.gov.it/new/it/banche-dati/elenco-strutture-della-rete-dellemergenza-ospedaliera/). Verificare livelli DEA I/II e ospedali fuori Piemonte.
2. **Scuola:** i due CSV MIM sono 2024/25, percio i 51 Comuni identificati rappresentano una proxy storica e non offerta corrente 2026/27. Confrontare con anagrafe scuole aggiornata; la distribuzione degli indirizzi 2024/25 e disponibile dal catalogo https://dati.istruzione.it/opendata/opendata/catalog/ALUSECGRADOINDSTA .
3. **Ferrovia:** confrontare le nove destinazioni con RFI/SFM, servizio effettivo, sostituzioni e confini regionali. SFM segnala Rivarolo-Pont Canavese come tratto in autobus (https://www.sfmtorino.it/le-linee-sfm/sfm1-pont-rivarolo-chieri/).
4. **Tutti e tre:** verificare almeno tre coppie origin-destination sull'originale ISTAT, provenienza/licenze, corrispondenza codici 2021/2026, eventuali destinazioni fuori regione.
5. **Approvazione:** registrare revisore reale, data, evidenza persistente e decisione metodologica; nessuna approvazione viene creata dal codice.

## Riprodurre il controllo senza modificare la matrice

Da PowerShell nella root della repository:

    python scripts/audit_accessibility_candidates.py --quality-dir outputs/quality --strict

Oppure con uno ZIP quality.zip:

    python scripts/audit_accessibility_candidates.py --quality-zip quality.zip --strict

Output: outputs/quality/accessibility_candidate_review/review_packet.json e review_packet.md (non versionati). Il codice verifica la coerenza degli audit, non autentica persone o fonti.

**Decisione di rilascio: NO.** I 27+27+27 risultati restano bozze tecniche, con validated_for_release=false, e la v0.1 mantiene i gate 243/243 e nove review documentate.
