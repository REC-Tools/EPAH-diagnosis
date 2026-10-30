# Contratto di release pilota EPAH v0.1.0 (27 Comuni)

Stato: policy operativa proposta per la v0.1.0. La release non e approvata automaticamente.

## Ambito e significato
- Origini: esattamente i 27 Comuni di Sinergie in Canavese, tutti e nove gli indicatori.
- Destinazioni: elenchi esterni ai 27 Comuni quando necessario (23 Comuni con DEA piemontesi, 51 poli scuola MIM, nove gateway ferroviari). Non ridurli ai 27 Comuni.
- Interpretazione: minimo TEP_TOT della matrice ISTAT 2021 (rete stradale 2020) rispetto alle destinazioni selezionate, non il servizio piu vicino in Italia.
- DEA: 30 DEA1/DEA2 del Ministero 2025 nei 23 Comuni piemontesi selezionati.
- Scuole: proxy offerta completa 2024/25, non verifica dell'offerta corrente 2026/27.
- Ferrovia: nove gateway ferroviari dello snapshot versionato; non censimento della rete 2026.

## Condizioni essenziali per la release v0.1
1. Originali e hash SHA-256 verificati; licenze e fonte citate; 27 codici ISTAT corretti e join dei codici 2021/2026 documentato.
2. Copertura 27/27 dei dati, nessun valore mancante, controlli di calcolo sui minimi rispetto ai servizi selezionati.
3. Almeno 3 controlli diretti di coppie origine/destinazione sul CSV originale ISTAT per ciascuno dei tre indicatori di accessibilita.
4. Validazione umana reale degli elenchi selezionati, con rapporti, nominativo, data, limiti e URL evidenza immutabile.
5. Tre approvazioni di accessibilita e nove approvazioni metodologiche basate su revisioni effettive; aggiornare maturita a OPERATIONAL o VALIDATED solo dopo tali revisioni.
6. Promozione tracciata delle 81 osservazioni su branch; protezione GitHub per modifiche dati attualmente richiede review indipendente di altro account.
7. Build del bundle solo quando 243/243 osservazioni e nove review soddisfano il gate: CSV, GeoJSON, nove mappe, XLSX, PDF, manifest e readiness.

## Attivita rinviate alla v0.2
- Rete nazionale DEA/alternative extra Piemonte e verifica del vero ospedale piu vicino in Italia.
- Analisi esaustiva di stazioni, linee 2026, frequenze, coincidenze e destinazioni ferroviarie esterne allo snapshot.
- Anagrafe completa scuole 2026/27, analisi dei poli scolastici extra Piemonte.
- Accessibilita porta a porta, tempi di ambulanza, trasporto pubblico e misurazione diretta della poverta energetica.

Le verifiche rimandate RESTANO false nei JSON: non attribuire loro un risultato inesistente. Le simulazioni, le statistiche e le firme testuali non sostituiscono la verifica effettiva.

## Verifica
pytest -q
python scripts/check_framework.py
python scripts/check_v0_1_readiness.py --phase inputs
python scripts/build_v0_1_bundle.py --boundaries data/geography/municipalities_2026.geojson
python scripts/check_v0_1_readiness.py --phase release
