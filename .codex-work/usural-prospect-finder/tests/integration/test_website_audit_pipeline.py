import asyncio
from pathlib import Path

from usural_prospect_finder.crawling.base import CrawlResult
from usural_prospect_finder.models import CrawlStatus, PageType
from usural_prospect_finder.pipeline.website_audit_pipeline import WebsiteAuditPipeline
from usural_prospect_finder.storage import SQLiteRepository

FIXTURES = Path(__file__).parents[1] / "websites"


class FixtureCrawler:
    async def fetch(self, url: str) -> CrawlResult:
        if url.endswith("robots.txt"):
            return CrawlResult(
                url,
                url,
                200,
                html="User-agent: *\nAllow: /",
                content_type="text/plain",
            )
        if "/practice-areas" in url:
            return CrawlResult(
                url,
                url,
                503,
                content_type="text/html",
                crawl_status=CrawlStatus.HTTP_ERROR,
                error="HTTP 503",
            )
        if url.rstrip("/").endswith(("team", "contact")):
            name = "contact-page" if url.rstrip("/").endswith("contact") else "team-page"
            html = (FIXTURES / name / "index.html").read_text()
        else:
            html = (FIXTURES / "modern-law-firm" / "index.html").read_text()
        return CrawlResult(url, url, 200, html=html, content_type="text/html")


def test_audit_persists_pages_contacts_signals_and_history(tmp_path: Path) -> None:
    repository = SQLiteRepository(tmp_path / "audits.sqlite3")
    repository.initialize()
    pipeline = WebsiteAuditPipeline(
        FixtureCrawler(), repository, max_pages_per_domain=4, minimum_domain_delay_seconds=0
    )
    first = asyncio.run(pipeline.run("firm.example"))
    assert first.pages_fetched == 3
    assert first.pages_failed == 1
    assert first.email_found
    assert first.phone_found
    assert first.team_page_found
    assert not first.services_page_found
    pages = repository.list_pages(first.audit_id)
    assert {page.page_type for page in pages} >= {
        PageType.HOMEPAGE,
        PageType.CONTACT,
        PageType.TEAM,
        PageType.SERVICES,
    }
    assert repository.list_contacts(first.audit_id)
    assert repository.list_signals(first.audit_id)

    second = asyncio.run(pipeline.run("firm.example"))
    website = repository.get_website_by_domain("firm.example")
    assert website is not None
    assert [audit.id for audit in repository.list_audits(website.id)] == [
        first.audit_id,
        second.audit_id,
    ]
