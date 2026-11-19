# v0.5: decisioni 2025 e registro delle risorse abitative

Decisioni espresse dal tecnico/revisore il 19 novembre 2026:

- Descrivere l'esposizione al freddo del territorio; non stimare povertà energetica familiare.
- Anno obiettivo **2025**, preservando il periodo effettivo di ogni fonte.
- Giorni di stress da freddo e dettaglio comunale dove sostenibile.
- Primo risultato atteso: pacchetto preliminare sui **27 Comuni**, con copertura e limiti espliciti.

Queste scelte restringono il protocollo, senza approvare soglia/classe UTCI,
campo del prodotto, metodo spaziale o completezza 2025. Il pacchetto è un
obiettivo concordato, non un prodotto già generato. I mancanti rimangono
espliciti: dettaglio comunale desiderato non significa risoluzione aggiuntiva
dei dati. Le decisioni aperte nel [dossier climatico](v0_5_climate_source_feasibility.md)
restano tali; la scelta dell'anno ora è 2025, subordinata a verifica della fonte.

## Date distinte, senza pesi automatici

Il [registro JSON](v0_5_source_register.json) distingue `publication_year`,
`reference_year_start/end`, `dataset_acquired_on` e `metadata_checked_on`.
I campi sconosciuti restano null. Le date della guida non sono ereditate dalle
57 risorse; acquisire la guida non significa acquisire i dataset collegati.
La data di verifica registra anche un tentativo fallito, con stato esplicito.

```powershell
uv run --locked epah methodology sources-check --register docs/v0_5_source_register.json
```

Il controllo restituisce `target_minus_reference_end_years`: differenza firmata
fra anno obiettivo e fine del periodo, null se sconosciuto. Zero indica periodo
che termina nel 2025; un valore negativo indica un periodo successivo, non
maggiore qualità. Non è una misura di affidabilità, completezza o comparabilità.
`weights_applied` rimane false. Un eventuale peso temporale richiederà una
patch metodologica distinta: formula, motivazione per fonte, casi senza anno,
analisi di sensibilità e revisione. Non si ricalcolano gli indicatori v0.4.

