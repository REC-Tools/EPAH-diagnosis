# PR M — baseline climatica e preparazione patrimonio edilizio

## Gradi giorno
Lo snapshot locale `data/reference/climate_dpr412_green_community.csv` contiene tutti i 27 Comuni. La PR aggiunge una tabella di indicatore e un riepilogo **non ponderato** in `data/indicators/`, con controlli automatizzati su copertura, zone climatiche e coerenza dei valori con lo snapshot.

Per non equiparare controlli interni a una verifica della fonte giuridica originaria, le 27 righe `heating_degree_days` della matrice passano a **`Dato acquisito`** e non a `Dato validato`. La verifica indipendente della trascrizione rispetto all'Allegato A del DPR 412/1993, licenza e versione resta un requisito per il passaggio a `Dato validato`.

## Patrimonio edilizio
Le 27 righe `old_building_stock` restano `Da verificare`. Esistono due finalizzatori che interrogano dataset ISTAT 2011 e producono gli stessi output: l'esecuzione con successo, la copertura territoriale e il confronto della formula pre-1981 richiedono un test di acquisizione reale. Non si aggiungono valori simulati né si altera la definizione.

## Limiti
Non sono stati eseguiti download. Nessuna pipeline remota è dichiarata operativa. La CI deve confermare gli invarianti di nuova tabella e matrice a 243 righe. L'esecuzione futura di `scripts/finalize_heating_degree_days.py` può elevare direttamente lo stato a `Dato validato`; è opportuno farlo **solo dopo** la verifica della fonte normativa primaria.

## PR-03 — confronto storico indipendente (ottobre 2026)

I 27 GG e le zone climatiche coincidono con la trascrizione della tabella normativa storica pubblicata dal Dipartimento delle Finanze. La quota accessoria di Pratiglione risulta 711 m nella tabella storica e 611 m nello snapshot locale; il Comune riporta 611 m. Il finalizzatore richiede ora prova documentata di revisione umana del testo consolidato dal 9 agosto 2016 prima di promuovere le righe a `Dato validato`. La matrice rimane `Dato acquisito` fino ad allora.
