"""Explainable search-result domain classification without page fetching."""

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import urlsplit

from ..providers.search import SearchResult
from ..utils.domains import canonical_domain
from ..utils.urls import normalize_url
from .base import DomainClassification

DOCUMENT_SUFFIXES = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"}
SIGNAL_TERMS = {
    DomainClassification.DIRECTORY: {
        "lawyer directory",
        "attorney directory",
        "law firm directory",
        "legal directory",
        "find a lawyer",
        "find an attorney",
        "recommended lawyers",
        "member directory",
        "directory",
        "a directory of",
        "yellow pages",
        "thousands of lawyers",
        "detailed profiles",
        "curated list",
    },
    DomainClassification.RANKING: {
        "best lawyers",
        "best law firms",
        "rankings",
        "ranked firms",
        "top lawyers",
        "top law firms",
        "rankings guide",
        "legal rankings",
        "global rankings",
        "leading lawyers",
        "law firm rankings",
        "research and rankings",
        "editorial rankings",
        "ranking de",
        "mejor valorados",
    },
    DomainClassification.NETWORK: {
        "global network",
        "international network",
        "lawyer network",
        "law firm network",
        "member firms",
        "find a member",
        "referral network",
        "lawyers worldwide",
    },
    DomainClassification.RECRUITMENT: {
        "legal recruitment",
        "legal recruiter",
        "attorney jobs",
        "law firm jobs",
        "legal careers",
        "legal search firm",
        "recruiter",
        "executive search",
    },
    DomainClassification.MARKETPLACE: {
        "compare lawyers",
        "request quotes",
        "get matched",
        "lawyer marketplace",
        "legal marketplace",
        "find legal help",
        "hire a lawyer",
        "our platform",
        "en nuestra plataforma",
        "puedes encontrar",
    },
    DomainClassification.EDITORIAL: {
        "legal analysis",
        "industry guide",
        "legal intelligence",
    },
    DomainClassification.NEWS: {"legal news", "newspaper", "news magazine"},
}
BLOG_TERMS = {"blog", "article", "author archive"}
AMBIGUOUS_SINGLE_TERMS = {"directory", "rankings", "recruiter"}
HIGH_CONFIDENCE_TERMS = {
    "a directory of",
    "best lawyers",
    "best law firms",
    "lawyer directory",
    "attorney directory",
    "law firm directory",
    "legal directory",
    "find a lawyer",
    "find an attorney",
    "member firms",
    "referral network",
    "legal recruitment",
    "attorney jobs",
    "law firm jobs",
    "executive search",
    "compare lawyers",
    "get matched",
    "lawyer marketplace",
    "legal marketplace",
    "our platform",
    "en nuestra plataforma",
    "ranking de",
    "mejor valorados",
}


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    classification: DomainClassification
    confidence: float
    reasons: tuple[str, ...]

    @property
    def reason(self) -> str:
        return "; ".join(self.reasons)


