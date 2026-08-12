"""Asynchronous crawler contracts."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from ..models.common import utc_now
from ..models.page import CrawlStatus


@dataclass(frozen=True, slots=True)
class CrawlResult:
    requested_url: str
    final_url: str | None = None
    status_code: int | None = None
    headers: dict[str, str] = field(default_factory=dict)
    html: str | None = None
    content_type: str | None = None
    elapsed_ms: float | None = None
    fetched_at: datetime = field(default_factory=utc_now)
    error: str | None = None
    crawl_status: CrawlStatus = CrawlStatus.SUCCESS
    redirect_chain: tuple[str, ...] = ()


class Crawler(Protocol):
    async def fetch(self, url: str) -> CrawlResult:
        """Fetch one validated public URL."""
        ...


class StaticCrawler(Crawler, Protocol):
    """Marker contract for HTTP-only crawlers."""


class BrowserCrawler(Crawler, Protocol):
    """Marker contract for future browser-backed crawlers."""
