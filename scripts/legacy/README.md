# Legacy previews — not part of EPAH v0.2 stable

I tre entrypoint qui conservati sono **generatori sperimentali storici**,
spostati dalla root `scripts/` senza alterare le formule o il contratto
degli output. La root Python e stata adattata al nuovo percorso:
`Path(__file__).resolve().parents[2]`.

| Entrypoint legacy | Input locali richiesti | Output locale |
| --- | --- | --- |
| `build_municipality_comparison.py` | `data/derived/municipality_profile.csv` | `data/derived/municipality_comparison.csv` |
| `build_multidimensional_overlap.py` | `data/derived/municipality_profile.geojson` + benchmark degli indicatori | `data/derived/municipality_overlap.geojson` |
| `generate_overlap_map.py` | `data/derived/municipality_overlap.geojson` | `outputs/maps/map_multidimensional_overlap.png` |

**Per riprodurre una preview storica**, usare un clone locale con dipendenze
installate ed evidenze originali presenti; non usare questi comandi per
validare o distribuire la diagnosi:

```powershell
uv run --locked python scripts/legacy/build_municipality_comparison.py
uv run --locked python scripts/legacy/build_multidimensional_overlap.py
uv run --locked python scripts/legacy/generate_overlap_map.py
```

Gli script sono indipendenti e alcuni richiedono un profilo o una geometria
creati con altri tool legacy. **Non eseguono il gate di release**: mantenere
gli output in cartelle locali, evitare di sovrascrivere artefatti esistenti
e non considerarli dati convalidati. Per la v0.2 usare `epah report v0.2`,
`epah analysis v0.2`, `epah dashboard v0.2`, `epah review-pack v0.2`.

Gli entrypoint originali rimangono recuperabili nella cronologia Git.
La documentazione storica puo riportare i vecchi percorsi: non e una guida
operativa corrente.
