"""Modernization scoring placeholder."""

from .base import ScoringContext


class ModernizationGapScorer:
    name = "modernization_gap"
    version = "0.1.0"

    def score(self, context: ScoringContext) -> None:
        del context
        raise NotImplementedError("Modernization scoring belongs to Phase 7")
