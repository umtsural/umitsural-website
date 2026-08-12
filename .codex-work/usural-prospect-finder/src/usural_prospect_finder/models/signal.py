"""Persistable evidence signals."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from .common import JsonValue, new_id, require_aware_utc, utc_now


class SignalCategory(StrEnum):
    WORDPRESS = "wordpress"
    TECHNOLOGY = "technology"
    MODERNITY = "modernity"
    SEO = "seo"
    PERFORMANCE = "performance"
    ACCESSIBILITY = "accessibility"
    CONTENT_FRESHNESS = "content_freshness"
    MOBILE = "mobile"
    SECURITY = "security"
    BUSINESS_QUALITY = "business_quality"
    COMMERCIAL_CAPACITY = "commercial_capacity"
    CONTACTABILITY = "contactability"
    DISCOVERY = "discovery"


@dataclass(frozen=True, slots=True)
class Signal:
    name: str
    category: SignalCategory
    value: JsonValue
    business_id: str | None = None
    website_id: str | None = None
    page_id: str | None = None
    audit_id: str | None = None
    id: str = field(default_factory=new_id)
    weight: float = 1.0
    confidence: float = 1.0
    source_url: str | None = None
    evidence: str | None = None
    metadata: dict[str, JsonValue] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        require_aware_utc(self.detected_at, "detected_at")