def classify_result(
    result: SearchResult,
    exclusions: dict[str, Any],
    category_hints: dict[str, Any] | None = None,
) -> ClassificationResult:
    """Classify using known domains, hostname/path, title/snippet and provider metadata."""
    normalized_url = normalize_url(result.url)
    domain = canonical_domain(normalized_url)
    parsed = urlsplit(normalized_url)
    path = parsed.path.lower()
    text = f"{result.title} {result.snippet or ''}".casefold()
    provider_type = str(result.metadata.get("type", "")).casefold()
    known_mapping = {
        "social": DomainClassification.SOCIAL,
        "directories": DomainClassification.DIRECTORY,
        "rankings": DomainClassification.RANKING,
        "networks": DomainClassification.NETWORK,
        "recruitment": DomainClassification.RECRUITMENT,
        "government": DomainClassification.GOVERNMENT,
        "marketplaces": DomainClassification.MARKETPLACE,
        "news": DomainClassification.NEWS,
        "editorial": DomainClassification.EDITORIAL,
    }
    for group, classification in known_mapping.items():
        if any(domain == item or domain.endswith(f".{item}") for item in exclusions.get(group, [])):
            return ClassificationResult(classification, 0.99, (f"known {group} domain",))
    if domain.endswith((".gov", ".gov.es", ".gob.es")) or provider_type == "government":
        return ClassificationResult(
            DomainClassification.GOVERNMENT, 0.98, ("government hostname or metadata",)
        )
    if PurePosixPath(path).suffix in DOCUMENT_SUFFIXES:
        return ClassificationResult(DomainClassification.UNKNOWN, 0.99, ("document result",))

    evidence: dict[DomainClassification, list[str]] = {}
    for classification, terms in SIGNAL_TERMS.items():
        matches = sorted(term for term in terms if term in text or term in domain)
        if matches:
            evidence[classification] = [f'text or hostname contains "{term}"' for term in matches]
    if "profile" in path.split("/"):
        evidence.setdefault(DomainClassification.DIRECTORY, []).append(
            'path contains directory segment "profile"'
        )
    if provider_type in {"news", "directory", "marketplace"}:
        mapped = DomainClassification(provider_type)
        evidence.setdefault(mapped, []).append(f'provider metadata type is "{provider_type}"')
    weak_platform_reasons: list[str] = []
    if evidence:
        classification, reasons = max(
            evidence.items(), key=lambda item: (len(item[1]), _signal_priority(item[0]))
        )
        only_term = reasons[0].removeprefix('text or hostname contains "').removesuffix('"')
        if len(reasons) > 1 or only_term not in AMBIGUOUS_SINGLE_TERMS:
            matched_terms = {
                reason.removeprefix('text or hostname contains "').removesuffix('"')
                for reason in reasons
            }
            base = 0.88 if matched_terms & HIGH_CONFIDENCE_TERMS else 0.72
            confidence = min(0.96, base + 0.08 * (len(reasons) - 1))
            return ClassificationResult(classification, confidence, tuple(reasons))
        weak_platform_reasons = reasons

    if any(segment in path.split("/") for segment in BLOG_TERMS) or provider_type == "blog":
        return ClassificationResult(DomainClassification.UNKNOWN, 0.85, ("blog or article result",))

    hints = category_hints or {}
    company_terms = {str(term).casefold() for term in hints.get("company_terms", [])}
    domain_terms = {str(term).casefold() for term in hints.get("company_domain_terms", [])}
    path_terms = {str(term).casefold() for term in hints.get("company_path_terms", [])}
    matched_company_terms = sorted(term for term in company_terms if term in text)
    matched_domain_terms = sorted(term for term in domain_terms if term in domain)
    matched_path_terms = sorted(term for term in path_terms if term in path)
    company_reasons = [
        f'text contains category company term "{term}"' for term in matched_company_terms
    ]
    company_reasons.extend(
        f'hostname contains category company term "{term}"' for term in matched_domain_terms
    )
    company_reasons.extend(
        f'path contains category company term "{term}"' for term in matched_path_terms
    )
    if company_reasons and result.title.strip() and parsed.scheme in {"http", "https"}:
        company_reasons.append("result has a titled public website")
        confidence = min(0.94, 0.72 + 0.06 * len(company_reasons))
        return ClassificationResult(
            DomainClassification.COMPANY, confidence, tuple(company_reasons)
        )
    if not hints and result.title.strip() and parsed.scheme in {"http", "https"}:
        return ClassificationResult(
            DomainClassification.COMPANY, 0.60, ("eligible web domain with business title",)
        )
    return ClassificationResult(
        DomainClassification.UNKNOWN,
        0.55,
        (*weak_platform_reasons, "insufficient category-specific company evidence"),
    )


def _signal_priority(classification: DomainClassification) -> int:
    order = (
        DomainClassification.RANKING,
        DomainClassification.RECRUITMENT,
        DomainClassification.NETWORK,
        DomainClassification.MARKETPLACE,
        DomainClassification.DIRECTORY,
        DomainClassification.EDITORIAL,
        DomainClassification.NEWS,
    )
    return len(order) - order.index(classification)
