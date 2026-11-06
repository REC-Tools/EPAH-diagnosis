# EPAH Diagnosis — Sinergie in Canavese

**Versione software stabile: v0.2.0** · **Perimetro: 27 Comuni** · **Output territoriali: revisione tecnica, non pubblicazione istituzionale**

Toolkit Python open-data per una **diagnosi territoriale descrittiva della vulnerabilità alla povertà energetica**. La v0.2 produce rapporto PDF, 27 schede comunali, confronti fra dimensioni, dashboard offline e pacchetto di revisione. Usa il bundle pilota v0.1 come **input verificato**, senza promuovere automaticamente le osservazioni nella matrice canonica.

> **Limite essenziale:** i nove indicatori/descrittori della base (otto numerici e classificazione SNAI) non misurano direttamente la povertà energetica delle famiglie. Il software non produce graduatorie di rischio, un indice EPAH certificato o autorizzazioni alla pubblicazione.

## Avvio rapido — software v0.2

Prerequisiti: Python **3.11+**, [uv](https://docs.astral.sh/uv/) e gli **input originali/QA locali** necessari per costruire o riutilizzare il bundle pilota. Dal repository:

```powershell
uv sync --python 3.11 --locked --group dev
uv run --locked pytest -q
uv run --locked epah status
uv run --locked epah sources check
uv run --locked epah data validate
```

La suite automatica verifica il software e le fixture; **non sostituisce** la revisione delle fonti territoriali reali.

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
- **v0.3 sperimentale:** inventario EPAH di 56 indicatori e 35 fonti; candidati H47 (0–11 anni), H50 (istruzione), H46 (disoccupazione), H03 (HDD), e nuovi candidati H05 (APE residenziali F/G), ADD-HOUSING-01 (abitazioni non occupate da residenti) e H04 (CDD). Nessun candidato entra automaticamente nel catalogo canonico. [Nomenclatura armonizzata EPAH e contratti di acquisizione](docs/v0_3_epah_harmonized_three_candidates.md) · [Scope della ricerca](docs/v0_3_scientific_scope.md).

## Documentazione e governance

Partire dall'[**indice della documentazione**](docs/index.md): distingue guide correnti, indicatori, procedure canoniche, prototipi e archivio storico. Per l'uso quotidiano: [guida operativa](docs/operational_guide.md), [CLI](docs/unified_cli.md), [riproducibilità](docs/reproducible_build.md). Per la pubblicazione servono QA delle fonti, revisione metodologica e approvazione istituzionale **separate** dai test CI. [Protezione delle modifiche ai dati](docs/data_change_protection.md).

Le mappe GeoJSON usano CRS84/WGS84 e il rendering cartografico usa EPSG:32632. Non cancellare o versionare involontariamente gli originali locali; non eseguire pulizie distruttive dei file `data/` o `outputs/`. [Licenza](LICENSE).
