"""Explicitly injected top-level coordination boundary."""

from dataclasses import dataclass

from .audit_pipeline import AuditPipeline
from .discovery_pipeline import DiscoveryPipeline
from .scoring_pipeline import ScoringPipeline


@dataclass(slots=True)
class ProspectFinderOrchestrator:
    discovery_pipeline: DiscoveryPipeline
    audit_pipeline: AuditPipeline
    scoring_pipeline: ScoringPipeline

    async def run(self, *, location: str, category: str, target: int) -> None:
        del location, category, target
        raise NotImplementedError("End-to-end prospecting starts in Phase 2")
