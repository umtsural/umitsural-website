"""Production Brave Search API adapter."""

from typing import Any

import httpx

from .search import SearchResult


class BraveSearchProvider:
    name = "brave"

    def __init__(
        self,
        api_key: str,
        *,
        timeout: float = 20.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("UPF_SEARCH_API_KEY is required for discovery")
        self._api_key = api_key
        self._timeout = timeout
        self._transport = transport

    async def search(self, query: str, *, limit: int) -> list[SearchResult]:
        headers = {"Accept": "application/json", "X-Subscription-Token": self._api_key}
        params: dict[str, str | int] = {"q": query, "count": min(max(limit, 1), 20)}
        async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
            response = await client.get(
                "https://api.search.brave.com/res/v1/web/search", headers=headers, params=params
            )
            response.raise_for_status()
        payload: dict[str, Any] = response.json()
        raw_results = payload.get("web", {}).get("results", [])
        if not isinstance(raw_results, list):
            raise ValueError("search provider returned an invalid results payload")
        results: list[SearchResult] = []
        for position, item in enumerate(raw_results, start=1):
            if not isinstance(item, dict) or not isinstance(item.get("url"), str):
                continue
            results.append(
                SearchResult(
                    title=str(item.get("title", "")),
                    url=item["url"],
                    position=position,
                    snippet=str(item["description"]) if item.get("description") else None,
                    metadata={
                        "language": item.get("language"),
                        "source": "web",
                        "type": item.get("type"),
                    },
                )
            )
        return results
