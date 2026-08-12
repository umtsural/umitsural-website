"""Deterministic URL normalization and safety checks."""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

TRACKING_PARAMETERS = {"fbclid", "gclid", "mc_cid", "mc_eid"}
TRACKING_PREFIXES = ("utm_",)
ALLOWED_SCHEMES = {"http", "https"}


def normalize_url(value: str, *, default_scheme: str = "https") -> str:
    """Normalize a web URL while preserving path, port, and IDN host semantics."""
    raw = value.strip()
    if not raw:
        raise ValueError("URL cannot be empty")
    if "://" not in raw:
        raw = f"{default_scheme}://{raw}"
    parsed = urlsplit(raw)
    scheme = parsed.scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        raise ValueError(f"Unsupported URL scheme: {scheme}")
    if not parsed.hostname:
        raise ValueError("URL must contain a hostname")
    host = parsed.hostname.encode("idna").decode("ascii").lower()
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Invalid URL port") from exc
    default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    port_text = "" if port is None or default_port else f":{port}"
    userinfo = ""
    if parsed.username:
        userinfo = parsed.username
        if parsed.password:
            userinfo += f":{parsed.password}"
        userinfo += "@"
    path = parsed.path or "/"
    query_items = [
        (key, val)
        for key, val in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in TRACKING_PARAMETERS and not key.lower().startswith(TRACKING_PREFIXES)
    ]
    query = urlencode(query_items)
    return urlunsplit((scheme, f"{userinfo}{host}{port_text}", path, query, ""))


def safe_url_join(base: str, relative: str) -> str:
    """Join and normalize a URL, rejecting non-web schemes."""
    return normalize_url(urljoin(normalize_url(base), relative))


@dataclass(frozen=True, slots=True)
class UrlSafetyResult:
    is_safe: bool
    reason: str | None = None


def validate_url_safety(value: str) -> UrlSafetyResult:
    """Reject direct local/private targets without performing DNS resolution."""
    try:
        normalized = normalize_url(value)
    except ValueError as exc:
        return UrlSafetyResult(False, str(exc))
    hostname = urlsplit(normalized).hostname
    if hostname is None:
        return UrlSafetyResult(False, "missing hostname")
    host = hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith(".localhost"):
        return UrlSafetyResult(False, "localhost is not allowed")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return UrlSafetyResult(True)
    if not address.is_global:
        return UrlSafetyResult(False, "non-global IP addresses are not allowed")
    return UrlSafetyResult(True)
