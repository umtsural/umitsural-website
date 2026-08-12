"""Analyzer context and protocol."""

from dataclasses import dataclass
from typing import Protocol

from ..models import Audit, Page, Signal, Website


@dataclass(frozen=True, slots=True)
class AnalysisContext:
    website: Website
    audit: Audit
    pages: tuple[Page, ...]


class Analyzer(Protocol):
    name: str
    version: str

    async def analyze(self, context: AnalysisContext) -> list[Signal]: ...


class PlaceholderAnalyzer:
    """Explicitly unavailable analyzer used until its implementation phase."""

    name = "placeholder"
    version = "0.1.0"

    async def analyze(self, context: AnalysisContext) -> list[Signal]:
        del context
        raise NotImplementedError(f"{self.name} analysis is not implemented in Phase 1.5")
