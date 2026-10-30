# v0.2 - Anteprima APE nel report di Assistenza Tecnica EPAH

La PR aggiunge il **primo capitolo PDF e la prima mappa extra** della v0.2, senza modificare il PDF, le nove mappe o i dati della v0.1. Si tratta di una **anteprima tecnica focalizzata sugli APE**, non del rapporto finale della v0.2.

## Esegui sul PC dopo il merge

Il CSV APE e il report di controllo sono gia stati generati da `prepare_piemonte_ape_fg.py` e devono restare in:
`outputs/quality/piemonte_ape_fg_v02/`.

Utilizza anche i confini ISTAT originali in `data/downloads/Limiti01012026_g.zip`.

```powershell
python scripts/build_v0_2_ape_preview.py
```

Output in `outputs/v0.2.0-ape-preview/`:
- `diagnostic_report_v0_2_ape_preview.pdf` (report A4 di 4 pagine con focus APE)
- `map_ape_fg_share_all_uses.png` (mappa dei 27 Comuni con rendering metrico EPSG:32632)
- `chart_ape_classes.png` (distribuzione dei certificati per classi A4-G)
- `ape_fg_27_municipalities.geojson` (EPSG:4326/CRS84, 27 geometrie ufficiali)
- `ape_fg_27_municipalities.csv` (copia dell'estratto comunale)
- `ape_v0_2_manifest.json` (SHA-256, provenance, status e perimetro)
- `README.md` (interpretazione e disclaimer)

**EPAH nametag, opzionale ma consigliato:** estrarre dall'archivio di comunicazione EPAH ricevuto il file `EPAH_Color.png`, salvarlo localmente in `data/downloads/EPAH_Color.png` e usare:

```powershell
python scripts/build_v0_2_ape_preview.py --epah-nametag data/downloads/EPAH_Color.png --output-dir outputs/v0.2.0-ape-preview-branded
```

Il logo originale viene inserito senza alterarne le proporzioni. Se manca, viene usato solo testo informativo senza inventare marchi europei. Non includere font o immagini istituzionali nella repo senza i permessi.

## Significato dell'indicatore

`ape_fg_share_all_uses` = 100 x (numero APE F + G) / (numero APE di tutte le classi) del Comune. Nel CSV regionale **non compare la destinazione d'uso**. Non e' la percentuale delle *abitazioni* con scarsa performance, ne' la percentuale di *famiglie* in poverta energetica. Il dato ha snapshot 31 agosto 2026; gli APE possono avere date di emissione diverse. Il 58,87% e' la quota **aggregata** sugli 8.070 certificati dei 27 Comuni, non la media delle 27 percentuali.

La mappa usa confini ISTAT 2026 in WGS84/CRS84, e il renderer GIS esistente disegna in EPSG:32632 per prevenire distorsioni. Il PDF usa le linee della **EPAH 2026 Technical Assistance Communications Guidelines**: progetto `26-IT-Unione-TA26`, formule di collaborazione non di certificazione, logo nelle proporzioni corrette, font accessibile e attenzione a chi riceve il documento.

L'elaborazione e' un output tecnico da discutere con FERVORES e Unione Montana: non implica ancora approvazione istituzionale.
