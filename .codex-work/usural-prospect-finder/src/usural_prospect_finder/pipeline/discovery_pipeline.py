"""Production discovery orchestration without website fetching."""

import asyncio
from collections import Counter
from dataclasses import dataclass
from typing import Any

from ..discovery import BusinessCandidate, DiscoveryCandidate, DomainClassification, QueryPlan
from ..discovery.classification import classify_result
from ..discovery.deduplication import business_candidates
from ..providers.search import SearchProvider, SearchResult
from ..storage import Repository
from ..utils.domains import canonical_domain
from ..utils.urls import normalize_url


class DiscoveryExecutionError(RuntimeError):
    """A provider query failed before observations could be persisted."""


@dataclass(frozen=True, slots=True)
class DiscoverySummary:
    queries_executed: int
    raw_results: int
    filtered: dict[DomainClassification, int]
    duplicates: int
    persisted_observations: int
    companies: tuple[BusinessCandidate, ...]

    @property
    def unique_company_domains(self) -> int:
        return len(self.companies)


@dataclass(slots=True)
class DiscoveryPipeline:
    provider: SearchProvider
    repository: Repository
    exclusions: dict[str, Any]
    category_hints: dict[str, Any] | None = None
    results_per_query: int = 20
    concurrency: int = 5

    async def run(self, plan: QueryPlan) -> DiscoverySummary:
        """Execute a plan, persist all provenance, and return unique company domains."""
        semaphore = asyncio.Semaphore(self.concurrency)

        async def search(text: str) -> list[SearchResult]:
            async with semaphore:
                return await self.provider.search(text, limit=self.results_per_query)

        try:
            result_groups = await asyncio.gather(*(search(query.text) for query in plan.queries))
        except Exception as exc:
            raise DiscoveryExecutionError(f"{self.provider.name} search failed: {exc}") from exc
        observations: list[DiscoveryCandidate] = []
        filtered: Counter[DomainClassification] = Counter()
        for query, results in zip(plan.queries, result_groups, strict=True):
            for result in results:
                observation = self._normalize(result, query.text, plan.category, plan.location)
                observations.append(observation)
                if observation.classification is not DomainClassification.COMPANY:
                    filtered[observation.classification] += 1
        with self.repository.transaction() as transaction:
            for observation in observations:
                transaction.add_discovery_candidate(observation)
        companies = tuple(business_candidates(observations))
        retained_company_observations = sum(len(company.observation_ids) for company in companies)
        return DiscoverySummary(
            queries_executed=len(plan.queries),
            raw_results=len(observations),
            filtered=dict(filtered),
            duplicates=retained_company_observations - len(companies),
            persisted_observations=len(observations),
            companies=companies,
        )

    def _normalize(
        self, result: SearchResult, query: str, category: str, location: str
    ) -> DiscoveryCandidate:
        try:
            url = normalize_url(result.url)
            domain = canonical_domain(url)
            classification = classify_result(result, self.exclusions, self.category_hints)
        except ValueError as exc:
            url = result.url
            domain = ""
            return DiscoveryCandidate(
                business_name=result.title.strip() or domain,
                url=url,
                source=str(result.metadata.get("source", "web")),
                query=query,
                position=result.position,
                category=category,
                location=location,
                canonical_domain=domain,
                provider=self.provider.name,
                classification=DomainClassification.UNKNOWN,
                filter_reason=f"invalid URL: {exc}",
                title=result.title or None,
                metadata=result.metadata,
            )
        return DiscoveryCandidate(
            business_name=result.title.strip() or domain,
            url=url,
            source=str(result.metadata.get("source", "web")),
            query=query,
            position=result.position,
            category=category,
            location=location,
            canonical_domain=domain,
            provider=self.provider.name,
            classification=classification.classification,
            filter_reason=None
            if classification.classification is DomainClassification.COMPANY
            else classification.reason,
            title=result.title or None,
            metadata={
                **result.metadata,
                "search_snippet": result.snippet,
                "classification_confidence": classification.confidence,
                "classification_reasons": list(classification.reasons),
            },
        )
