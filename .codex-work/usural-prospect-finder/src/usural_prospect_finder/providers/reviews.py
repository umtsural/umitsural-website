"""Review provider port and normalized result."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ReviewSummary:
    rating: float | None
    review_count: int
    source: str


class ReviewProvider(Protocol):
    name: str

    async def summarize(self, canonical_domain: str) -> ReviewSummary: ...
