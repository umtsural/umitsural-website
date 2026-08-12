"""Business domain model."""

from dataclasses import dataclass, field
from datetime import datetime

from .common import Location, new_id, require_aware_utc, utc_now


@dataclass(frozen=True, slots=True)
class Business:
    """A commercial organization observed by discovery."""

    name: str
    category: str
    location: Location
    country: str | None = None
    id: str = field(default_factory=new_id)
    website_id: str | None = None
    first_seen_at: datetime = field(default_factory=utc_now)
    last_seen_at: datetime = field(default_factory=utc_now)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        for name in ("first_seen_at", "last_seen_at", "created_at", "updated_at"):
            require_aware_utc(getattr(self, name), name)
