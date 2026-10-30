# Indicatore v0.2 — Quota APE classi F/G (tutte le destinazioni d'uso)

## Decisione sulla fonte, 30 ottobre 2026

**Fonte:** Regione Piemonte / CSI Piemonte, "Numero di Attestati di Prestazione Energetica distinti per classe energetica e per Comune", \`Ape_comune_c_3985\`.

- Catalogo: https://www.dati.gov.it/node/view-dataset/dataset?id=63401619-1a9f-4382-8399-84c20c59dad0
- Licenza dei dati: **CC BY 4.0**; attribuire Regione Piemonte / CSI Piemonte e indicare elaborazione, data, URL e licenza.
- File effettivamente analizzato: \`regpie-Ape_comune_c_3985-all.csv\`.
- **SHA-256 originale:** \`77f7f171106bb64429fef74486fef56ed5a6bb2435c16b95c998fc47c5bebd97\`
- **Data nel CSV originale:** \`2026-08-31T00:00:00.000Z\` in tutte le 1.219 righe. La data 2018 nei metadati del catalogo NON è la data di questo snapshot.
- Comuni presenti: 1.215 codici distinti; 4 duplicati con denominazioni storiche alternative e conteggi identici **fuori** dai 27 Comuni. Le 27 corrispondenze ISTAT sono uniche.

**Risultato dei 27 Comuni:** 8.070 APE, dei quali 4.751 in classe F o G, pari a **58,87% degli APE registrati nel campione territoriale**. Ogni Comune ha il proprio denominatore, da **18** a **1.855** certificati. Non leggere il 58,87% come media semplice delle 27 quote comunali.

### Denominatore e interpretazione corretta

Il CSV contiene \`Key_istat_comune\`, \`Desc_comune\`, le classi energetiche \`Classe_a4\` ... \`Classe_g\` e \`Data_aggiornamento_record\`. **Non contiene la destinazione d'uso** né i certificati per singolo edificio o il conteggio di tutte le abitazioni comunali.

Si definisce pertanto **\`ape_fg_share_all_uses\`**:

    100 * (Classe_f + Classe_g) / sum(Classe_a4, Classe_a3, Classe_a2,
                                     Classe_a1, Classe_b, Classe_c,
                                     Classe_d, Classe_e, Classe_f, Classe_g)

Valido solo per i certificati censiti nello snapshot; **non è** la quota di abitazioni residenziali in classe F/G, e **non è** un indicatore diretto di povertà energetica delle famiglie. Il nome preesistente \`poor_energy_label_share\` resta riservato alla quota **residenziale**, quando sarà disponibile una fonte che consenta il filtro corretto.

### Dove conservare i dati

**Consigliato**:
- Salvare l'originale in \`data/downloads/regpie-Ape_comune_c_3985-all.csv\`. Questa cartella è intenzionalmente in \`.gitignore\`: evitare di importare automaticamente tutti i dati Piemonte in Git.
- Versionare **codice, documentazione metodologica e checksum**; gli output generati sono sotto \`outputs/quality/\`, anche questo ignorato.
- Qualora serva distribuire un snapshot completo e immutabile, proporre una PR dati **separata** con licenza, hash e diff esplicito, rispettando il protected-data guard.

### Rigenera il dataset comunale

    python scripts/prepare_piemonte_ape_fg.py

Oppure:

    python scripts/prepare_piemonte_ape_fg.py --input data/downloads/regpie-Ape_comune_c_3985-all.csv --registry data/municipalities.csv --out-dir outputs/quality/piemonte_ape_fg_v02

Output: \`ape_fg_27_municipalities.csv\` (27 Comuni, 10 classi, totale, F+G, quota %, data) e \`ape_fg_qa.json\` (checksum fonte e risultati, copertura, duplicati extra-area, fonte/licenza, significato e limiti). Il programma rifiuta di sovrascrivere output esistenti e dati anomali.

### Integrazione successiva

Il prossimo modulo del report v0.2 deve leggere questo CSV con stato **\`technical_extraction_only\`** e riportare **anno, N certificati, significato non residenziale e limiti** accanto alle mappe. Evitare di sostituire retroattivamente l'indicatore storico degli edifici ante-1981. Se una nuova fonte con filtro residenziale sarà disponibile, generare un *secondo* indicatore distintamente denominato.

**Nessuna modifica** alla matrice e alla release pilota v0.1; l'estrazione non costituisce una firma o certificazione dell'Unione Montana.
