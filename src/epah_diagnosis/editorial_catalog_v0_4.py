"""v0.4 editorial crosswalk; semantic labels only, never numeric transformations.

Stable IDs, metric names, source strings, units, years, and values are owned by
the atlas builders. This file describes how to READ those metrics, not how to
recalculate them or whether their territorial sources are scientifically valid.
Its H.. labels are internal EPAH-handbook mapping, not official EPAH codes.
"""
from __future__ import annotations

from copy import deepcopy

VERSION = "0.4-editorial-crosswalk-1"
CANONICAL = (
    "population_65_plus", "income_vulnerability", "old_building_stock",
    "heating_degree_days", "mean_altitude", "dea_accessibility",
    "upper_secondary_accessibility", "rail_accessibility", "snai_classification",
)
CANDIDATES = ("H47", "H50", "H46", "H03", "H04", "H05", "ADD-HOUSING-01")


def _entry(role: str, universe: str, short: str, definition: str,
           caution: str, dimension: str) -> dict[str, str]:
    return {
        "role": role,
        "population_reference": universe,
        "short_population_reference": short,
        "operational_meaning": definition,
        "interpretation_limit": caution,
        "epah_dimension": dimension,
        "editorial_review": "technical_only_not_scientifically_approved",
    }


CATALOG = {
    "population_65_plus": _entry(
        "proxy_demografico", "Popolazione residente di ogni età", "Residenti",
        "Quota dei residenti di 65 anni e più sul totale dei residenti.",
        "Non misura direttamente fabbisogno energetico né povertà delle famiglie.",
        "socio_economica"),
    "income_vulnerability": _entry(
        "proxy_economico", "Contribuenti IRPEF nel periodo di riferimento", "Contribuenti",
        "Quota dei contribuenti con reddito dichiarato fino a 15.000 euro.",
        "I contribuenti non sono nuclei familiari. Non coincide con AROP.",
        "socio_economica"),
    "old_building_stock": _entry(
        "proxy_edilizio", "Edifici residenziali censiti nella fonte 2011", "Edifici residenziali",
        "Quota di edifici residenziali costruiti prima del 1981.",
        "L'epoca di costruzione non è una misura della classe energetica.",
        "abitazioni_ed_edifici"),
    "heating_degree_days": _entry(
        "descrittore_normativo", "Ambito geografico comunale (parametro normativo)", "Comune (normativa)",
        "Gradi-giorno previsti dalla normativa DPR 412/1993, non serie meteorologica osservata.",
        "NON confrontare come se fosse lo stesso indicatore degli HDD climatici H03.",
        "clima"),
    "mean_altitude": _entry(
        "descrittore_geografico", "Territorio comunale e modello di quota della fonte", "Territorio comunale",
        "Altitudine media in metri, descrittore della morfologia comunale.",
        "Non è un indicatore orientato automaticamente verso minore o maggiore benessere.",
        "contesto_territoriale"),
    "dea_accessibility": _entry(
        "accessibilita_stradale", "Localizzazione comunale e rete stradale del modello", "Rete stradale",
        "Tempo stradale stimato verso il Comune sede di DEA I/II più vicino.",
        "Non equivale al tempo di ambulanza, al trasporto pubblico o all'accessibilità senza auto.",
        "mobilita_servizi"),
    "upper_secondary_accessibility": _entry(
        "accessibilita_stradale", "Localizzazione comunale e rete stradale del modello", "Rete stradale",
        "Tempo stradale stimato verso un polo scolastico superiore.",
        "Non misura accesso con TPL, servizi disponibili o tempo casa-scuola individuale.",
        "mobilita_servizi"),
    "rail_accessibility": _entry(
        "accessibilita_stradale", "Localizzazione comunale e rete stradale del modello", "Rete stradale",
        "Tempo stradale stimato per raggiungere il gateway ferroviario selezionato.",
        "Non misura frequenza dei treni, distanza pedonale o accessibilità ferroviaria con TPL.",
        "mobilita_servizi"),
    "snai_classification": _entry(
        "descrittore_istituzionale", "Comune classificato dalla strategia SNAI", "Comune",
        "Classe territoriale SNAI A–F, una categoria e non una grandezza numerica.",
        "Non è un punteggio energetico, una probabilità o una misura di trasporto pubblico.",
        "contesto_territoriale"),
    "H47": _entry(
        "proxy_demografico_candidato", "Residenti nella popolazione ISTAT POSAS provvisoria 2026", "Residenti (POSAS)",
        "Quota di residenti da 0 a 11 anni sul totale della popolazione residente.",
        "La natura provvisoria dei dati e la metodologia devono essere documentate.",
        "socio_economica"),
    "H50": _entry(
        "proxy_istruzione_candidato", "Residenti di 25–64 anni, inclusi i casi con titolo non noto nella definizione dell'anteprima", "Residenti 25–64",
        "Quota di persone di 25–64 anni senza licenza media; non include chi ha la licenza media.",
        "Non confondere titolo di istruzione e povertà energetica; audit del mapping richiesto.",
        "socio_economica"),
    "H46": _entry(
        "proxy_lavoro_candidato", "Forze di lavoro di 15 anni e oltre (occupati + disoccupati)", "Forze di lavoro 15+",
        "Disoccupati divisi per forze di lavoro di almeno 15 anni; stime ISTAT anche decimali.",
        "Gli inattivi sono esclusi. Non arrotondare artificialmente le stime ufficiali.",
        "socio_economica"),
    "H03": _entry(
        "descrittore_climatico_candidato", "Cella di temperatura NWIOI associata tecnicamente al Comune", "Cella ARPA NWIOI",
        "HDD annui stimati da temperature minime e massime giornaliere, metodo Eurostat 15/18.",
        "Non equivale ai gradi-giorno normativi o a una media climatica pesata sulla popolazione.",
        "clima"),
    "H04": _entry(
        "descrittore_climatico_candidato", "Cella di temperatura NWIOI associata tecnicamente al Comune", "Cella ARPA NWIOI",
        "CDD annui stimati da temperature minime e massime giornaliere, metodo Eurostat 24/21.",
        "Non misura consumi elettrici, stress termico individuale o ondate di calore.",
        "clima"),
    "H05": _entry(
        "proxy_prestazione_edilizia_candidato", "Solo attestati APE residenziali validi nell'export filtrato", "APE residenziali validi",
        "Quota di attestati residenziali validi classificati F o G sul totale dei certificati del campione.",
        "Gli attestati non rappresentano automaticamente tutte le abitazioni; filtri da approvare.",
        "abitazioni_ed_edifici"),
    "ADD-HOUSING-01": _entry(
        "descrittore_abitativo_candidato", "Abitazioni rilevate nel Censimento ISTAT 2023", "Abitazioni censite",
        "Quota di abitazioni non occupate da persone residenti sul totale delle abitazioni censite.",
        "Non equivale a case vuote, seconde case, disponibilità per affitto o edifici inutilizzati.",
        "abitazioni_ed_edifici"),
}

