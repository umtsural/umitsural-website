"""Phase 3 selective crawl orchestration and objective evidence persistence."""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass, replace
from urllib.parse import urlsplit

from ..crawling.base import Crawler, CrawlResult
from ..crawling.extraction import HtmlEvidence, extract_html
from ..crawling.page_selector import LinkCandidate, classify_page, select_pages
from ..crawling.robots import RobotsPolicy
from ..models import (
    Audit,
    Business,
    Contact,
    ContactClassification,
    ContactType,
    CrawlStatus,
    Page,
    PageType,
    Signal,
    SignalCategory,
    Website,
)
from ..models.common import JsonValue, Location, RunStatus, utc_now
from ..storage import Repository
from ..utils.domains import canonical_domain
from ..utils.urls import normalize_url

CRAWLER_VERSION = "3.0-static"


@dataclass(frozen=True, slots=True)
class WebsiteAuditSummary:
    domain: str
    audit_id: str
    homepage_url: str | None
    pages_selected: int
    pages_fetched: int
    pages_failed: int
    company_name: str | None
    email_found: bool
    phone_found: bool
    team_page_found: bool
    services_page_found: bool
    latest_content_date: str | None
    facts: dict[str, JsonValue]
    issues: tuple[str, ...]


@dataclass(slots=True)
class WebsiteAuditPipeline:
    crawler: Crawler
    repository: Repository
    max_pages_per_domain: int = 8
    user_agent: str = "USURALProspectFinder/0.1"
    minimum_domain_delay_seconds: float = 0.25

    async def run(self, domain: str) -> WebsiteAuditSummary:
        normalized_domain = canonical_domain(normalize_url(domain))
        homepage = await self._resolve_homepage(normalized_domain)
        website, business = self._ensure_entities(normalized_domain, homepage.final_url)
        audit = Audit(
            website_id=website.id,
            crawler_version=CRAWLER_VERSION,
            analyzer_version="none",
            configuration_hash=self._configuration_hash(),
            status=RunStatus.RUNNING,
        )
        self.repository.add_audit(audit)
        issues: list[str] = []
        pages: list[Page] = []
        contacts: dict[tuple[ContactType, str], Contact] = {}
        aggregate: dict[str, JsonValue] = {}
        company_name: str | None = None
        latest_dates: list[str] = []
        selected: list[LinkCandidate] = []
        try:
            home_page, home_evidence = self._persist_result(
                homepage, website, audit, PageType.HOMEPAGE, contacts
            )
            pages.append(home_page)
            if home_evidence is None:
                issues.append(homepage.error or "homepage unavailable")
                raise RuntimeError(issues[-1])
            company_name = self._probable_company_name(home_evidence.company_name)
            self._merge_facts(aggregate, home_evidence)
            latest_dates.extend(home_evidence.dates)
            robots = await self._robots(homepage.final_url or website.url)
            self._persist_signal(
                audit,
                website,
                None,
                "robots_txt_available",
                robots.available,
                SignalCategory.TECHNOLOGY,
                homepage.final_url,
                robots.error,
            )
            selected = select_pages(
                homepage.final_url or website.url,
                home_evidence.links,
                max(0, self.max_pages_per_domain - 1),
            )
            for candidate in selected:
                if not robots.allows(candidate.url, self.user_agent):
                    page = Page(
                        website_id=website.id,
                        audit_id=audit.id,
                        url=candidate.url,
                        requested_url=candidate.url,
                        final_url=candidate.url,
                        page_type=classify_page(candidate.url, candidate.text),
                        crawl_status=CrawlStatus.ROBOTS_BLOCKED,
                    )
                    self.repository.add_page(page)
                    pages.append(page)
                    issues.append(f"robots blocked {candidate.url}")
                    continue
                if self.minimum_domain_delay_seconds:
                    await asyncio.sleep(self.minimum_domain_delay_seconds)
                result = await self.crawler.fetch(candidate.url)
                page, evidence = self._persist_result(
                    result,
                    website,
                    audit,
                    classify_page(candidate.url, candidate.text),
                    contacts,
                )
                pages.append(page)
                if evidence:
                    company_name = company_name or self._probable_company_name(
                        evidence.company_name
                    )
                    self._merge_facts(aggregate, evidence)
                    latest_dates.extend(evidence.dates)
                else:
                    issues.append(result.error or f"failed: {candidate.url}")
            if company_name and company_name != business.name:
                self.repository.update_business(
                    replace(business, name=company_name, updated_at=utc_now())
                )
            completed = replace(audit, completed_at=utc_now(), status=RunStatus.COMPLETED)
        except Exception as exc:
            issues.append(str(exc))
            completed = replace(
                audit, completed_at=utc_now(), status=RunStatus.FAILED, notes=str(exc)
            )
        self.repository.update_audit(completed)
        successful = [page for page in pages if page.crawl_status is CrawlStatus.SUCCESS]
        emails = [
            contact
            for contact in contacts.values()
            if contact.type is ContactType.EMAIL
            and contact.classification
            not in {
                ContactClassification.INVALID,
                ContactClassification.PLACEHOLDER,
                ContactClassification.TECHNICAL,
            }
        ]
        phones = [contact for contact in contacts.values() if contact.type is ContactType.PHONE]
        return WebsiteAuditSummary(
            domain=normalized_domain,
            audit_id=audit.id,
            homepage_url=homepage.final_url,
            pages_selected=1 + len(selected),
            pages_fetched=len(successful),
            pages_failed=len(pages) - len(successful),
            company_name=company_name,
            email_found=bool(emails),
            phone_found=bool(phones),
            team_page_found=any(
                page.page_type is PageType.TEAM and page.crawl_status is CrawlStatus.SUCCESS
                for page in pages
            ),
            services_page_found=any(
                page.page_type is PageType.SERVICES and page.crawl_status is CrawlStatus.SUCCESS
                for page in pages
            ),
            latest_content_date=max(latest_dates, default=None),
            facts=aggregate,
            issues=tuple(dict.fromkeys(issues)),
        )

    async def _resolve_homepage(self, domain: str) -> CrawlResult:
        candidates = (
            f"https://{domain}/",
            f"https://www.{domain}/",
            f"http://{domain}/",
            f"http://www.{domain}/",
        )
        last: CrawlResult | None = None
        for candidate in candidates:
            result = await self.crawler.fetch(candidate)
            last = result
            if result.crawl_status is CrawlStatus.SUCCESS and result.html is not None:
                return result
        assert last is not None
        return last

    async def _robots(self, homepage_url: str) -> RobotsPolicy:
        parsed = urlsplit(homepage_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        result = await self.crawler.fetch(robots_url)
        if result.crawl_status is CrawlStatus.SUCCESS and result.html is not None:
            return RobotsPolicy.from_text(robots_url, result.html)
        return RobotsPolicy(error=result.error or "robots.txt unavailable")

    def _ensure_entities(self, domain: str, homepage_url: str | None) -> tuple[Website, Business]:
        existing = self.repository.get_website_by_domain(domain)
        if existing:
            business = self.repository.get_business(existing.business_id)
            if business is None:
                raise RuntimeError("website has no business")
            return existing, business
        business = Business(name=domain, category="unknown", location=Location("unknown"))
        website = Website(
            business_id=business.id,
            url=homepage_url or f"https://{domain}/",
            canonical_domain=domain,
            scheme=urlsplit(homepage_url or f"https://{domain}/").scheme,
        )
        business = replace(business, website_id=website.id)
        with self.repository.transaction() as transaction:
            transaction.add_business(business)
            transaction.add_website(website)
        return website, business

    def _persist_result(
        self,
        result: CrawlResult,
        website: Website,
        audit: Audit,
        page_type: PageType,
        contacts: dict[tuple[ContactType, str], Contact],
    ) -> tuple[Page, HtmlEvidence | None]:
        html = result.html if result.crawl_status is CrawlStatus.SUCCESS else None
        evidence: HtmlEvidence | None = None
        parse_status = result.crawl_status
        if html is not None and (result.content_type or "").startswith(
            ("text/html", "application/xhtml")
        ):
            try:
                evidence = extract_html(html, result.final_url or result.requested_url)
            except Exception:
                parse_status = CrawlStatus.PARSE_ERROR
        page = Page(
            website_id=website.id,
            audit_id=audit.id,
            url=result.final_url or result.requested_url,
            requested_url=result.requested_url,
            final_url=result.final_url,
            page_type=page_type,
            status_code=result.status_code,
            content_type=result.content_type,
            title=evidence.title if evidence else None,
            fetched_at=result.fetched_at,
            crawl_status=parse_status,
            elapsed_ms=result.elapsed_ms,
            content_length=len(result.html.encode()) if result.html else None,
            content_hash=hashlib.sha256(result.html.encode()).hexdigest() if result.html else None,
            language=evidence.language if evidence else None,
            redirect_chain=result.redirect_chain,
        )
        self.repository.add_page(page)
        if evidence:
            for name, value in evidence.facts.items():
                self._persist_signal(
                    audit, website, page, name, self._json(value), self._category(name), page.url
                )
            for schema_type in sorted(evidence.schema_types):
                self._persist_signal(
                    audit,
                    website,
                    page,
                    "structured_data_type",
                    schema_type,
                    SignalCategory.TECHNOLOGY,
                    page.url,
                )
            if evidence.dates:
                self._persist_signal(
                    audit,
                    website,
                    page,
                    "latest_visible_content_date",
                    max(evidence.dates),
                    SignalCategory.CONTENT_FRESHNESS,
                    page.url,
                    "content date only; not a redesign date",
                )
            extracted = list(evidence.contacts)
            if evidence.address:
                from ..crawling.extraction import ExtractedContact

                extracted.append(
                    ExtractedContact(
                        ContactType.ADDRESS,
                        evidence.address,
                        ContactClassification.GENERIC_BUSINESS,
                        0.9,
                    )
                )
            for item in extracted:
                if item.classification in {
                    ContactClassification.INVALID,
                    ContactClassification.PLACEHOLDER,
                    ContactClassification.TECHNICAL,
                }:
                    continue
                key = (item.type, item.value.casefold())
                if key in contacts and contacts[key].confidence >= item.confidence:
                    continue
                contact = Contact(
                    business_id=website.business_id,
                    website_id=website.id,
                    audit_id=audit.id,
                    type=item.type,
                    value=item.value,
                    source_url=page.url,
                    classification=item.classification,
                    confidence=item.confidence,
                )
                self.repository.add_contact(contact)
                contacts[key] = contact
        return page, evidence

    def _persist_signal(
        self,
        audit: Audit,
        website: Website,
        page: Page | None,
        name: str,
        value: JsonValue,
        category: SignalCategory,
        source_url: str | None,
        evidence: str | None = None,
    ) -> None:
        self.repository.add_signal(
            Signal(
                name=name,
                category=category,
                value=value,
                business_id=website.business_id,
                website_id=website.id,
                page_id=page.id if page else None,
                audit_id=audit.id,
                source_url=source_url,
                evidence=evidence,
            )
        )

    @staticmethod
    def _category(name: str) -> SignalCategory:
        if name in {"copyright_year"}:
            return SignalCategory.CONTENT_FRESHNESS
        if name.startswith("image_") or name.endswith("_ratio"):
            return SignalCategory.PERFORMANCE
        return SignalCategory.TECHNOLOGY

    @staticmethod
    def _json(value: object) -> JsonValue:
        if value is None or isinstance(value, bool | int | float | str):
            return value
        return str(value)

    @staticmethod
    def _merge_facts(target: dict[str, JsonValue], evidence: HtmlEvidence) -> None:
        for key, value in evidence.facts.items():
            if isinstance(value, bool):
                target[key] = bool(target.get(key, False)) or value
            elif isinstance(value, int | float):
                current = target.get(key, 0)
                current_number = float(current) if isinstance(current, int | float) else 0.0
                target[key] = max(current_number, float(value))
            elif value:
                target.setdefault(key, str(value))

    def _configuration_hash(self) -> str:
        raw = f"{self.max_pages_per_domain}:{self.minimum_domain_delay_seconds}:{self.user_agent}"
        return hashlib.sha256(raw.encode()).hexdigest()

    @staticmethod
    def _probable_company_name(value: str | None) -> str | None:
        if not value:
            return None
        folded = value.casefold()
        if any(token in folded for token in ("admin", "webmaster", "wordpress")):
            return None
        return value
