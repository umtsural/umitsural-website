"""Search provider port and normalized result."""

from dataclasses import dataclass, field
from typing import Protocol

from ..models.common import JsonValue


@dataclass(frozen=True, slots=True)
class SearchResult:
    title: str
    url: str
    position: int
    snippet: str | None = None
    metadata: dict[str, JsonValue] = field(default_factory=dict)


class SearchProvider(Protocol):
    name: str

    async def search(self, query: str, *, limit: int) -> list[SearchResult]: ...
