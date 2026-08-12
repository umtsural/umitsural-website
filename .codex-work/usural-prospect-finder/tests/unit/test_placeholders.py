import asyncio

import pytest

from usural_prospect_finder.analyzers.base import AnalysisContext, PlaceholderAnalyzer
from usural_prospect_finder.enrichment.base import EnrichmentContext, PlaceholderEnricher
from usural_prospect_finder.models import Audit, Business, Website
from usural_prospect_finder.models.common import Location


def test_non_cli_placeholders_fail_explicitly() -> None:
    business = Business("Fixture", "architects", Location("Barcelona"))
    website = Website(business.id, "https://example.com/", "example.com", "https")
    audit = Audit(website.id, "0.1", "0.1", "hash")
    with pytest.raises(NotImplementedError, match="analysis"):
        asyncio.run(PlaceholderAnalyzer().analyze(AnalysisContext(website, audit, ())))
    with pytest.raises(NotImplementedError, match="enrichment"):
        asyncio.run(PlaceholderEnricher().enrich(EnrichmentContext(business, website)))
