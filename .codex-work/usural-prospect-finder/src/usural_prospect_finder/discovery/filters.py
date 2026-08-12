"""Candidate filtering primitives."""

from collections.abc import Collection

from ..utils.domains import canonical_domain


def is_excluded(url: str, excluded_domains: Collection[str]) -> bool:
    """Return whether a URL matches a configured excluded domain."""
    domain = canonical_domain(url)
    return any(domain == item or domain.endswith(f".{item}") for item in excluded_domains)
