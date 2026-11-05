# V0.2 | Schede comunali (27 PDF A4)

Questa funzione crea **una pagina PDF per ciascuno dei 27 Comuni**,
utilizzando soltanto il bundle pilota v0.1 verificato. Gli otto
indicatori numerici mostrano il valore comunale, la mediana dei
27 Comuni e l'anno della fonte. SNAI rimane una categoria.

Da PowerShell, dopo il merge:

~~~powershell
uv run --locked epah sheets v0.2 --bundle outputs/v0.1.0-pilot --out-dir outputs/v0.2-municipal-sheets
~~~

La destinazione deve essere nuova; non vengono alterati gli input.
Produce `municipalities/<codice_istat>.pdf` (27 schede) e
`sheets_index_v0_2.json` con SHA-256 e provenienza.

**Limiti:** nessun indice composito, stima di famiglie vulnerabili,
dato CIT non verificato o nuovo valore osservato. Le mediane sono
non ponderate e non costituiscono una soglia di povertà energetica.
Gli anni e i denominatori dei proxy non sono necessariamente allineati.
Le schede riportano `NON PUBBLICARE`: la validazione istituzionale
resta distinta dall'accettazione tecnica del pilota.

La suite automatica verifica che ciascuna scheda abbia una pagina A4,
contenga il codice ISTAT e lo status di bozza, e corrisponda al manifest.
La revisione grafica visiva rimane necessaria prima della condivisione.
