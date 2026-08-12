"""Business enrichment contract."""

from dataclasses import dataclass
from typing import Protocol

from ..models import Business, Signal, Website


@dataclass(frozen=True, slots=True)
class EnrichmentContext:
    business: Business
    website: Website | None = None


class Enricher(Protocol):
    name: str
    version: str

    async def enrich(self, context: EnrichmentContext) -> list[Signal]: ...


class PlaceholderEnricher:
    name = "placeholder"
    version = "0.1.0"

    async def enrich(self, context: EnrichmentContext) -> list[Signal]:
        del context
        raise NotImplementedError(f"{self.name} enrichment is not implemented in Phase 1.5")
