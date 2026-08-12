"""Shared domain types."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from uuid import uuid4

JsonScalar = None | bool | int | float | str | date | datetime
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


def new_id() -> str:
    """Return a sortable-independent opaque identifier."""
    return str(uuid4())


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(UTC)


def require_aware_utc(value: datetime, field_name: str) -> None:
    """Reject naive timestamps and non-UTC offsets at domain boundaries."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    if value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} must use UTC")


class RunStatus(StrEnum):
    """Lifecycle state for persisted work."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class Location:
    """Extensible structured geography."""

    display_name: str
    city: str | None = None
    region: str | None = None
    postal_code: str | None = None
    country_code: str | None = None
    metadata: dict[str, JsonValue] | None = None
