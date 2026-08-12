"""Discovery contracts and normalized candidates."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from ..models.common import JsonValue, new_id, require_aware_utc, utc_now


class DomainClassification(StrEnum):
    COMPANY = "company"
    DIRECTORY = "directory"
    RANKING = "ranking"
    NETWORK = "network"
    RECRUITMENT = "recruitment"
    SOCIAL = "social"
    GOVERNMENT = "government"
    MARKETPLACE = "marketplace"
    NEWS = "news"
    EDITORIAL = "editorial"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class DiscoveryQuery:
    text: str
    locale: str
    category: str
    location: str


@dataclass(frozen=True, slots=True)
class QueryPlan:
    category: str
    location: str
    queries: tuple[DiscoveryQuery, ...]


@dataclass(frozen=True, slots=True)
class DiscoveryCandidate:
    business_name: str
    url: str
    source: str
    query: str
    position: int
    category: str
    location: str
    canonical_domain: str
    provider: str
    classification: DomainClassification
    filter_reason: str | None = None
    title: str | None = None
    metadata: dict[str, JsonValue] = field(default_factory=dict)
    id: str = field(default_factory=new_id)
    discovered_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        require_aware_utc(self.discovered_at, "discovered_at")


class DiscoveryService(Protocol):
    async def discover(self, *, location: str, category: str) -> list[DiscoveryCandidate]:
        """Return normalized candidates without persisting them."""
        ...


@dataclass(frozen=True, slots=True)
class BusinessCandidate:
    canonical_domain: str
    website: str
    business_name: str
    category: str
    location: str
    observation_ids: tuple[str, ...]
