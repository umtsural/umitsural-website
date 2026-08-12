"""Deterministic, configuration-driven localized query plans."""

from typing import Any

from .base import DiscoveryQuery, QueryPlan


def build_query_plan(category: str, location: str, profiles: dict[str, Any]) -> QueryPlan:
    """Build an ordered unique query plan entirely from category configuration."""
    category_key = category.strip().lower().replace(" ", "_")
    location_name = location.strip()
    if not location_name:
        raise ValueError("location cannot be empty")
    profile = profiles.get(category_key)
    if not isinstance(profile, dict):
        raise ValueError(f"unknown category: {category}")
    labels = profile["labels"]
    synonyms = profile.get("synonyms", {})
    templates = profile["query_templates"]
    queries: list[DiscoveryQuery] = []
    seen: set[str] = set()
    for locale, localized_labels in labels.items():
        terms = [*localized_labels, *synonyms.get(locale, [])]
        for term in terms:
            for template in templates:
                text = " ".join(template.format(label=term, location=location_name).split())
                folded = text.casefold()
                if folded not in seen:
                    seen.add(folded)
                    queries.append(DiscoveryQuery(text, locale, category_key, location_name))
    return QueryPlan(category_key, location_name, tuple(queries))
