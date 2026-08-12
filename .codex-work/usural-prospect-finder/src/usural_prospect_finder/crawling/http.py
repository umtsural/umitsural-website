"""Bounded asynchronous static HTTP crawler with redirect SSRF protection."""

from __future__ import annotations

import asyncio
import socket
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from time import monotonic
from urllib.parse import urljoin, urlsplit

import httpx
import structlog

from ..models.common import utc_now
from ..models.page import CrawlStatus
from ..utils.retry import RetryPolicy, retry_async
from ..utils.urls import normalize_url, validate_url_safety
from .base import CrawlResult

Resolver = Callable[[str], Awaitable[list[str]]]
logger = structlog.get_logger(__name__)


async def resolve_host_addresses(hostname: str) -> list[str]:
    loop = asyncio.get_running_loop()
    records = await loop.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    return sorted({str(record[4][0]) for record in records})


async def validate_public_url(url: str, resolver: Resolver = resolve_host_addresses) -> None:
    direct = validate_url_safety(url)
    if not direct.is_safe:
        raise UnsafeUrlError(direct.reason or "unsafe URL")
    hostname = urlsplit(normalize_url(url)).hostname
    if hostname is None:
        raise UnsafeUrlError("missing hostname")
    for address in await resolver(hostname):
        result = validate_url_safety(
            f"https://[{address}]" if ":" in address else f"https://{address}"
        )
        if not result.is_safe:
            raise UnsafeUrlError(f"DNS resolved to a non-public address: {address}")


class UnsafeUrlError(ValueError):
    pass


class ResponseTooLargeError(ValueError):
    pass


@dataclass(slots=True)
class AsyncHttpCrawler:
    timeout: float = 20.0
    max_redirects: int = 5
    max_response_bytes: int = 2_000_000
    user_agent: str = "USURALProspectFinder/0.1"
    global_concurrency: int = 10
    resolver: Resolver = resolve_host_addresses
    transport: httpx.AsyncBaseTransport | None = None
    retry_policy: RetryPolicy = field(
        default_factory=lambda: RetryPolicy(maximum_attempts=2, initial_delay_seconds=0.25)
    )
    _semaphore: asyncio.Semaphore = field(init=False)

    def __post_init__(self) -> None:
        self._semaphore = asyncio.Semaphore(self.global_concurrency)

    async def fetch(self, url: str) -> CrawlResult:
        started = monotonic()
        requested = normalize_url(url)
        logger.info("crawl.fetch.started", url=requested)
        try:
            async with self._semaphore:
                result = await retry_async(
                    lambda: self._fetch_once(requested, started),
                    self.retry_policy,
                    retryable=lambda exc: isinstance(
                        exc, (httpx.TimeoutException, httpx.TransportError)
                    ),
                )
                logger.info(
                    "crawl.fetch.completed",
                    url=requested,
                    final_url=result.final_url,
                    status_code=result.status_code,
                    crawl_status=result.crawl_status,
                    elapsed_ms=result.elapsed_ms,
                )
                return result
        except UnsafeUrlError as exc:
            return self._error(requested, started, CrawlStatus.UNSAFE_URL, str(exc))
        except ResponseTooLargeError as exc:
            return self._error(requested, started, CrawlStatus.TOO_LARGE, str(exc))
        except httpx.TimeoutException as exc:
            return self._error(requested, started, CrawlStatus.TIMEOUT, str(exc))
        except (httpx.TooManyRedirects, ValueError) as exc:
            return self._error(requested, started, CrawlStatus.REDIRECT_ERROR, str(exc))
        except httpx.HTTPError as exc:
            return self._error(requested, started, CrawlStatus.HTTP_ERROR, str(exc))

    async def _fetch_once(self, requested: str, started: float) -> CrawlResult:
        current = requested
        redirects: list[str] = []
        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=False,
            transport=self.transport,
            headers={"User-Agent": self.user_agent, "Accept": "text/html,application/xhtml+xml"},
        ) as client:
            for _ in range(self.max_redirects + 1):
                await validate_public_url(current, self.resolver)
                async with client.stream("GET", current) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        if not location:
                            raise ValueError("redirect response omitted Location")
                        current = normalize_url(urljoin(current, location))
                        redirects.append(current)
                        continue
                    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                    if content_type not in {"text/html", "application/xhtml+xml", "text/plain"}:
                        return CrawlResult(
                            requested,
                            current,
                            response.status_code,
                            dict(response.headers),
                            content_type=content_type,
                            elapsed_ms=(monotonic() - started) * 1000,
                            crawl_status=CrawlStatus.UNSUPPORTED_CONTENT,
                            error="unsupported content type",
                            redirect_chain=tuple(redirects),
                        )
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > self.max_response_bytes:
                            raise ResponseTooLargeError("response exceeded configured byte limit")
                    status = (
                        CrawlStatus.SUCCESS
                        if 200 <= response.status_code < 300
                        else CrawlStatus.HTTP_ERROR
                    )
                    return CrawlResult(
                        requested_url=requested,
                        final_url=current,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        html=body.decode(response.encoding or "utf-8", "replace"),
                        content_type=content_type,
                        elapsed_ms=(monotonic() - started) * 1000,
                        fetched_at=utc_now(),
                        crawl_status=status,
                        error=None
                        if status is CrawlStatus.SUCCESS
                        else f"HTTP {response.status_code}",
                        redirect_chain=tuple(redirects),
                    )
            raise httpx.TooManyRedirects("maximum redirects exceeded")

    @staticmethod
    def _error(url: str, started: float, status: CrawlStatus, message: str) -> CrawlResult:
        logger.warning("crawl.fetch.failed", url=url, crawl_status=status, error=message)
        return CrawlResult(
            requested_url=url,
            elapsed_ms=(monotonic() - started) * 1000,
            crawl_status=status,
            error=message,
        )
