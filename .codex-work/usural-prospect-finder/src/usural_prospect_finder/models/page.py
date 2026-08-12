"""Crawled page model."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from .common import new_id, require_aware_utc


class PageType(StrEnum):
    HOMEPAGE = "homepage"
    CONTACT = "contact"
    ABOUT = "about"
    TEAM = "team"
    SERVICES = "services"
    PROJECTS = "projects"
    BLOG = "blog"
    NEWS = "news"
    LEGAL = "legal"
    PRIVACY = "privacy"
    OTHER = "other"


class CrawlStatus(StrEnum):
    PENDING = "pending"
    SUCCESS = "success"
    TIMEOUT = "timeout"
    HTTP_ERROR = "http_error"
    ROBOTS_BLOCKED = "robots_blocked"
    TOO_LARGE = "too_large"
    UNSUPPORTED_CONTENT = "unsupported_content"
    UNSAFE_URL = "unsafe_url"
    REDIRECT_ERROR = "redirect_error"
    PARSE_ERROR = "parse_error"


@dataclass(frozen=True, slots=True)
class Page:
    website_id: str
    url: str
    audit_id: str | None = None
    requested_url: str | None = None
    final_url: str | None = None
    page_type: PageType = PageType.OTHER
    id: str = field(default_factory=new_id)
    status_code: int | None = None
    content_type: str | None = None
    title: str | None = None
    fetched_at: datetime | None = None
    crawl_status: CrawlStatus = CrawlStatus.PENDING
    elapsed_ms: float | None = None
    content_length: int | None = None
    content_hash: str | None = None
    language: str | None = None
    redirect_chain: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.fetched_at is not None:
            require_aware_utc(self.fetched_at, "fetched_at")
