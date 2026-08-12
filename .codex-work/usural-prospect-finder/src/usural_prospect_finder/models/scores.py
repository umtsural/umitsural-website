"""Explainable score models."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from .common import JsonValue, new_id, require_aware_utc, utc_now


class ScoreType(StrEnum):
    WEBSITE_MODERNITY = "website_modernity"
    REDESIGN_NEED = "redesign_need"
    MODERNIZATION_GAP = "modernization_gap"
    SEO_HEALTH = "seo_health"
    SEO_GAP = "seo_gap"
    BUSINESS_QUALITY = "business_quality"
    COMMERCIAL_CAPACITY = "commercial_capacity"
    CONTACTABILITY = "contactability"
    OPPORTUNITY = "opportunity"


@dataclass(frozen=True, slots=True)
class Score:
    audit_id: str
    score_type: ScoreType
    score: float
    confidence: float
    id: str = field(default_factory=new_id)
    top_positive_signals: tuple[str, ...] = ()
    top_negative_signals: tuple[str, ...] = ()
    reason: str | None = None
    scorer_version: str = "unknown"
    configuration_version: str = "unknown"
    configuration_hash: str = ""
    metadata: dict[str, JsonValue] = field(default_factory=dict)
    calculated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not 0 <= self.score <= 100:
            raise ValueError("score must be between 0 and 100")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        require_aware_utc(self.calculated_at, "calculated_at")


@dataclass(frozen=True, slots=True)
class ModernizationGapScore(Score):
    score_type: ScoreType = field(default=ScoreType.MODERNIZATION_GAP, init=False)


@dataclass(frozen=True, slots=True)
class SEOHealthScore(Score):
    score_type: ScoreType = field(default=ScoreType.SEO_HEALTH, init=False)


@dataclass(frozen=True, slots=True)
class SEOGapScore(Score):
    score_type: ScoreType = field(default=ScoreType.SEO_GAP, init=False)


@dataclass(frozen=True, slots=True)
class BusinessQualityScore(Score):
    score_type: ScoreType = field(default=ScoreType.BUSINESS_QUALITY, init=False)


@dataclass(frozen=True, slots=True)
class CommercialCapacityScore(Score):
    score_type: ScoreType = field(default=ScoreType.COMMERCIAL_CAPACITY, init=False)


@dataclass(frozen=True, slots=True)
class ContactabilityScore(Score):
    score_type: ScoreType = field(default=ScoreType.CONTACTABILITY, init=False)


@dataclass(frozen=True, slots=True)
class OpportunityScore(Score):
    score_type: ScoreType = field(default=ScoreType.OPPORTUNITY, init=False)
