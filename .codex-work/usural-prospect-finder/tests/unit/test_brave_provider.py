import asyncio

import httpx
import pytest

from usural_prospect_finder.providers.brave import BraveSearchProvider


def test_brave_provider_normalizes_payload_offline() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-Subscription-Token"] == "test-key"
        assert request.url.params["q"] == "lawyers Barcelona"
        return httpx.Response(
            200,
            json={
                "web": {
                    "results": [
                        {
                            "title": "Estudi Jurídic",
                            "url": "https://legal.example/",
                            "description": "Corporate law",
                            "language": "ca",
                        }
                    ]
                }
            },
        )

    provider = BraveSearchProvider("test-key", transport=httpx.MockTransport(handler))
    results = asyncio.run(provider.search("lawyers Barcelona", limit=100))
    assert len(results) == 1
    assert results[0].position == 1
    assert results[0].metadata["source"] == "web"


def test_brave_provider_requires_key() -> None:
    with pytest.raises(ValueError, match="UPF_SEARCH_API_KEY"):
        BraveSearchProvider("  ")
