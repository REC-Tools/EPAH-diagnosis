# EPAH Diagnosis v0.1.0 — release scientific preflight, 30 October 2026

**Decision: NOT READY** for a validated v0.1.0 production release.
Do not create a production tag, bypass the release gate, or claim that missing
human approvals have been granted.

## Verified evidence

- The canonical matrix has **162 of 243** records labeled Dato validato.
  The remaining **81** are 27 DEA, 27 rail, and 27 school accessibility.
- All **nine** methodologies remain EXPERIMENTAL in the indicator catalog;
  the methodology review manifest contains **zero** approvals.
- Accessibility QA is technically coherent: DEA 27 × 23 = **621** routes,
  rail 27 × 9 = **243**, schools 27 × 51 = **1,377**. QA is not source signoff.
- The Ministry of Health 2025 source includes **605** national emergency
  records, **357** DEA1/DEA2 facility rows, **280** distinct hospital-host
  municipalities with 2026 ISTAT boundaries: 23 in Piemonte, **257 outside**.
  The three documented 2026 municipality-name aliases Bolzano/Bozen,
  Negrar di Valpolicella, Popoli Terme still need 2021 historical review.
- The updated Ministry 2025 Piemonte-only DEA calculation changes no
  destination, time, or distance among the 27 compared municipalities.
  This does NOT establish the closest DEA in all of Italy.
- Tommaso Ferrucci's 30/10/2026 text-signature approval in
  docs/reviews/dea_review_20261030_signed.md is for preliminary use of
  the limited Piemonte DEA methodology, NOT a completed data review.
- SFM Torino reports Germagnano–Ceres rail service resumed **13 September
  2026**. Neither Germagnano nor Ceres is among the **nine** currently
  versioned rail gateway destinations; evaluate both and regenerate
  drafts if eligible. The SFM1 page still describes Rivarolo–Pont Canavese
  as an autobus-substituted section.
- The schools' **2024/25** service snapshot should not be described as a
  reviewed 2026/27 school-offer inventory; school/rail minima coincide
  for all 27 origins and cannot serve as independent confirmation.

## New read-only original-source check

The original ISTAT Piemonte.zip contains origin routes from Piemonte
towards all Italian municipalities, not just destinations inside Piemonte.

From the repository root on the PC containing the original sources,
run the following command in a fresh output folder:

    python scripts/audit_v0_1_dea_national_coverage.py --road-zip data/downloads/Piemonte.zip --boundaries-zip data/downloads/Limiti01012026_g.zip --ministry-xlsx data/downloads/Strutture_Emergenza_2025.xlsx --draft-dir outputs/quality/dea_accessibility_2025_v03 --out-dir outputs/quality/dea_national_2025_v01 --strict

The report at outputs/quality/dea_national_2025_v01/dea_national_coverage_audit.json
records the three original ISTAT sample route values and their CSV row
locations, all **27 × 257 = 6,939** potential outside-Piemonte DEA
road pairs, and which origins would have a closer DEA outside Piemonte.
The national network is compared by municipality reference points using
road graph 2020 and service-list snapshot 2025, NOT actual 2026 ambulance
routes, queues, or access to individual hospital entrances.

A nonzero --strict exit may mean a real out-of-region faster DEA:
that does not prohibit a clearly labeled Piemonte-only proxy but
DOES prohibit describing it as the nearest DEA across Italy.
No matrix edits, signatures, metadata approvals or release promotion
are performed by the auditor.

## Essential conditions before an official release

1. Verify national DEA coverage and the three sample original routes;
   check 2021 vs 2026 codes, source attributions and reuse conditions.
2. Review the live 2026 rail gateway list after Germagnano–Ceres
   reopening; quantify changes to all 27 minima with a fresh QA draft.
3. Verify 51 MIM complete school poles against the official 2024/25
   sources and evaluate more recent 2026/27 information; check at least
   three original road pairs for school and three for rail.
4. Complete the three genuine, evidence-linked accessibility approval
   JSONs after reviewing every required flag; preserve actual reviewer,
   date, justifications, URLs and source checksums.
5. Review all nine core methodologies, including the six previously
   populated ones, and document genuine approved records before
   changing catalog maturity to OPERATIONAL or VALIDATED.
6. Promote the 81 observations via the existing finalizers in a protected
   data PR. The repository currently requires independent GitHub review
   for protected-file changes: future Unione Montana approval is a
   separate, subsequent governance decision.
7. After 243/243 genuinely valid rows and nine genuine methodology
   approvals, run the input readiness gate, build the complete bundle,
   inspect PDF, XLSX, GeoJSON and nine maps, verify manifests, then
   run the release readiness gate and only then publish v0.1.0.

## Primary sources

- Ministry of Health 2025 emergency hospital network:
  https://www.salute.gov.it/new/it/banche-dati/elenco-strutture-della-rete-dellemergenza-ospedaliera/
- ISTAT regional origin-destination distance matrices 2021:
  https://www.istat.it/notizia/matrici-di-contiguita-distanza-e-pendolarismo/
- SFM Torino 2026 passenger-rail schedules:
  https://www.sfmtorino.it/orari/
- SFM1 Rivarolo–Pont bus replacement:
  https://www.sfmtorino.it/le-linee-sfm/sfm1-pont-rivarolo-chieri/
- MIM Open Data:
  https://dati.istruzione.it/opendata/
