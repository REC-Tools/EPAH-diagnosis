# Recupero evidenze delle 81 osservazioni prioritarie (29 ottobre 2026)

**Stato: archivio tecnico storico, revisione umana ancora necessaria.**
Il materiale qui recuperato **non** costituisce dati pubblicabili, un’approvazione metodologica, né una modifica alla matrice.

## Perché esiste questo archivio

La [PR #79](https://github.com/REC-Tools/EPAH-diagnosis/pull/79) aveva introdotto 81 osservazioni con stato `Dato validato` (27 gradi-giorno normativi, 27 altitudini medie ISTAT, 27 classi SNAI) e salvato file CSV, hash SHA-256 e un dossier. Il testo della PR indicava che la revisione GitHub sarebbe stata necessaria prima del merge, ma **non risultano review o commenti registrati sulla #79**. La successiva [PR #80](https://github.com/REC-Tools/EPAH-diagnosis/pull/80), destinata alla cartografia, ha eliminato anche quei file e annullato la promozione. Questa modifica non era dichiarata nell'ambito cartografico.

È corretto **non** ripristinare autonomamente lo stato di validazione, ma eliminare le copie tracciate rende più difficile verificare gli originali. Questa PR recupera **i byte esatti** dei quattro CSV originali e del JSON storico dal commit merge della #79 (`077d88f7227e2befb766c5417023b5959086062f`) in una posizione di archivio, non nel percorso operativo `data/indicators/`.

## Contenuto recuperato

Directory: `data/reference/priority_source_archive_20261029/`.

| File | Contenuto | Anno | Righe comunali |
| --- | --- | --- | --- |
| `mean_altitude_2021.csv` | quota media territoriale; **non** quota del municipio | 2021 | 27 |
| `mean_altitude_summary_2021.csv` | media/mediana/min/max descrittivi | 2021 | riepilogo |
| `snai_classification_2020.csv` | classe istituzionale A–F, non rischio numerico | 2020 | 27 |
| `snai_classification_summary_2020.csv` | distribuzione classi | 2020 | riepilogo |
| `priority_81_source_evidence_original.json` | riferimento storico delle tre fonti e relativi hash | versioni 2016/2021/2020 | metadata |

I file sono archiviati **senza modificare i byte**. Il JSON originale cita **135 righe validate, 81 promosse e una PR draft**: quelle dichiarazioni si riferiscono al contesto della #79 e **non descrivono il presente stato del repository**. Non usarlo come manifest di approvazione corrente.

Il confronto storico indicava 81/81 valori coincidenti. I file **originali binari** (PDF ministeriale e due XLSX) **non sono nel Git**: i loro hash nel JSON storico sono registrazioni, **non una verifica ripetuta in questa PR**.

## Stato corrente e protezioni

Nello snapshot di `main` prima di questa modifica: **54/243** `Dato validato`, **27/243** `Dato acquisito` e **162/243** `Da verificare`. In particolare altitudine e SNAI risultano da verificare e i gradi-giorno sono acquisiti, non approvati. Il file `config/release_reviews_v0_1.json` rimane invariato e la v0.1 non è pronta.

Il test `tests/test_priority_source_archive.py` verifica offline:
- hash SHA-256 dei quattro CSV archivio rispetto a costanti storiche e manifest;
- corrispondenza esatta dei 27 nomi e codici ISTAT rispetto al registro canonico;
- unicità, anno e unità corretta delle due serie;
- stato di review ancora pendente nel dossier corrente, senza promozioni;
- riconoscibilità esplicita dei metadati storici.

I controlli sui CSV **non** certificano gli XLSX/PDF originali: per una revisione scientifica è necessario procurarsi i file istituzionali, confrontarli agli SHA-256 del manifest, controllare versioni e geografia e registrare un **review GitHub effettivo**. Solo dopo usare i finalizzatori protetti su un nuovo branch e sottoporre il diff della matrice a ulteriore controllo.

## Sequenza di ri-validazione consigliata

1. Recuperare originali normativi ISTAT/SNAI e calcolarne gli hash; confrontare con `priority_81_source_evidence_original.json`.
2. Eseguire `python scripts/audit_priority_sources.py --annex-file ... --altitude-xlsx ... --snai-xlsx ... --strict --out-dir outputs/quality/priority_audit_recheck`.
3. Confermare la comparabilità 2020/2021 rispetto al registro comunale corrente e il significato di GG, quota media e classe SNAI.
4. Registrare il vero revisore, la data, il risultato e un riferimento persistente in GitHub, distinguendo **validazione del dato** e **approvazione metodologica**.
5. Solo con evidenza autentica e gate dei finalizzatori superati, proporre una PR di promozione, limitata ai record interessati e con test di regressione.

Questo recupero non modifica lo stato di **alcuna osservazione** e non equivale ad una ripubblicazione della PR #79.
