"""Stable company-domain deduplication with provenance preservation."""

from ..utils.domains import canonical_domain
from .base import BusinessCandidate, DiscoveryCandidate, DomainClassification


def deduplicate(candidates: list[DiscoveryCandidate]) -> list[DiscoveryCandidate]:
    """Keep the earliest candidate for each canonical domain."""
    found: dict[str, DiscoveryCandidate] = {}
    for candidate in candidates:
        found.setdefault(canonical_domain(candidate.url), candidate)
    return list(found.values())


def business_candidates(observations: list[DiscoveryCandidate]) -> list[BusinessCandidate]:
    """Build unique company views while retaining every contributing observation ID."""
    grouped: dict[str, list[DiscoveryCandidate]] = {}
    excluded_domains = {
        observation.canonical_domain
        for observation in observations
        if _high_confidence_platform(observation)
    }
    for observation in observations:
        if (
            observation.classification is DomainClassification.COMPANY
            and observation.canonical_domain not in excluded_domains
        ):
            grouped.setdefault(observation.canonical_domain, []).append(observation)
    return [
        BusinessCandidate(
            canonical_domain=domain,
            website=items[0].url,
            business_name=items[0].business_name,
            category=items[0].category,
            location=items[0].location,
            observation_ids=tuple(item.id for item in items),
        )
        for domain, items in grouped.items()
    ]


def _high_confidence_platform(observation: DiscoveryCandidate) -> bool:
    confidence = observation.metadata.get("classification_confidence")
    return (
        observation.classification
        in {
            DomainClassification.DIRECTORY,
            DomainClassification.RANKING,
            DomainClassification.NETWORK,
            DomainClassification.RECRUITMENT,
            DomainClassification.MARKETPLACE,
        }
        and isinstance(confidence, int | float)
        and not isinstance(confidence, bool)
        and confidence >= 0.88
    )
