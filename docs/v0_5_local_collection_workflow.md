# Primo workflow v0.5: dalle fonti territoriali al protocollo revisionabile

Destinatario: tecnico incaricato e revisore della diagnosi EPAH per i 27 Comuni.
Punto di partenza concordato: **contesto climatico e abitativo**, prima delle
interviste e delle misure dichiarate dalle famiglie. Software stabile v0.4.0;
questo incremento prepara la v0.5, senza pubblicare nuove osservazioni.

## 1. Partire da una proposta e da una domanda diagnostica

Primo caso di lavoro: **V05-02, giorni di stress da freddo**, per verificare se
la fonte e un metodo documentato consentano una lettura territoriale utile.
È una scelta per il dossier, non l'approvazione dell'indicatore locale.
Usare il [catalogo](v0_5_indicator_contracts.json) e la
[metodologia](v0_5_methodology.md) già presenti, senza ricopiare definizioni.

Il contratto disponibile riguarda un benchmark nazionale/grigliato aggregato.
Il protocollo locale rimane da decidere. Non convertire il valore nazionale in
valori comunali e non usarlo come prevalenza di povertà energetica.

## 2. Generare la scheda senza alterare fonti o prodotti

Dal checkout del branch `feat/v05-local-collection-protocol`:

```powershell
uv sync --python 3.11 --locked --group dev
uv run --locked epah methodology check --catalog docs/v0_5_indicator_contracts.json
uv run --locked epah methodology prepare --catalog docs/v0_5_indicator_contracts.json --indicator V05-02 --out-dir work/v05-cold-stress-01
```

Ogni esecuzione richiede una destinazione nuova, anche se quella precedente è
vuota. Nessun download, estrazione, calcolo o modifica al catalogo. Per verificare
la catena dei prodotti v0.4 indipendentemente dal protocollo:

```powershell
uv run --locked epah examples synthetic --out-dir work/v05-baseline-synthetic-01
```

Aprire `work/v05-cold-stress-01/README_REVIEW.md`, poi `protocol.json`.
Il file conserva il contratto di benchmark e la fonte originali, l'hash del
catalogo esatto e domande con risposte inizialmente `null`. Non eredita
automaticamente universo, periodi o denominatori per un calcolo municipale.
Il risultato è `protocol_template_prepared_not_ready_for_collection`.

## 3. Compilare una copia con evidenze, prima di cercare altri archivi

Conservare la cartella generata come baseline; compilare una copia locale
esterna al repository. Per ogni voce in `local_decisions`, inserire una proposta
in `proposed_answer` e un riferimento in `evidence_reference`. Se una voce non è
applicabile a una fonte grigliata, motivarlo esplicitamente. Non modificare
`benchmark_contract`, `benchmark_source`, hash o stati di autorizzazione.
Non inserire dati personali; il dossier compilato può contenere riferimenti
locali e non va committato automaticamente.

Per il primo passaggio il tecnico verifica:

| Evidenza da cercare | Decisione da preparare | Limite da preservare |
| --- | --- | --- |
| Inventario effettivo di originali, QA e ricevute già locali | Quali file esistono, quali mancano, quali sono riutilizzabili | Non riacquisire file soltanto perché una nota storica li descrive mancanti |
| Specifica del prodotto UTCI, variabile, unità, versione e licenza | Quale fonte sostiene V05-02 e quale accesso è consentito | Tmin/Tmax e HDD/CDD non equivalgono automaticamente a UTCI |
| Coordinate, griglia, maschera, calendario e copertura temporale | Quale estrazione e aggregazione territoriale proporre | Nessuna soglia, formula, anno o ponderazione scelti dal software |
| Registro/confini e copertura dei 27 Comuni | Quale raccordo geografico e come trattare lacune | Nessun valore nazionale distribuito ai Comuni |
| Dizionario e QA della fonte abitativa selezionata | Quale unità osservare e quale denominatore | Persone in abitazioni riqualificate non sono edifici ristrutturati |

Per l'abitativo si può preparare separatamente il dossier **V05-04**, cambiando
`--indicator` e destinazione. Il suo benchmark riguarda persone 16+ in abitazioni
migliorate: non sostituisce H05 o la serie sulle abitazioni non occupate.

## 4. Revisionare le scelte e registrare i blocchi distinti

Tu sei il revisore tecnico. Prima di proporre implementazioni, esamina le
risposte e registra una decisione riferita alla versione esatta del dossier,
con evidenze, responsabile e data. La compilazione del file e `methodology check`
non verificano la validità delle risposte e non autorizzano raccolta o calcolo.
Il comando `check` continua a controllare soltanto il catalogo delle proposte.

Restano distinti i [blocchi scientifici v0.4](v0_4_scientific_decisions.md):

- **H03/H04:** originali climatici recuperati, decisioni metodologiche aperte.
  Non vengono risolte introducendo una proposta UTCI.
- **H05:** fonte APE residenziale comunale ancora necessaria.
- **Abitazioni e altri candidati:** mapping e revisioni umane dei rispettivi
  dossier, senza promozione automatica.

Le interviste agli stakeholder serviranno a validare rilevanza e interpretazione.
Non sostituiscono specifiche della fonte, audit numerico o un campione
rappresentativo, e non approvano automaticamente formule o prevalenze comunali.

## 5. Aprire la prossima PR soltanto su una decisione circoscritta

Questa prima PR consegna il generatore della scheda, regressioni sintetiche e
questa guida. Criterio di successo: un altro tecnico produce lo stesso dossier
dal medesimo catalogo, vede tutte le scelte aperte e non sovrascrive evidenze.

La PR successiva potrà documentare la fattibilità di **una** fonte climatica o
abitativa usando l'inventario esistente: disponibilità, specifiche, licenza,
copertura e decisioni richieste. Un estrattore seguirà soltanto un contratto
metodologico deliberato, con fixture sintetiche e replay indipendente.
Le nuove osservazioni richiederanno poi contratti e audit espliciti; i 16 slot
storici v0.4 e i risultati esistenti rimangono preservati.

Seguire [CONTRIBUTING](../CONTRIBUTING.md): branch dedicato, commit mirati,
draft PR, suite bloccata e CI, revisione. Nessun merge, tag o rilascio v0.5
automatico. I dossier restano `technical_draft_do_not_publish`.
