import pytest

from usural_prospect_finder.utils.domains import canonical_domain, extract_domain
from usural_prospect_finder.utils.urls import normalize_url, safe_url_join, validate_url_safety


def test_normalize_removes_tracking_fragment_and_default_port() -> None:
    assert (
        normalize_url("HTTPS://WWW.Example.COM:443/path?utm_source=x&a=1#part")
        == "https://www.example.com/path?a=1"
    )


def test_domain_normalization_handles_idn_and_www() -> None:
    assert extract_domain("https://münich.example/") == "xn--mnich-kva.example"
    assert canonical_domain("www.Example.com") == "example.com"


def test_safe_join_rejects_unsafe_scheme() -> None:
    with pytest.raises(ValueError):
        safe_url_join("https://example.com", "javascript:alert(1)")


@pytest.mark.parametrize(
    "url",
    [
        "localhost",
        "127.0.0.1",
        "10.0.0.1",
        "169.254.169.254",
        "[::1]",
        "file:///etc/passwd",
        "ftp://example.com",
        "data:text/plain,x",
    ],
)
def test_unsafe_urls_are_rejected(url: str) -> None:
    assert not validate_url_safety(url).is_safe


def test_public_url_is_safe_without_dns_lookup() -> None:
    assert validate_url_safety("https://example.com").is_safe
