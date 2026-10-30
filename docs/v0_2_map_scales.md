# Mappe v0.2: scale assolute e relative

Il renderer usa geometrie CRS84/WGS84 e disegna in EPSG:32632. Non modifica GeoJSON né valori originali.

## Assoluta
Scala sequenziale scientifica Matplotlib cividis, adatta a lettura continua e con visione dei colori alterata. Il colore non implica giudizi di benessere.

## Relativa
Scostamento dalla media aritmetica non ponderata dei Comuni mappati. Lo zero è grigio (#DFE2E4), la condizione favorevole è verde (#1B7837), quella sfavorevole rossa (#B2182B); limiti cromatici simmetrici attorno allo zero.

La direzione è obbligatoria: higher_is_better o higher_is_worse. Per un indicatore in %, lo scostamento di default è in punti percentuali (p.p.), non percent change. Per indicatori in minuti o metri è la differenza assoluta. Si può scegliere percent_change con media diversa da zero.

APE F/G: valori sopra la media comunale sono sfavorevoli (rossi), sotto la media favorevoli (verdi). Non attribuire questo trattamento a altitudine/SNAI senza un giudizio scientifico motivato.

Il colore relativo descrive un confronto comunale e non la significatività statistica. Media di 27 percentuali comunali non ponderate diversa dalla quota aggregata degli 8.070 certificati APE.

La release v0.1 già distribuita non è riscritta: la versione v0.2 produrrà output separati.
## Altre mappe core

La CLI di preview genera 9 mappe assolute e 7 relative. Altitudine e SNAI non vengono colorate come benessere/malessere; gli HDD vengono interpretati solo come maggiore pressione per riscaldamento, non prova di povertà energetica.

Comando: python scripts/generate_diagnostic_maps.py --map-mode both --output-dir outputs/maps_v0_2

Usare --input per indicare un GeoJSON già arricchito con i 9 indicatori. Non si sovrascrivono le mappe storiche.

Il percorso di input predefinito della CLI è outputs/v0.1.0-pilot/municipality_profile.geojson (builder pilota). Se assente, usare --input e una nuova directory per --output-dir.
