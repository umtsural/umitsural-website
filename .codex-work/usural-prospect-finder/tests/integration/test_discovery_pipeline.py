import asyncio

from usural_prospect_finder.config import PROJECT_ROOT, load_yaml
from usural_prospect_finder.discovery import DiscoveryQuery, DomainClassification, QueryPlan
from usural_prospect_finder.pipeline.discovery_pipeline import DiscoveryPipeline
from usural_prospect_finder.providers.search import SearchResult
from usural_prospect_finder.storage import SQLiteRepository


class FixtureSearchProvider:
    name = "fixture-search"

    async def search(self, query: str, *, limit: int) -> list[SearchResult]:
        del limit
        if query.startswith("law firm"):
            return [
                SearchResult("Acme Legal", "https://www.acme.example/en/", 1),
                SearchResult("Lawyers Directory", "https://yelp.com/lawyers", 2),
            ]
        return [
            SearchResult("Acme Legal", "http://acme.example/contact", 1),
            SearchResult("Association profile", "https://directory.example/profile/acme", 2),
        ]


class MixedAggregatorProvider:
    name = "fixture-search"

    async def search(self, query: str, *, limit: int) -> list[SearchResult]:
        del query, limit
        return [
            SearchResult(
                "Best lawyers",
                "https://platform.example/rankings",
                1,
                "Rankings and detailed profiles from our curated list",
            ),
            SearchResult(
                "Acme is a law firm",
                "https://platform.example/acme",
                2,
                "Acme lawyers serve Barcelona",
            ),
        ]


def test_pipeline_preserves_provenance_filters_and_deduplicates(
    repository: SQLiteRepository,
) -> None:
    plan = QueryPlan(
        "lawyers",
        "Barcelona",
        (
            DiscoveryQuery("law firm Barcelona", "en", "lawyers", "Barcelona"),
            DiscoveryQuery("abogados Barcelona", "es", "lawyers", "Barcelona"),
        ),
    )
    pipeline = DiscoveryPipeline(
        FixtureSearchProvider(),
        repository,
        load_yaml(PROJECT_ROOT / "config/exclusions.yaml"),
    )
    summary = asyncio.run(pipeline.run(plan))
    observations = repository.list_discovery_candidates(category="lawyers", location="Barcelona")
    assert summary.raw_results == 4
    assert summary.persisted_observations == 4
    assert summary.unique_company_domains == 1
    assert summary.duplicates == 1
    assert len(summary.companies[0].observation_ids) == 2
    assert {item.query for item in observations if item.canonical_domain == "acme.example"} == {
        "law firm Barcelona",
        "abogados Barcelona",
    }
    assert summary.filtered[DomainClassification.DIRECTORY] == 2


def test_high_confidence_platform_observation_vetoes_mixed_company_result(
    repository: SQLiteRepository,
) -> None:
    plan = QueryPlan(
        "lawyers",
        "Barcelona",
        (DiscoveryQuery("lawyers Barcelona", "en", "lawyers", "Barcelona"),),
    )
    hints = {
        "company_terms": ["law firm", "lawyers"],
        "company_domain_terms": ["law", "legal"],
    }
    summary = asyncio.run(
        DiscoveryPipeline(
            MixedAggregatorProvider(),
            repository,
            load_yaml(PROJECT_ROOT / "config/exclusions.yaml"),
            category_hints=hints,
        ).run(plan)
    )
    assert summary.unique_company_domains == 0
