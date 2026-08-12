"""Public contact facts."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from .common import new_id, require_aware_utc, utc_now


class ContactType(StrEnum):
    EMAIL = "email"
    PHONE = "phone"
    SOCIAL = "social"
    CONTACT_FORM = "contact_form"
    ADDRESS = "address"


class ContactClassification(StrEnum):
    GENERIC_BUSINESS = "generic_business"
    PERSONAL_BUSINESS = "personal_business"
    SUPPORT = "support"
    MARKETING = "marketing"
    BILLING = "billing"
    TECHNICAL = "technical"
    INVALID = "invalid"
    PLACEHOLDER = "placeholder"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Contact:
    business_id: str
    website_id: str
    type: ContactType
    value: str
    source_url: str
    audit_id: str | None = None
    id: str = field(default_factory=new_id)
    classification: ContactClassification = ContactClassification.UNKNOWN
    confidence: float = 0.0
    is_public: bool = True
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        require_aware_utc(self.created_at, "created_at")
