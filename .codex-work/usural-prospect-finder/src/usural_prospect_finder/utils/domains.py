"""Domain extraction and comparison utilities."""

from urllib.parse import urlsplit

from .urls import normalize_url


def extract_domain(value: str) -> str:
    """Extract the lowercase ASCII hostname, retaining no port."""
    hostname = urlsplit(normalize_url(value)).hostname
    if hostname is None:
        raise ValueError("URL has no domain")
    return hostname.encode("idna").decode("ascii").lower().rstrip(".")


def canonical_domain(value: str) -> str:
    """Return a comparison domain with one leading www label removed."""
    domain = extract_domain(value)
    return domain[4:] if domain.startswith("www.") else domain
