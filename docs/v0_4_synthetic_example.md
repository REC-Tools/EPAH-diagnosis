# Esempio v0.4 senza originali territoriali

Destinatari: nuovi contributori che vogliono vedere il percorso dei prodotti
prima di acquisire fonti reali. L'esempio usa 27 Comuni fittizi, valori sintetici
e i renderer di produzione per HTML, CSV, grafici, PDF, schede e portale.
Gli slot non acquisiti restano espliciti. Nessuna osservazione è territoriale.

## Preparazione

Da un checkout dei sorgenti, installare Python 3.11+ e `uv`, poi:

```powershell
uv sync --python 3.11 --locked --group dev
```

Non servono download ISTAT/ARPA, credenziali o i file ignorati da Git.
La generazione dei prodotti avviene con una fixture sintetica dei test: la
fixture sostituisce l'ingestione degli originali e usa i normali renderer e
audit. Non crea un bundle pilota verificato dalle fonti.

## Generare e verificare il portale

Scegliere ogni volta una destinazione nuova. Se esiste già, l'esportazione
fallisce per conservarla; non cancellare risultati precedenti per riprovare.

PowerShell:

```powershell
$env:EPAH_SYNTHETIC_QA_DIR = Join-Path (Get-Location) "work/synthetic-example-01"
uv run --locked pytest -q tests/test_output_bundle_quality_v0_4.py::test_real_renderers_produce_consistent_complete_synthetic_bundle
Remove-Item Env:EPAH_SYNTHETIC_QA_DIR
```

Shell POSIX:

```bash
EPAH_SYNTHETIC_QA_DIR="$PWD/work/synthetic-example-01" \
  uv run --locked pytest -q tests/test_output_bundle_quality_v0_4.py::test_real_renderers_produce_consistent_complete_synthetic_bundle
```

Il test deve terminare con esito positivo. Aprire poi
`work/synthetic-example-01/index.html`, mantenendo tutta la cartella insieme.
`work/` è ignorata da Git. In PowerShell, rimuovere la variabile d'ambiente
anche prima di una successiva esecuzione generale della suite, per evitare
esportazioni involontarie nella stessa destinazione.

## Cosa seguire nei file

1. `atlas/atlas_data.json`: catalogo dei 16 slot, Comuni fittizi, valori, anni
   e assenze; il payload dichiara `synthetic_fixture: true`.
2. `review/observations.csv`: le stesse osservazioni, compresi zero e assenze;
   `review/review.pdf` e `review/review.html` ne sono le viste leggibili.
3. `sheets/`: 27 schede da due pagine e volume unico; `sintesi.pdf` orienta
   il lettore senza attribuire validazione ai valori.
4. Manifest e registro delle evidenze: hash e corrispondenze controllati dagli
   audit. Etichette e fonti dell'esempio identificano i dati come sintetici.

La fixture verifica il pacchetto con l'audit integrato. Per ripetere
separatamente il controllo senza modificare il portale:

```powershell
uv run --locked python scripts/audit_v0_4_output_quality.py --hub work/synthetic-example-01 --json-out work/synthetic-example-01-audit.json
```

Il report QA deve essere nuovo ed esterno alla cartella del portale.
Un esito positivo riguarda coerenza e integrità del pacchetto sintetico,
non l'autenticità di fonti o la validazione scientifica.

## Passare dal codice ai dati reali

I builder importabili sono
`epah_diagnosis.visual_atlas_v0_3.build` e
`epah_diagnosis.visual_atlas_v0_4.build`. I comandi storici
`scripts/build_v0_3_visual_atlas.py` e `scripts/build_v0_4_visual_atlas.py`
delegano alle medesime implementazioni; la v0.4 importa la v0.3 come modulo
Python ordinario, senza caricare codice da un percorso dentro `scripts/`.

L'esecuzione territoriale utilizza gli input reali e le ricevute richieste dal
[workflow `epah outputs`](v0_4_developer_guide.md). Il portale sintetico non è
un input sostitutivo per quel workflow. Conservare separatamente originale,
normalizzato, anteprima e decisioni umane, come descritto nell'
[architettura](v0_4_architecture.md).