assert len(CATALOG) == 16 and set(CATALOG) == set(CANONICAL) | set(CANDIDATES)


def annotate_v04(indicators: list[dict]) -> list[dict]:
    """Return a deep copy with additive metadata. Refuse unknown/reordered slots."""
    keys = [item.get("id") for item in indicators]
    if (keys != list(CANONICAL) + list(CANDIDATES[:4]) + list(CANDIDATES[4:])
            or len(keys) != 16):
        raise ValueError("v0.4 editorial catalog expects the 16 original indicator IDs in builder order")
    enriched = deepcopy(indicators)
    for item in enriched:
        if (not all(isinstance(item.get(key), str) and item[key].strip()
                    for key in ("id", "name", "unit", "family", "source", "description"))
                or item.get("available") not in (True, False)):
            raise ValueError(f"Incomplete original indicator metadata for {item.get('id')}")
        item["editorial"] = deepcopy(CATALOG[item["id"]])
        item["editorial"]["provenance_class"] = (
            "historical_pilot_technical" if item["id"] in CANONICAL
            else "candidate_technical_not_canonical"
        )
        item["editorial"]["publication_allowed"] = False
    return enriched


def snapshot(indicators: list[dict]) -> dict:
    """Serialize only fields already bound to the atlas, without editorial inference."""
    rows = []
    for metric in indicators:
        label = metric.get("editorial")
        if label is None:
            continue
        if (metric.get("id") not in CATALOG
                or not isinstance(label, dict)
                or any(label.get(key) != value for key, value in CATALOG[metric["id"]].items())):
            raise ValueError("Editorial crosswalk on atlas is incomplete or inconsistent")
        rows.append({
            "id": metric["id"], "name": metric["name"],
            "unit": metric["unit"], "family": metric["family"],
            "description": metric.get("description", ""),
            "source": metric["source"], "available": metric["available"],
            "years": metric.get("years", []), "editorial": deepcopy(label),
        })
    if rows and len(rows) != len(indicators):
        raise ValueError("Some atlas metrics have editorial metadata while others do not")
    return {
        "schema_version": VERSION,
        "status": "technical_draft_do_not_publish",
        "scientific_approval": False,
        "publication_allowed": False,
        "no_composite_score": True,
        "indicators": rows,
        "semantic_only": True,
        "note": "The reference population is descriptive; it never fills missing observation denominators.",
    }
