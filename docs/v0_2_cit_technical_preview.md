# CIT Piemonte — prima anteprima territoriale per la v0.2

Questa PR chiude il passaggio fra i **due CSV aggregati ufficiali** e un prodotto di screening per i 27 Comuni: quattro mappe (cividis assoluta, diverging relativa), GeoJSON, CSV e un PDF tecnico da presentare nell'ambito dell'Assistenza Tecnica EPAH 2026.

## Stato delle fonti

Al 30 ottobre 2026 i dataset sono identificati: [combustibili](https://www.dati.gov.it/node/view-dataset/dataset?id=80540d5b-72af-4c45-901b-eb4a4f7ae9cf) e [data installazione](https://www.dati.gov.it/node/view-dataset/dataset?id=d34fb6c0-6ae3-4ff6-9915-387d21606807). Non sono stati forniti i loro CSV reali; il codice è collaudato **solo con fixture sintetiche**. Le date 2020/2025 dei cataloghi NON sono prove dell'anno di estrazione. Non committare i raw: salvarli sotto data/downloads/.

## Passaggio A: verifica schema dei CSV

    python scripts/inspect_piemonte_cit.py --mode fuel --input data/downloads/CIT_combustibili.csv
    python scripts/inspect_piemonte_cit.py --mode age --input data/downloads/CIT_data_installazione.csv

Mostra colonne, separatore, encoding, categorie top 30 e copertura dei 27 codici; **non pubblica alcun valore**. Se le colonne proposte sono ambigue, passare a prepare i nomi corretti tramite --code-col, --category-col e --count-col. Non inventare la data del file.

## Passaggio B: prepara i due estratti reali

    python scripts/prepare_piemonte_cit.py --mode fuel --input data/downloads/CIT_combustibili.csv --snapshot-date AAAA-MM-GG --out-dir outputs/quality/cit_fuel_v02 --strict
    python scripts/prepare_piemonte_cit.py --mode age --input data/downloads/CIT_data_installazione.csv --snapshot-date AAAA-MM-GG --out-dir outputs/quality/cit_age_v02 --strict

Se lo schema è diverso da quello del parser v0.2, fermarsi: l'estrattore non assegna significati alle colonne per somiglianza vaga. La data snapshot va letta dalla fonte, non sostituita con oggi.

## Passaggio C: genera tutti gli elaborati

    python scripts/build_v0_2_cit_preview.py

Input aggiuntivo: data/downloads/Limiti01012026_g.zip (confini ISTAT 2026). Output: outputs/v0.2.0-cit-preview/ con CSV combinato, GeoJSON, mappe combustibili/installazioni assolute e relative, report PDF EPAH-TA e manifest di checksum.

Facoltativo, se disponibile il nametag originale autorizzato dalle Communications Guidelines:

    python scripts/build_v0_2_cit_preview.py --epah-nametag data/downloads/EPAH_Color.png --out-dir outputs/v0.2.0-cit-preview-branded

Il nametag viene ridimensionato senza deformazioni; in sua assenza il PDF usa solo un titolo testuale.

## Caveat e unità di confronto

- I gruppi termici non coincidono con edifici, case, famiglie o impianti completi.
- Una maggiore quota gasolio/GPL indica una **presenza relativa dei vettori** in CIT: il colore rosso è un segnale di possibile esposizione, non la misura di disagio o di costo energetico.
- La vetustà usa la differenza in **anni di calendario**, non sempre l'età precisa in giorni.
- Le mappe relative si riferiscono alla media **non ponderata delle 27 quote**, a differenza del dato aggregato ponderato per numero di gruppi.
- Per percentuali, lo scostamento è espresso in punti percentuali. GeoJSON CRS84, PNG EPSG:32632.
- Nel PDF distinguere chiaramente *anteprima tecnica* da pubblicazione o certificazione ufficiale EPAH.
- I due dataset devono coprire 27/27 Comuni con denominatori non nulli e categorie combustibili riconosciute: in caso contrario l'output è bloccato.
- Il codice non modifica la matrice canonica né la release v0.1.

Se gli originali sono difficili da scaricare, seguire le pagine dei due dataset nel portale dati.gov.it e salvare i file effettivi nella cartella indicata. Il metadato pubblico non sostituisce il CSV.