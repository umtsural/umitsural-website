"""Commercial prospect projection."""

from dataclasses import dataclass
from enum import StrEnum

from .business import Business
from .contact import Contact
from .scores import Score
from .website import Website


class LeadQuality(StrEnum):
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ModernizationEstimate(StrEnum):
    LIKELY_RECENT = "LIKELY_RECENT"
    LIKELY_2_4_YEARS = "LIKELY_2_4_YEARS"
    LIKELY_5_PLUS_YEARS = "LIKELY_5_PLUS_YEARS"
    LEGACY_IMPL = "LEGACY_IMPL"
    UNKNOWN = "UNKNOWN"


class OpportunityType(StrEnum):
    WEBSITE_REDESIGN = "WEBSITE_REDESIGN"
    SEO = "SEO"
    REDESIGN_AND_SEO = "REDESIGN_AND_SEO"
    PERFORMANCE = "PERFORMANCE"
    LOCAL_SEO = "LOCAL_SEO"
    MULTILINGUAL_SEO = "MULTILINGUAL_SEO"
    DIGITAL_STRATEGY = "DIGITAL_STRATEGY"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class Prospect:
    business: Business
    website: Website
    contacts: tuple[Contact, ...] = ()
    wordpress_status: str = "unknown"
    wordpress_confidence: float = 0.0
    detected_theme: str | None = None
    detected_plugins: tuple[str, ...] = ()
    modernization_gap: Score | None = None
    seo_health: Score | None = None
    seo_gap: Score | None = None
    business_quality: Score | None = None
    commercial_capacity: Score | None = None
    contactability: Score | None = None
    opportunity: Score | None = None
    lead_quality: LeadQuality = LeadQuality.LOW
    primary_opportunity: OpportunityType = OpportunityType.UNKNOWN
    secondary_opportunity: OpportunityType | None = None
    reason: str | None = None
    notes: str | None = None