Esempio reale: il comunicato [ISTAT Abitazioni occupate](https://www.istat.it/comunicato-stampa/abitazioni-occupate/)
è pubblicato nel 2026, ma riguarda 2021–2023. Il registro conserva entrambi:
rispetto al 2025 lo scarto della fine del periodo è due anni, non zero.
Non si etichettano come dati 2025 o 2026 le osservazioni del 2023.

## Come viene usata la biblioteca EUI

La guida [Abitare la città](https://www.urban-initiative.eu/sites/default/files/2026-11/Abitare_la_citta_PDF_finale.pdf),
edizione 05.11.2026, contiene 57 schede (13 politiche, 18 dati/conoscenze,
16 pratiche, 10 reti). Originale acquisito localmente con SHA-256
`1cf2a9c875e8c3ac4c83fd0b3a670d700a328330882ce1a8d34f31166656002d`.
Le 24 pagine sono state lette; p.9 è stata anche controllata visivamente.
Il registro conserva titoli, URL effettivi delle annotazioni e pagina di ogni
scheda. URL ripetuti sono preservati: le schede non sono tutte fonti distinte.
La pagina evento finale è un collegamento aggiuntivo, non una 58a scheda.

Tutte le risorse entrano nella biblioteca del progetto; non tutte sono dataset
o indicatori comunali. Sei destinazioni prioritarie sono state consultate;
8milaCensus ha restituito 403 al lettore web. Le altre sono indicizzate e da
esaminare: `indexed_only` non attesta accessibilità, contenuto aggiornato,
licenza o applicabilità locale. Nessuna norma è stata interpretata come
autorizzazione alla pubblicazione e nessuna rete è stata contattata.

| Pista | Uso iniziale e limite |
| --- | --- |
| EPAH Observatory/Handbooks | Riutilizzare metodologia e inventario esistenti; non duplicare acquisizioni o promuovere benchmark nazionali |
| ISTAT Abitazioni occupate | Contestualizzare il patrimonio; verificare dizionario e raccordo con gli originali 2023 già recuperati, non riscaricarli automaticamente |
| 8milaCensus | Pista per contesto comunale; accesso/anni da verificare, nessuna serie dichiarata 2025 |
| Mapadomo/JRC | Fonte candidata su prezzi e stock; la [pagina JRC](https://joint-research-centre.ec.europa.eu/scientific-activities/mapadomo_en) descrive armonizzazione NUTS3 e rilascio progressivo. La raccolta LAU non prova disponibilità di export per tutti i 27 Comuni |
| Eurostat Housing Database e OECD | Verificare dataset, geografia e anni per confronti, senza trasferire valori nazionali ai Comuni |
| Federcasa ERP | Contesto edilizia pubblica/sociale; disponibilità locale, unità e copertura richiedono verifica |
| Pratiche, reti e politiche | Preparare confronto e domande agli stakeholder; non convertirle in osservazioni numeriche o approvazioni |

H03/H04, H05 e mapping abitazioni restano separati. La guida EUI non è un
originale climatico UTCI o un export APE residenziale dei 27 Comuni.
Nessuna nuova osservazione municipale prodotta. Stato invariato:
`technical_draft_do_not_publish`; verifica software e revisione scientifica distinte.

## Tutte le schede, con localizzatore

I titoli sono quelli della guida; gli stati aggiornabili e le date sono nel JSON.

| ID | Pagina PDF | Risorsa | Categoria |
| --- | --- | --- | --- |
| EUI-01 | 3 | [Affordable Housing Act](https://housing.ec.europa.eu/affordable-housing-act_en) | policy |
| EUI-02 | 3 | [Affordable Housing in Europe: Real Stories of Change with NextGenerationEU](https://www.youtube.com/watch?v=L0jTLH_7esU) | policy |
| EUI-03 | 3 | [Council recommendations on fighting housing exclusion](https://employment-social-affairs.ec.europa.eu/document/download/21450169-5eaf-40e7-8a5a-4133f20510f1_en?filename=EC-anti-poverty_housing_2026.pdf) | policy |
| EUI-04 | 4 | [Developing a coordinated EU approach to housing](https://www.europarl.europa.eu/RegData/etudes/BRIE/2026/785738/EPRS_BRI(2026)785738_EN.pdf) | policy |
| EUI-05 | 4 | [EIB – Affordable and Sustainable Housing](https://www.eib.org/en/projects/topics/sustainable-cities-regions/urban-development/affordable-and-sustainable-housing) | policy |
| EUI-06 | 4 | [Financing for sustainable and affordable housing in areas under housing stress](https://housing.ec.europa.eu/affordable-housing-act/financing-areas-under-housing-stress_en) | policy |
| EUI-07 | 5 | [Making Housing Affordable in the EU: The NextGenEU Contribution](https://reforms-investments.ec.europa.eu/recovery-and-resilience-facility-1/rrf-impact/making-housing-affordable-eu_en) | policy |
| EUI-08 | 5 | [NEB Tools and Resources](https://new-european-bauhaus.europa.eu/tools-and-resources_en) | policy |
| EUI-09 | 5 | [Urban Agenda for the EU – Sustainable Tourism Action Plan](https://www.urbanagenda.urban-initiative.eu/sites/default/files/2024-11/2024_11_01_FINAL_ST_Action_Plan_0.pdf) | policy |
| EUI-10 | 6 | [Legge Regionale in materia di locazioni turistiche - Regione Puglia](https://www.consiglio.puglia.it/-/consiglio-regionale-approvata-la-legge-in-materia-di-locazioni-turistiche) | policy |
| EUI-11 | 6 | [Regole UE per la trasparenza degli affitti brevi](https://single-market-economy.ec.europa.eu/news/new-rules-bring-increased-transparency-short-term-rentals-sector-2026-05-20_en) | policy |
| EUI-12 | 6 | [Pan-European Investment Platform for Affordable and Sustainable Housing](https://housing.ec.europa.eu/pan-european-housing-investment-platform_en#towards-a-new-pan-european-investment-platform-for-affordable-and-sustainable-housing) | policy |
| EUI-13 | 7 | [Firenze – Regolamento per le locazioni turistiche brevi](https://www.comune.firenze.it/turismo/locazioni-turistiche-brevi) | policy |
| EUI-14 | 8 | [Energy Poverty Advisory Hub – Observatory](https://energy-poverty.ec.europa.eu/observatory) | knowledge_data |
| EUI-15 | 8 | [EUI Innovative Actions](https://www.urban-initiative.eu/ia-cities?keys=affordable+housing&field_thematic_interests_target_id=All&field_country_target_id=All&field_call_for_proposal_target_id=&field_related_eu_cohesion_policy_target_id=All&field_term_status_target_id=All) | knowledge_data |
| EUI-16 | 8 | [Eurostat Housing Database](https://ec.europa.eu/eurostat/web/housing/database) | knowledge_data |
| EUI-17 | 9 | [Federcasa – Osservatorio ERP](https://www.federcasa.it/osservatori/osservatorio-erp) | knowledge_data |
| EUI-18 | 9 | [ISTAT – 8milaCensus](https://ottomilacensus.istat.it/) | knowledge_data |
| EUI-19 | 9 | [ISTAT – Abitazioni occupate](https://www.istat.it/comunicato-stampa/abitazioni-occupate/) | knowledge_data |
| EUI-20 | 10 | [Lavorare e Abitare in Lombardia](https://cll.regione.lombardia.it/documenti/documenti/view?id=91) | knowledge_data |
| EUI-21 | 10 | [Mapadomo: granular housing data for Europe](https://joint-research-centre.ec.europa.eu/scientific-activities/mapadomo_en) | knowledge_data |
| EUI-22 | 10 | [OECD Affordable Housing Database](https://www.oecd.org/en/data/datasets/oecd-affordable-housing-database.html) | knowledge_data |
| EUI-23 | 11 | [PORTICO Knowledge Hub](https://portico.urban-initiative.eu/search/knowledge?kesp%5BrefinementList%5D%5Bthematic_area_facets%5D%5B0%5D=Just%20and%20Inclusive%20%3E%20Affordable%20housing) | knowledge_data |
| EUI-24 | 11 | [PORTICO Themes](https://portico.urban-initiative.eu/urban-themes/affordable-housing) | knowledge_data |
| EUI-25 | 11 | [PORTICO Urban Practices](https://portico.urban-initiative.eu/search/knowledge?kesp%5BhitsPerPage%5D=12&kesp%5BhierarchicalMenu%5D%5Bindex_name%5D%5B0%5D=kesp_urban_practices&kesp%5BrefinementList%5D%5Bthematic_area_facets%5D%5B0%5D=Just%20and%20Inclusive%20%3E%20Affordable%20housing) | knowledge_data |
| EUI-26 | 12 | [Progetto ESPON House4all](https://www.espon.eu/projects/access-affordable-and-quality-housing-all-people-house4all) | knowledge_data |
| EUI-27 | 12 | [ReHousIn: Reducing Housing Inequalities](https://rehousin.eu/) | knowledge_data |
| EUI-28 | 12 | [UAEU - Housing Partnership](https://www.urbanagenda.urban-initiative.eu/partnerships/housing) | knowledge_data |
| EUI-29 | 13 | [URBACT Knowledge Hub](https://urbact.eu/knowledge-hub/housing) | knowledge_data |
| EUI-30 | 13 | [OCA - Osservatorio Casa Abbordabile](https://oca.milano.it/) | knowledge_data |
| EUI-31 | 13 | [Bergamo – Osservatorio sull’abitare e gli affitti brevi](https://www.comune.bergamo.it/urn-solver/download-file?data=UmR0eG9temMvSi9LSC9BaUVNK2R5QT09&type=MjhLUUdtNW1ONkZxZmVFbkJRMkxXQT09) | knowledge_data |
| EUI-32 | 14 | [Basismonitor Groningen](https://basismonitor-groningen.nl/contact/) | practice |
| EUI-33 | 14 | [Biccari è in movimento: coesione e visione](https://www.youtube.com/watch?v=sSsFv6OUDBc) | practice |
| EUI-34 | 14 | [Carta dei servizi di Padova per Abitarci](https://www.padovaperabitarci.com/wp-content/uploads/2026/06/carta-dei-servizi-Padova-per-abitarci_2025_vI.pdf) | practice |
| EUI-35 | 15 | [Creating NEBourhoods Together – Monaco di Baviera](https://www.nebourhoods.de/) | practice |
| EUI-36 | 15 | [Energy Poverty Advisory Hub – Handbooks](https://energy-poverty.ec.europa.eu/observatory) | practice |
| EUI-37 | 15 | [EPIU, Getafe, ES](https://portico.urban-initiative.eu/urban-practices/epiu-getafe-es-8725) | practice |
| EUI-38 | 16 | [Evento EUI Bari – materiali e presentazioni](https://www.urban-initiative.eu/events/abitare-la-citta-politiche-la-casa-e-pianificazione-territoriale-strategica) | practice |
| EUI-39 | 16 | [Housing First Europe Hub – Resources](https://housingfirsteurope.eu/) | practice |
| EUI-40 | 16 | [ILHO (Investigation Logement Huisvesting Onderzoek) housing investigation system](https://urbact.eu/good-practices/housing-investigation) | practice |
| EUI-41 | 17 | [Jonadi WillAge – Il borgo che sarà](https://cityvision.zone/buona-pratica/borgo-erasmus-comune-di-jonadi/) | practice |
| EUI-42 | 17 | [NEB Catalogue of Blueprints](https://new-european-bauhaus.europa.eu/tools-and-resources_en) | practice |
| EUI-43 | 17 | [Ostana Smart Rural 21](https://www.smartrural21.eu/villages/ostana_it/) | practice |
| EUI-44 | 18 | [Padova per Abitarci](https://www.padovaperabitarci.com/) | practice |
| EUI-45 | 18 | [Provision of Affordable Housing by Local Authorities or subsidiaries using the Cost Rental Model](https://www.urban-initiative.eu/capacity-building/city2city/provision-affordable-housing-local-authorities-or-subsidiaries-using/about-projects) | practice |
| EUI-46 | 18 | [Reggio Emilia – ABC Abitare bene comune](https://www.comune.reggioemilia.it/novita/comunicati/a-reggio-emilia-comune-e-acer-lanciano-abc-abitare-bene-comune-una-nuova-agenda-per-la-casa) | practice |
| EUI-47 | 19 | [Milano – Piano straordinario per la casa](https://www.comune.milano.it/w/piano-casa.-comune-di-milano-apre-i-primi-tre-bandi-proposte-entro-il-26-giugno#descrizione) | practice |
| EUI-48 | 20 | [AEDES](https://aedes.nl/over-aedes/about-aedes) | network |
| EUI-49 | 20 | [Eurhonet – European Housing Network](https://www.eurhonet.eu/) | network |
| EUI-50 | 20 | [EUROCITIES](https://eurocities.eu/focusarea/housing-and-homelessness/) | network |
| EUI-51 | 21 | [European Community Land Trust Network](https://www.clteurope.org/) | network |
| EUI-52 | 21 | [European Housing alliance](https://housing.ec.europa.eu/european-housing-alliance_en) | network |
| EUI-53 | 21 | [European Network for Housing Research](https://enhr.net/) | network |
| EUI-54 | 22 | [FEANTSA](https://www.feantsa.org/) | network |
| EUI-55 | 22 | [Federcasa](https://www.federcasa.it/) | network |
| EUI-56 | 22 | [Housing Europe](https://www.housingeurope.eu/) | network |
| EUI-57 | 23 | [Housing First Europe Hub](https://housingfirsteurope.eu/) | network |
