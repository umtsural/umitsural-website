"""Immutable audit run history."""

from dataclasses import dataclass, field
from datetime import datetime

from .common import RunStatus, new_id, require_aware_utc, utc_now


@dataclass(frozen=True, slots=True)
class Audit:
    website_id: str
    crawler_version: str
    analyzer_version: str
    configuration_hash: str
    id: str = field(default_factory=new_id)
    started_at: datetime = field(default_factory=utc_now)
    completed_at: datetime | None = None
    status: RunStatus = RunStatus.PENDING
    notes: str | None = None

    def __post_init__(self) -> None:
        require_aware_utc(self.started_at, "started_at")
        if self.completed_at is not None:
            require_aware_utc(self.completed_at, "completed_at")
