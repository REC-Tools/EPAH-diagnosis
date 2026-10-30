# Approvazioni umane v0.1: tre indicatori di accessibilita e nove metodologie

## Stato e principio

I 27 risultati DEA, i 27 ferroviari e i 27 scolastici dispongono di
bozze tecniche, ma nessuna approvazione umana e generata dal software.
Anche i sei indicatori gia popolati nella matrice richiedono una
revisione metodologica esplicita. La v0.1 richiede pertanto:
- tre dossier di approvazione dei dati di accessibilita (81 osservazioni);
- nove schede di approvazione metodologica, una per indicatore;
- review GitHub realmente indipendente per le modifiche protette ai dati.

## Generazione delle bozze da fonti locali con SHA-256

Aggiornare il repository dopo il merge della PR che introduce lo script.
Dalla root in PowerShell:

    python scripts/prepare_v0_1_review_packets.py --out-dir outputs/quality/human_review_packets_v01

Default dei tre report sorgenti:
- outputs/quality/dea_accessibility_2025_v03
- outputs/quality/rail_accessibility_v01
- outputs/quality/upper_secondary_accessibility_v01

Il comando controlla SHA-256 degli originali ISTAT, degli XLSX/CSV
di riferimento e degli output QA; verifica 27/27 Comuni e tutte le
coppie origine-destinazione dichiarate. Prima di scrivere richiede
una cartella di destinazione nuova. Se il percorso non coincide
con la tua copia locale, usa gli argomenti mostrati da --help.

Sono generati **otto file**:
- dea_approval.pending.json, rail_approval.pending.json,
  school_approval.pending.json: hash autentici delle bozze, decisione
  pending, flags reviewed=false, nessuna firma.
- tre checklist operative per le verifiche DEA, ferrovia e scuola.
- methodology_reviews.pending.json: nove decisioni pending.
- nine_methodology_checklists.md: nove schede con definizione,
  unita, caveat e fonte documentale per ciascun indicatore.

Questi file restano in outputs/quality, ignorato da Git; non sono
copiati in data/indicators o config/release_reviews_v0_1.json.

## Verifiche reali da compiere

Ogni checklist richiede un controllo delle fonti e licenze,
dell'ammissibilita delle destinazioni, dei codici ISTAT 2021/2026,
delle possibili destinazioni fuori regione e di almeno tre coppie
OR_PROCOM, DEST_PROCOM, TEP_TOT, KM_TOT sull'originale ISTAT.

Per DEA, il confronto della fonte ministeriale 2025 e della bozza
precedente ha restituito 27/27 righe con nessuna variazione di tempi
o destinazioni. NON prova tuttavia la copertura fuori Piemonte.
Per ferrovia bisogna controllare le nove stazioni e i servizi ferroviari,
incluso il bus sostitutivo Rivarolo-Pont.
Per scuola bisogna controllare i 51 poli MIM 2024/25 e l'offerta
attuale prima di descrivere il dato come 2026/27; i tempi scuola e
ferrovia coincidono per 27/27 Comuni.

## Conversione in approvazioni effettive

Solo dopo che una persona abbia eseguito e documentato i controlli:
1. Riportare le tre checklist e gli originali in un rapporto con URL
   HTTPS persistente, inserire data, nominativo e note motivate.
2. Aggiornare i tre JSON copiati in un luogo di review: impostare
   decision=approved solo se tutti i campi di verifica realmente
   soddisfatti; indicare l'esplicita decisione di ambito richiesta
   dal relativo finalizzatore.
3. Su un branch apposito, controllare e archiviare i CSV non tracciati
   presenti in data/indicators prima di usare i finalizzatori:
   rifiutano sovrascritture, quindi non cancellare output alla cieca.
4. Completare le nove schede metodologiche; documentare l'eventuale
   cambio da EXPERIMENTAL a OPERATIONAL o VALIDATED nel catalogo.
5. Solo a revisione avvenuta inserire i nove record approvati in
   config/release_reviews_v0_1.json. Il release gate non accetta
   record pending.
6. Creare PR con dichiarazioni Data-change: yes, Data-evidence:
   docs/reviews/... e Data-review: required, e chiedere review
   GitHub da account diverso dall'autore, sull'ultimo commit.

Il protocollo **non attribuisce approvazioni automaticamente**;
i controlli dei finalizzatori e il release gate rimangono invariati.

## Controllo finale

    pytest -q
    python scripts/check_v0_1_readiness.py --phase inputs

Il bundle finale si costruisce solo dopo 243/243 osservazioni
validate e nove revisioni metodologiche reali.
