"""Date serialization helpers."""

from datetime import datetime


def to_iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
