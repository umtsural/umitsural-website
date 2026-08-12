import asyncio
from pathlib import Path

import httpx

from usural_prospect_finder.crawling.extraction import extract_html
from usural_prospect_finder.crawling.http import AsyncHttpCrawler, validate_public_url
from usural_prospect_finder.crawling.page_selector import classify_page, select_pages
from usural_prospect_finder.crawling.robots import RobotsPolicy
from usural_prospect_finder.models import ContactClassification, CrawlStatus, PageType

FIXTURES = Path(__file__).parents[1] / "websites"


async def public_resolver(hostname: str) -> list[str]:
    del hostname
    return ["93.184.216.34"]


def fixture(name: str) -> str:
    return (FIXTURES / name / "index.html").read_text()


def test_multilingual_selective_page_classification_and_limits() -> None:
    parsed = extract_html(fixture("multilingual-law-firm"), "https://firm.example/")
    selected = select_pages("https://firm.example/", parsed.links, 2)
    assert len(selected) == 2
    assert classify_page("https://firm.example/equip") is PageType.TEAM
    assert classify_page("https://firm.example/arees-de-practica") is PageType.SERVICES
    assert classify_page("https://firm.example/article-about-lawyers") is not PageType.TEAM


def test_html_business_contact_social_structured_data_and_freshness() -> None:
    parsed = extract_html(fixture("modern-law-firm"), "https://modern-law.example/")
    assert parsed.company_name == "Modern Law"
    assert {"LegalService"} <= parsed.schema_types
    assert parsed.facts["viewport_meta_present"] is True
    assert parsed.facts["srcset_ratio"] == 1.0
    assert parsed.facts["lazy_loading_ratio"] == 1.0
    assert "2026-02-03" in parsed.dates
    assert any(contact.value == "info@modern-law.example" for contact in parsed.contacts)
    assert any(contact.value.startswith("https://linkedin.com/") for contact in parsed.contacts)


def test_legacy_technology_and_image_markup_are_objective_facts() -> None:
    parsed = extract_html(fixture("legacy-wordpress-law-firm"), "https://legacy.example/")
    assert parsed.facts["wordpress_asset_path_detected"] is True
    assert parsed.facts["jquery_detected"] is True
    assert parsed.facts["jquery_migrate_detected"] is True
    assert parsed.facts["slider_reference"] is True
    assert parsed.facts["large_declared_image_count"] == 1
    assert parsed.facts["copyright_year"] == 2026


def test_email_rejection_social_share_rejection_phone_and_js_shell() -> None:
    parsed = extract_html(fixture("contact-page"), "https://firm.example/contact")
    classifications = {contact.value: contact.classification for contact in parsed.contacts}
    assert classifications["test@test.com"] is ContactClassification.PLACEHOLDER
    assert classifications["webmaster@vendor.example"] is ContactClassification.TECHNICAL
    assert not any("sharer" in contact.value for contact in parsed.contacts)
    assert any(contact.value == "+34931234567" for contact in parsed.contacts)
    shell = extract_html(fixture("js-heavy-shell"), "https://app.example/")
    assert shell.facts["possible_js_rendered_site"] is True


def test_robots_policy_blocks_disallowed_path() -> None:
    text = (FIXTURES / "robots-blocked" / "robots.txt").read_text()
    policy = RobotsPolicy.from_text("https://firm.example/robots.txt", text)
    assert policy.allows("https://firm.example/contact", "USURAL")
    assert not policy.allows("https://firm.example/private", "USURAL")


def test_dns_private_ip_is_rejected() -> None:
    async def private_resolver(hostname: str) -> list[str]:
        del hostname
        return ["127.0.0.1"]

    try:
        asyncio.run(validate_public_url("https://public.example/", private_resolver))
    except ValueError as exc:
        assert "non-public" in str(exc)
    else:
        raise AssertionError("private DNS resolution was accepted")


def test_http_redirect_homepage_resolution_and_content_type() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/":
            return httpx.Response(301, headers={"location": "/en/"})
        return httpx.Response(
            200, headers={"content-type": "text/html"}, text="<title>Firm</title>"
        )

    crawler = AsyncHttpCrawler(transport=httpx.MockTransport(handler), resolver=public_resolver)
    result = asyncio.run(crawler.fetch("http://firm.example/"))
    assert result.crawl_status is CrawlStatus.SUCCESS
    assert result.final_url == "http://firm.example/en/"
    assert result.redirect_chain == ("http://firm.example/en/",)


def test_response_size_limit_and_unsupported_content() -> None:
    large = AsyncHttpCrawler(
        max_response_bytes=4,
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                200, headers={"content-type": "text/html"}, content=b"12345"
            )
        ),
        resolver=public_resolver,
    )
    assert asyncio.run(large.fetch("https://firm.example/")).crawl_status is CrawlStatus.TOO_LARGE
    pdf = AsyncHttpCrawler(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                200, headers={"content-type": "application/pdf"}, content=b"pdf"
            )
        ),
        resolver=public_resolver,
    )
    assert (
        asyncio.run(pdf.fetch("https://firm.example/file")).crawl_status
        is CrawlStatus.UNSUPPORTED_CONTENT
    )
