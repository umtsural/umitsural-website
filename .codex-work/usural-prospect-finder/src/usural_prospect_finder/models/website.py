"""Website domain model."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from .common import new_id, require_aware_utc, utc_now


class WebsiteStatus(StrEnum):
    UNKNOWN = "unknown"
    ACTIVE = "active"
    UNREACHABLE = "unreachable"
    UNSAFE = "unsafe"


@dataclass(frozen=True, slots=True)
class Website:
    """A canonical website belonging to a business."""

    business_id: str
    url: str
    canonical_domain: str
    scheme: str
    id: str = field(default_factory=new_id)
    status: WebsiteStatus = WebsiteStatus.UNKNOWN
    first_seen_at: datetime = field(default_factory=utc_now)
    last_crawled_at: datetime | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        for name in ("first_seen_at", "created_at", "updated_at"):
            require_aware_utc(getattr(self, name), name)
        if self.last_crawled_at is not None:
            require_aware_utc(self.last_crawled_at, "last_crawled_at")
