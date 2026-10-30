# PR-06 — QA accessibilità sanitaria DEA I/II

## Definizione e limiti

Indicatore: minimo tempo stradale **TEP_TOT** fra il centroide della sezione
censuaria contenente il municipio e il Comune sede di un **DEA I o II** nello
snapshot degli ospedali piemontesi. Non misura percorsi casa–ospedale,
ambulanza, trasporto pubblico, né tempo verso l'ingresso della struttura.

La rete candidata è limitata al **Piemonte**, non alla rete nazionale.
Un DEA oltre confine potrebbe risultare più vicino. Non presentare il dato
come "DEA nazionale più vicino" senza revisione del perimetro e della rete
nazionale 2025. La proposta di riferimento **2025** della PR di riconciliazione
include 30 DEA in 23 Comuni piemontesi, ricavati dal foglio del Ministero.
La modifica Biella → Ponderano obbliga a rigenerare la bozza DEA; in assenza
di approvazione umana il dataset resta soltanto candidato.
Vedere [riconciliazione ministeriale 2025](dea_2025_ministry_reconciliation_20261030.md).

Fonti:
- [ISTAT matrici delle distanze](https://www.istat.it/notizia/matrici-di-contiguita-distanza-e-pendolarismo/):
  geografia comunale 01/01/2021, rete viaria 2020, minuti TEP_TOT, km KM_TOT.
- [Ministero della Salute, rete emergenza ospedaliera](https://www.salute.gov.it/new/it/banche-dati/elenco-strutture-della-rete-dellemergenza-ospedaliera/):
  elenco 2025 dei DEA I/II, PS e PS pediatrici; solo DEA I/II sono ammissibili.
- [Regione Piemonte, DGR 7463/2023](https://www.regione.piemonte.it/governo/bollettino/abbonati/2023/39/attach/dgr_07463_1050_25092023.pdf).
- `data/reference/piemonte_dea_hospitals.csv`: elenco locale da verificare.

## Fase 1: preparazione riproducibile offline

Acquisire e conservare localmente gli ZIP originali:
`Piemonte.zip` della matrice ISTAT 2021 e
`Limiti01012026_g.zip` dei confini ufficiali ISTAT 2026.

```bash
python scripts/prepare_dea_accessibility.py \
  --road-zip /local/Piemonte.zip \
  --boundaries-zip /local/Limiti01012026_g.zip \
  --out-dir outputs/quality/dea_accessibility
```

Il codice verifica:
1. 27 codici ISTAT comunali a sei cifre e corrispondenza con confini 2026.
2. DEA I/II soltanto e nessun record duplicato nel registro delle strutture.
3. Tutte le **27 × N destinazioni** nella matrice origine–destinazione;
   vietati percorsi mancanti, duplicati, tempi negativi, NaN o infiniti.
4. Selezione deterministica del minimo TEP_TOT (non distanza in linea d'aria).
5. Dati aggregati e statistiche descrittive senza score composito.

Output: `dea_accessibility_minutes.csv`,
`dea_accessibility_summary.csv`, `dea_accessibility_qa.json` con
checksum SHA-256 dei veri input e output, anni di riferimento e flag
`technical_checks_only` e `validated_for_release=false`.
Non scrive in `data/verification_matrix.csv` e rifiuta di sovrascrivere
una bozza già presente.

## Fase 2: revisione scientifica documentata

Prima di pubblicare, verificare indipendentemente:
- provenienza, data di acquisizione e licenze degli archivi ISTAT e salute;
- struttura, livello DEA e operatività della rete **2025**, anche fuori Piemonte;
- ammissibilità di un proxy Piemonte-only per il caso pilota;
- passaggio amministrativo da codici ISTAT 2026 a matrice ISTAT 2021;
- almeno tre coppie origine/destinazione e relativo TEP_TOT alla fonte.

L'approvazione JSON deve contenere `indicator_id="dea_accessibility"`,
`reference_year="2021"`, `road_graph_year="2020"`, `decision="approved"`,
i sei campi `*_sha256` del report di QA, `reviewed_by`,
`reviewed_on`, `review_evidence_url` HTTPS e `review_notes`.
Richiede inoltre flag `true` per
`source_authenticity_reviewed`, `national_2025_dea_network_reviewed`,
`cross_region_eligibility_reviewed`, `historical_code_crosswalk_reviewed`,
`license_reviewed`, `independent_route_sample_reviewed`
e `methodology_scope_decision="piemonte_dea_proxy_approved_with_limits"`.

```bash
python scripts/finalize_dea_accessibility.py \
  --road-zip /local/Piemonte.zip \
  --boundaries-zip /local/Limiti01012026_g.zip \
  --draft-dir outputs/quality/dea_accessibility \
  --approval /local/dea_approval.json
```

Il finalizzatore ricalcola gli output dai file originali, controlla gli hash
e aggiorna solo le 27 osservazioni DEA tramite upsert atomico della matrice.
La semplice presenza di un JSON non autentica l'identità del revisore.

**Stato PR-06:** fonti reali non scaricate o riviste durante questa PR;
nessuna riga della matrice viene promossa. L'indicatore resta
`Da verificare` fino all'acquisizione e revisione reale.

## Esecuzione dopo il merge della reference PR e verifica indipendente

Con l'originale Ministero della Salute conservato in `data/downloads/` (non
committato), riprodurre l'estrazione e controllare che il riferimento coincida:

```powershell
python scripts/audit_dea_2025_source.py --source-xlsx data/downloads/Strutture_Emergenza_2025.xlsx --out-dir outputs/quality/dea_ministry_2025_v01 --strict
```

Poi produrre una **nuova** bozza, senza sovrascrivere la precedente:

```powershell
python scripts/prepare_dea_accessibility.py --road-zip data/downloads/Piemonte.zip --boundaries-zip data/downloads/Limiti01012026_g.zip --hospitals data/reference/piemonte_dea_hospitals.csv --out-dir outputs/quality/dea_accessibility_2025_v02
```

Confrontare le 27 righe della precedente bozza con la bozza ministeriale 2025,
senza attivare un finalizzatore:

```powershell
python scripts/compare_dea_2025_drafts.py --old-dir outputs/quality/dea_accessibility_v01 --new-dir outputs/quality/dea_accessibility_2025_v02 --out-dir outputs/quality/dea_2025_draft_comparison --strict
```

La matrice non viene promossa da questi comandi. Servono ancora controlli
interregionali e la revisione di almeno tre rotte sull'originale ISTAT.
