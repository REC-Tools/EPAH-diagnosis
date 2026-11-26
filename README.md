# EPAH Diagnosis — Sinergie in Canavese

**Versione software stabile: v0.5.0** · **Perimetro: 27 Comuni** · **Output territoriali: revisione tecnica, non pubblicazione istituzionale**

Toolkit Python open-data per una **diagnosi territoriale descrittiva della vulnerabilità alla povertà energetica**. La v0.5.0 aggiunge una consegna selezionata con affitto 2021 e caldo UTCI 2025 sulle celle originali, conservando il percorso di costruzione, il portale e gli strumenti di revisione delle versioni precedenti. La release distribuisce solo software; il pacchetto territoriale resta parziale e locale. Il toolkit v0.2 produce rapporto PDF, 27 schede comunali, confronti fra dimensioni, dashboard offline e pacchetto di revisione. Usa il bundle pilota v0.1 come **input verificato**, senza promuovere automaticamente le osservazioni nella matrice canonica.

> **Limite essenziale:** i nove indicatori/descrittori della base (otto numerici e classificazione SNAI) non misurano direttamente la povertà energetica delle famiglie. Il software non produce graduatorie di rischio, un indice EPAH certificato o autorizzazioni alla pubblicazione.

## Leggere la repo e usare il percorso v0.4

Per capire lo strumento partire da [architettura e responsabilità](docs/v0_4_architecture.md), poi dalla [guida sviluppatore](docs/v0_4_developer_guide.md). Il percorso è: originali e QA → snapshot verificato → atlante → fascicolo → portale → audit → revisione umana. I dati canonici e le anteprime dei candidati mantengono ruoli e approvazioni distinti.

Il comando `epah outputs` coordina i builder v0.4 esistenti, conserva denominatori e ricevute e si ferma al primo errore:

```powershell
uv run --locked epah outputs plan --bundle work/input/pilot --out-dir work/review-run-01
```

`plan` non scrive file. `run` costruisce e verifica il pacchetto; una revisione con candidati assenti richiede esplicitamente `--allow-incomplete`. La presenza delle 16 serie non autorizza la diffusione. [Esempi e stati delle esecuzioni](docs/v0_4_developer_guide.md) · [Piano di completamento](docs/v0_4_delivery_plan.md) · [Decisioni scientifiche aperte](docs/v0_4_scientific_decisions.md).

## Avvio rapido

**Consegna tecnica v0.5 selezionata:** [perimetro, caldo sulle celle originali e percorso SIPEE](docs/v0_4_v05_closeout_20261126.md).
Il profilo mantiene affitto 2021 e caldo 2025, con gli altri candidati rinviati
esplicitamente; il catalogo completo resta disponibile.

**Pacchetto reale v0.4 parziale:** [chiusura tecnica e riproduzione](docs/v0_4_technical_closeout.md).
Per consultare insieme le fonti climatiche e abitative v0.5 e confrontare due
importazioni: [portale unico offline](docs/v0_5_source_review_hub.md), con prova
sintetica `epah methodology source-portal --example --out-dir work/source-demo-01`.

Gli input verificati si possono dichiarare una volta in un file locale:

```powershell
uv run --locked epah outputs run --inputs-file work/review-inputs.json --out-dir work/v04-review-01 --allow-incomplete
```

Il portale espone disponibilità e periodi per indicatore e un modello di revisione
da compilare in una copia esterna. [Preparazione metodologica v0.5](docs/v0_5_methodology.md):
18 proposte da fonti EPAH, senza promozione automatica a osservazioni comunali.

**Vuoi provare lo strumento senza dati territoriali?** Segui l'
[esempio sintetico](docs/v0_4_synthetic_example.md): il comando `epah examples synthetic` genera e verifica
atlante, CSV, PDF e portale per 27 Comuni fittizi, senza originali o credenziali.

```powershell
uv sync --python 3.11 --locked --no-dev
uv run --locked --no-dev epah examples synthetic --out-dir work/synthetic-example-01
```

