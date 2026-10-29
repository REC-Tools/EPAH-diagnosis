# Governance e revisione delle modifiche

## Principio
Ogni cambiamento passa da una pull request con ambito, evidenza e verifiche dichiarate. La revisione umana è necessaria per interpretazioni e pubblicazione dei risultati. Questo documento definisce una **procedura di lavoro**, non implica che branch protection o approvazioni obbligatorie siano già configurate in GitHub.

## Percorsi di revisione
| Tipo | Revisione minima richiesta | Verifiche |
| --- | --- | --- |
| Documentazione/editoriale | coerenza con framework e stato effettivo | link, assenza di affermazioni non verificate |
| Fonti/dati | origine, anno, licenza, copertura, chiavi e assenze | QA, provenance, impatto su risultati pregressi |
| Indicatore/metodo | definizione, ruolo, denominatore, direzione, soglie, limiti | revisione metodologica umana prima del merge |
| Pipeline/codice | riproducibilità e regressioni | test pertinenti e compatibilità con matrice |
| Mappe/report pubblici | periodi, interpretazione, provenienza e autorizzazione | controllo editoriale e metodologico |

## Definition of Done
Una modifica è pronta per il merge quando:
1. obiettivo e portata sono leggibili nella PR;
2. rischio e file modificati sono circoscritti;
3. fonti, metodi e limiti sono documentati quando pertinenti;
4. i test pertinenti sono stati eseguiti oppure è esplicitato perché non si applicano;
5. nessuno stato `Dato validato` è attribuito senza evidenza QA;
6. dati mancanti, anni differenti e confronti non equivalenti restano visibili;
7. nessuna pipeline elimina o sovrascrive risultati senza piano di migrazione;
8. per cambi metodologici è registrata una decisione umana;
9. ogni output condiviso ha percorso di provenance e indicazione del suo stato editoriale;
10. non ci sono dati personali né segreti nel diff.

Non è necessario imporre tutti i campi a una correzione ortografica: il template PR prevede risposte `non applicabile` motivate.

## Ruoli e decisioni
- **Autore:** prepara modifica, fonte e verifiche, senza autoattribuire approvazione metodologica.
- **Revisore tecnico:** valuta compatibilità, qualità, riproducibilità e controlli.
- **Revisore metodologico (esperto EPAH/progetto):** valuta coerenza del significato diagnostico; autorizza modifiche di formule, pesi, soglie e categorie.
- **Responsabile della diffusione (team beneficiario):** verifica che le mappe e i report siano condivisibili e contestualizzati.

In un team piccolo la stessa persona può coprire più ruoli, ma le decisioni devono restare documentate. Nessun vincolo di approvazione automatica è attivato da questa PR.

## Conflitti e compatibilità
Se una modifica influenza gli ID, la matrice o la struttura degli output, separare migrazione applicativa e modifica metodologica. Prima di fondere il branch descrivere la transizione, il ripristino dei dati e gli effetti sui prodotti precedenti. Non rigenerare distruttivamente `data/verification_matrix.csv`.

## GitHub
- `.github/pull_request_template.md`: checklist per ogni PR.
- `.github/ISSUE_TEMPLATE/methodology.yml`: discussione sulla metodologia.
- `.github/ISSUE_TEMPLATE/data_quality.yml`: incidenti di fonte e QA.
- `docs/indicator_completion_criteria.md`: definizione di validazione.
- `docs/data_contract.md` e `docs/provenance.md`: contratti di qualità e tracciabilità.

## Protezione automatica degli artefatti canonici

Il [controllo PR sui dati](data_change_protection.md) rileva modifiche, cancellazioni e regressioni di stato rispetto al commit base, e richiede dichiarazioni esplicite e una review GitHub effettiva delle PR dati prima del merge. Questo è un controllo **tecnico**: non attribuisce mai una validazione scientifica o metodologica automatica. La protezione effettiva del branch richiede che un amministratore imposti required checks e review obbligatorie su GitHub. I workflow programmati di aggiornamento non devono più effettuare push diretti su `main`: aprono proposte draft per revisione.

## Possibili controlli successivi
La PR E potrà introdurre verifiche automatiche non distruttive del catalogo e delle referenze. Branch protection, CODEOWNERS e policy di approvazione obbligatoria richiedono una scelta esplicita del team, non vengono imposti qui.
