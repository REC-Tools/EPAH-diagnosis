# Reconciling Piemonte DEA I/II with Ministry of Health 2025

**Status: proposed source correction, pending independent review. Not a release approval.**

## Official input and reproducibility

- Landing page: https://www.salute.gov.it/new/it/banche-dati/elenco-strutture-della-rete-dellemergenza-ospedaliera/
- Uploaded original: `Strutture_Emergenza_2025.xlsx`, workbook sheet `Strutture_Emergenza_2025`; Ministry reports active services at **31 December 2025**.
- SHA-256 of supplied original: `1598e1358872f8be49006066d83bc8687f2af6a21eabfad28f82d674e0bcae6e` (76,772 bytes).
- 605 national data rows; Piemonte 44 rows: 21 `DEA1`, 9 `DEA2`, 13 `PS`, 1 empty emergency level. Only 30 explicit DEA1/DEA2 records are eligible.
- **30 eligible facility rows in 23 Piemonte municipalities**, candidate CSV SHA-256 `eedd2806ced98981311656def6e2c375dc7b7d0ce1cebf4a10f2722630963f95`. The official Ministry `Codice struttura` and `Subcodice` are retained in each source field. Names are trimmed but not completed beyond the original XLSX.

The original XLSX is **not committed**; preserve it unmodified in `data/downloads/` locally. The extraction script writes a *candidate* in `outputs/quality/` and compares the committed reference against it; it never changes the matrix. Git for Windows can check out committed LF CSVs as CRLF, so the audit ignores **only** LF vs CRLF line-ending conversion; it still rejects changed rows, columns, hospital names, codes and order. The audit reports `matches_reference_bytes`, `matches_reference` and `reference_line_endings_only_difference` separately.

## Comparison against previously committed 2023/2025 curated snapshot

| Aspect | Previous reference | Ministry 2025 candidate | Interpretation |
| --- | ---: | ---: | --- |
| Facility records | 27 | 30 | +3; not three additional destinations |
| Host municipalities | 23 | 23 | unchanged total |
| Biella | 1 | 0 | Replace municipality of Ospedale degli Infermi with Ponderano, based on official 2025 `Comune` field |
| Ponderano | 0 | 1 | Municipality for Ospedale degli Infermi (code `010032`) |
| Torino | 5 | 7 | Additional separately listed DEA2 hospital units |
| Alessandria | 1 | 2 | Separately listed pediatric DEA2 hospital unit |
| Cuorgne | 0 | 0 | Ministry classifies its hospital as `PS`: do not include as DEA |

For a nearby **cross-region candidate**, the same XLSX lists `OSPEDALE REGIONALE UMBERTO PARINI` in Aosta with `DEA2`. It is not in the Piemonte-only matrix, and whether it is actually nearer to any of the 27 municipalities **must be established using applicable original road-time routes**, not presumed.

## Effects on the technical draft

The old `dea_accessibility_v01` draft reports 27/27 outputs, with chosen destinations Ciriè (23) and Ivrea (4). Neither selected Biella, but **do not presume the proposed Ponderano destination cannot be nearer**. Recompute all 27 × 23 routes from the unchanged original ISTAT ZIP after review, save in a fresh `dea_accessibility_2025_v02` folder, and compare value-by-value against v01. The geography remains municipality-centroid to municipality-centroid in ISTAT 2021, graph 2020, **not ambulance travel or travel to the actual hospital entrance**.

## Reproduce locally

```powershell
python scripts/audit_dea_2025_source.py --source-xlsx data/downloads/Strutture_Emergenza_2025.xlsx --out-dir outputs/quality/dea_ministry_2025_v01 --strict
python scripts/prepare_dea_accessibility.py --road-zip data/downloads/Piemonte.zip --boundaries-zip data/downloads/Limiti01012026_g.zip --hospitals data/reference/piemonte_dea_hospitals.csv --out-dir outputs/quality/dea_accessibility_2025_v02
```

Before running, ensure this proposed data PR has been checked out (or merged after genuine review); otherwise the `--strict` comparison correctly reports a mismatch. Use **new output directories** on rerun.

## Quantitative v01 versus v02 comparison

After generating `dea_accessibility_2025_v02`, run:

```powershell
python scripts/compare_dea_2025_drafts.py --old-dir outputs/quality/dea_accessibility_v01 --new-dir outputs/quality/dea_accessibility_2025_v02 --out-dir outputs/quality/dea_2025_draft_comparison --strict
```

`comparison.json` reports each changed municipality, nearest destination and delta of ISTAT minutes, as well as source and QA checksums. Changes are not approvals, and matching values do not establish independent scientific validation.

**Additional 2026 geographic confirmation:** the supplied original ISTAT generalized boundary archive has `Ponderano = 096047` and `Biella = 096004`. The 2021 road matrix code crosswalk must still be verified by the user with its local ZIP.

## Outstanding sign-off

- Verify original download and attribution/reuse rights; a local checksum identifies the supplied bytes but does not prove independent source authenticity.
- Check cross-region DEA coverage (at minimum Aosta and relevant Lombardia hospitals) and the appropriateness of a Piemonte-only proxy.
- Validate 2021/2026 municipal code matching (including Ponderano) and independently sample 3 origin-destination times.
- Obtain an actual named, independent GitHub review and a real methodology decision. Until then, `validated_for_release=false` and no canonical indicator promotion.

**The 27 DEA rows in `data/verification_matrix.csv` are unchanged.** This PR is a proposed *reference* correction only.