Aprire `work/synthetic-example-01/hub/index.html`. Usare una destinazione nuova
per ogni esecuzione; pytest non è richiesto per la dimostrazione.

Prerequisiti: Python **3.11+**, [uv](https://docs.astral.sh/uv/) e gli **input originali/QA locali** necessari per costruire o riutilizzare il bundle pilota. Dal repository:

```powershell
uv sync --python 3.11 --locked --group dev
uv run --locked pytest -q
uv run --locked epah status
uv run --locked epah sources check
uv run --locked epah data validate
```

La suite automatica verifica il software e le fixture; **non sostituisce** la revisione delle fonti territoriali reali.

### Prodotti v0.2 (rapporto, schede, dashboard)

Se il bundle `outputs/v0.1.0-pilot` è già disponibile e verificato, creare una **nuova cartella** per ogni esecuzione (PowerShell):

```powershell
$bundle = "outputs/v0.1.0-pilot"
$run = "outputs/v0.2-technical-$(Get-Date -Format yyyyMMdd-HHmmss)"
uv run --locked epah report v0.2 --bundle $bundle --out-dir "$run/report"
uv run --locked epah sheets v0.2 --bundle $bundle --out-dir "$run/sheets"
uv run --locked epah analysis v0.2 --bundle $bundle --out-dir "$run/analysis"
uv run --locked epah dashboard v0.2 --bundle $bundle --analysis-dir "$run/analysis" --out-dir "$run/dashboard"
uv run --locked epah review-pack v0.2 --bundle $bundle --report-dir "$run/report" --sheets-dir "$run/sheets" --analysis-dir "$run/analysis" --dashboard-dir "$run/dashboard" --out-dir "$run/review"
uv run --locked epah audit v0.2 --dir "$run/review"
```

Interrompere la sequenza al primo errore. Nessuno di questi comandi autorizza la distribuzione dei risultati; il pacchetto è marcato **`technical_draft_do_not_publish`**. Se manca il bundle, consultare la [procedura di preparazione del pilota](docs/v0_1_owner_accepted_release.md). I download originali e i prodotti locali non sono distribuiti dalla release GitHub.

### Atlante v0.3 dei candidati

Con il bundle pilota e le anteprime dei candidati prodotte localmente (vedi [guida all'atlante](docs/v0_3_visual_atlas.md)):

```powershell
$run = "outputs/v0.3-atlas-$(Get-Date -Format yyyyMMdd-HHmmss)"
uv run --locked python scripts/build_v0_3_visual_atlas.py --bundle outputs/v0.1.0-pilot --out-dir $run
```

Senza anteprime l'atlante mostra i 9 indicatori del pilota e marca gli altri come `DATI ASSENTI`.

## Componenti della v0.2

| Componente | Cosa fornisce |
| --- | --- |
| **Rapporto** | PDF tecnico, mappe selezionate e statistiche con provenienza. |
| **27 schede comunali** | Indicatori separati, anni, confronti e cautele interpretative. |
| **Analisi multidimensionale** | 28 co-occorrenze descrittive, **senza** indice composito. |
| **Dashboard HTML offline** | Esplorazione dei Comuni, delle dimensioni e degli incroci. |
| **Review-pack e audit** | Bundle per revisione interna, manifest SHA-256 e verifiche d'integrità. |

La v0.2.0 è **stabile come software**, non come diagnosi approvata dall'Unione Montana o da EPAH. I dati **CIT/Pont Canavese** rimangono in quarantena e fuori dai prodotti principali. [Note di release e limiti](docs/releases/v0.2.0.md).

## Stato dei dati e sviluppi successivi

- **v0.1 pilota:** base storica 27 × 9, accettazione tecnica distinta dal gate canonico; il bundle deve essere generato localmente.
- **v0.2 stabile:** strumenti di analisi e presentazione basati sul pilota, senza nuova validazione scientifica automatica.
- **v0.3.0 (release precedente):** inventario EPAH di 56 indicatori e 35 fonti e pipeline per sette candidati. H47 (0–11 anni), H50 (istruzione) e H46 (disoccupazione) hanno anteprime reali 27/27 verificate da audit indipendenti; H03 (HDD), H04 (CDD), H05 (APE residenziali F/G) e ADD-HOUSING-01 (abitazioni non occupate da residenti) avevano solo la pipeline nella release storica. Per lo stato corrente, inclusi gli originali climatici disponibili e la revisione abitazioni, vedere la [chiusura v0.4](docs/v0_4_technical_closeout.md). Nessun candidato entra nel catalogo canonico, che resta di nove indicatori. [Note di release v0.3.0](docs/releases/v0.3.0.md) · [Nomenclatura armonizzata EPAH e contratti di acquisizione](docs/v0_3_epah_harmonized_three_candidates.md) · [Scope della ricerca](docs/v0_3_scientific_scope.md).

## Come orientarsi nel repository

| Cartella | Contenuto | Da guardare per primo |
| --- | --- | --- |
| [`docs/`](docs/index.md) | Guide, metodologia, candidati, release e storico | [Indice della documentazione](docs/index.md) |
| [`scripts/`](scripts/README.md) | Comandi Python, raggruppati per versione e funzione | [Guida agli script](scripts/README.md) |
| `src/epah_diagnosis/` | Libreria e CLI `epah` (report, schede, dashboard, audit v0.2) | `workflow_cli.py` |
| `config/` | Catalogo canonico dei 9 indicatori, fonti, configurazioni release | `indicators.json` |
| `data/` | Registro dei 27 Comuni, serie canoniche validate, riferimenti e inventario EPAH v0.3 | `municipalities.csv`, `reference/epah_v0_3_*.csv` |
| `tests/` | Test automatici su dati sintetici (nessun dato territoriale reale) | — |
| `.github/workflows/` | CI, controlli dei dati protetti, pubblicazione manuale delle release | `ci.yml` |

`outputs/`, `data/downloads/`, `artifacts/` e `work/` sono **locali** e ignorati da Git: export originali ISTAT/ARPA, anteprime e atlanti si generano sulla propria macchina e non compaiono su GitHub.

### Percorso per una revisione (15 minuti)

1. [Note di release v0.5.0](docs/releases/v0.5.0.md): funzioni, installazione e limiti della release corrente.
   [Contribuire](CONTRIBUTING.md): branch, commit, PR e release separate.
2. [Registro scientifico EPAH v0.3](docs/v0_3_scientific_scope.md): perché i candidati sono proxy e non misure di povertà energetica.
3. [Atlante esplorativo v0.3](docs/v0_3_visual_atlas.md): come si generano mappe e grafici.
4. Un candidato completo, dalla fonte all'audit: [H46 disoccupazione](docs/v0_3_h46_official_normalization_and_independent_audit.md) oppure [H50 istruzione](docs/v0_3_h50_education_candidate.md).
5. [Catalogo dei 9 indicatori canonici](docs/indicator_catalog.md) e [governance](docs/governance.md): cosa resta da approvare e chi decide.

## Documentazione e governance

Partire dall'[**indice della documentazione**](docs/index.md): distingue guide correnti, indicatori, procedure canoniche, prototipi e archivio storico. Per l'uso quotidiano: [guida operativa](docs/operational_guide.md), [CLI](docs/unified_cli.md), [riproducibilità](docs/reproducible_build.md). Per la pubblicazione servono QA delle fonti, revisione metodologica e approvazione istituzionale **separate** dai test CI. [Protezione delle modifiche ai dati](docs/data_change_protection.md).

Le mappe GeoJSON usano CRS84/WGS84 e il rendering cartografico usa EPSG:32632. Non cancellare o versionare involontariamente gli originali locali; non eseguire pulizie distruttive dei file `data/` o `outputs/`. [Licenza](LICENSE).
