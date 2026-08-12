"""Repository-backed, no-network Phase 4 redesign rescoring service."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config import PROJECT_ROOT, load_yaml
from ..models import Website
from ..models.common import RunStatus
from ..scoring.base import ScoringContext
from ..scoring.redesign import RedesignAnalysis, RedesignScorer
from ..storage import Repository


@dataclass(frozen=True, slots=True)
class ScoredWebsite:
    website: Website
    company_name: str
    analysis: RedesignAnalysis


@dataclass(slots=True)
class RedesignScoringPipeline:
    repository: Repository
    configuration_path: Path = PROJECT_ROOT / "config/redesign.yaml"

    def run(self, domain: str | None = None) -> list[ScoredWebsite]:
        configuration = load_yaml(self.configuration_path)
        scorer = RedesignScorer(configuration)
        websites = self.repository.list_websites()
        if domain is not None:
            normalized = domain.casefold().removeprefix("www.")
            websites = [item for item in websites if item.canonical_domain == normalized]
            if not websites:
                raise ValueError(f"unknown domain: {domain}")
        results: list[ScoredWebsite] = []
        for website in websites:
            audits = [
                audit
                for audit in self.repository.list_audits(website.id)
                if audit.status in {RunStatus.COMPLETED, RunStatus.FAILED}
            ]
            if not audits:
                continue
            audit = audits[-1]
            signals = tuple(self.repository.list_signals(audit.id))
            context = ScoringContext(
                audit.id,
                signals,
                {"audit_status": audit.status.value},
            )
            analysis = scorer.analyze(context)
            with self.repository.transaction() as transaction:
                transaction.add_score(analysis.modernity_score)
                transaction.add_score(analysis.redesign_need_score)
            business = self.repository.get_business(website.business_id)
            if business is None:
                raise RuntimeError(f"missing business for {website.canonical_domain}")
            results.append(ScoredWebsite(website, business.name, analysis))
        return results


def score_metadata(analysis: RedesignAnalysis) -> dict[str, Any]:
    """Return the stable reporting projection for an analysis."""
    return {
        "lead_quality": analysis.lead_quality.value,
        "modernization_estimate": analysis.modernization_estimate.value,
        "dimensions": analysis.dimensions,
        "evidence_coverage": analysis.evidence_coverage,
        "reasons": [item.text for item in analysis.reasons],
        "counter_signals": [item.text for item in analysis.counter_signals],
    }
