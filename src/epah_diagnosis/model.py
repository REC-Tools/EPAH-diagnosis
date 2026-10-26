from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class VerificationStatus(StrEnum):
    TO_VERIFY = "Da verificare"
    SOURCE_IDENTIFIED = "Fonte individuata"
    DATA_AVAILABLE = "Dato disponibile"
    DATA_ACQUIRED = "Dato acquisito"
    DATA_VALIDATED = "Dato validato"
    NOT_AVAILABLE = "Non disponibile"


@dataclass(frozen=True)
class Indicator:
    id: str
    name: str
    macro_area: str
    definition: str
    preferred_source: str
    unit: str
    priority: str = "P1"
    caveat: str = ""


INDICATORS: tuple[Indicator, ...] = (
    Indicator(
        id="population_65_plus",
        name="Popolazione ≥65 anni",
        macro_area="Socio-economic",
        definition="Residenti di 65 anni o più / popolazione residente × 100",
        preferred_source="ISTAT",
        unit="%",
        caveat="Proxy di vulnerabilità: non identifica direttamente famiglie in povertà energetica.",
    ),
    Indicator(
        id="income_vulnerability",
        name="Vulnerabilità reddituale",
        macro_area="Socio-economic",
        definition=(
            "Quota di contribuenti nelle fasce di reddito più basse. "
            "La soglia operativa sarà definita dopo la verifica delle classi MEF disponibili."
        ),
        preferred_source="MEF - Dichiarazioni fiscali",
        unit="%",
        caveat="Non fissare una soglia arbitraria prima di verificare il dataset MEF.",
    ),
    Indicator(
        id="old_building_stock",
        name="Vetustà del patrimonio abitativo",
        macro_area="Facilities/Housing",
        definition=(
            "Quota di edifici residenziali antecedenti alla soglia temporale scelta "
            "/ totale edifici residenziali × 100."
        ),
        preferred_source="ISTAT - Censimento / patrimonio edilizio",
        unit="%",
        caveat="La soglia temporale va scelta in funzione delle classi disponibili nel dataset.",
    ),
)
