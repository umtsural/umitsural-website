"""Multilingual deterministic internal page classification and selection."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from ..models import PageType
from ..utils.domains import canonical_domain
from ..utils.urls import normalize_url

PAGE_TERMS: dict[PageType, tuple[str, ...]] = {
    PageType.CONTACT: ("contact", "contacto", "contacte"),
    PageType.ABOUT: ("about", "firm", "nosotros", "quienes somos", "despatx", "bufete"),
    PageType.TEAM: (
        "team",
        "lawyers",
        "attorneys",
        "professionals",
        "partners",
        "our team",
        "equipo",
        "profesionales",
        "socios",
        "advocats",
        "equip",
        "socis",
    ),
    PageType.SERVICES: (
        "services",
        "practice",
        "practice areas",
        "expertise",
        "servicios",
        "áreas de práctica",
        "areas de practica",
        "àrees de pràctica",
        "arees de practica",
    ),
    PageType.PROJECTS: ("projects", "portfolio", "cases", "proyectos", "projectes"),
    PageType.NEWS: ("news", "noticias", "actualidad", "premsa"),
    PageType.BLOG: ("blog", "insights", "articles", "artículos", "articles"),
    PageType.LEGAL: ("legal", "imprint", "aviso legal", "legal notice"),
    PageType.PRIVACY: ("privacy", "privacidad", "privacitat", "cookies"),
}
PRIORITY = {
    PageType.CONTACT: 100,
    PageType.ABOUT: 90,
    PageType.TEAM: 85,
    PageType.SERVICES: 80,
    PageType.PROJECTS: 60,
    PageType.NEWS: 50,
    PageType.BLOG: 45,
    PageType.LEGAL: 30,
    PageType.PRIVACY: 20,
    PageType.OTHER: 0,
}


@dataclass(frozen=True, slots=True)
class LinkCandidate:
    url: str
    text: str = ""
    context: str = ""
    title: str = ""


def classify_page(url: str, text: str = "", context: str = "", title: str = "") -> PageType:
    raw_path = urlsplit(normalize_url(url)).path.casefold()
    path = raw_path.replace("-", " ").replace("_", " ")
    evidence = " ".join((path, text, context, title)).casefold()
    path_segments = {
        segment.replace("-", " ").replace("_", " ") for segment in raw_path.strip("/").split("/")
    }
    exact_team_terms = {
        "lawyers",
        "attorneys",
        "professionals",
        "partners",
        "abogados",
        "advocats",
        "socios",
        "socis",
    }
    matches: list[tuple[int, PageType]] = []
    for page_type, terms in PAGE_TERMS.items():
        matched = any(term in evidence for term in terms if term not in exact_team_terms)
        if page_type is PageType.TEAM:
            matched = matched or any(
                term in path_segments or text.strip().casefold() == term
                for term in exact_team_terms
            )
        if matched:
            matches.append((PRIORITY[page_type], page_type))
    return max(matches, default=(0, PageType.OTHER))[1]


def select_pages(homepage_url: str, links: list[LinkCandidate], limit: int) -> list[LinkCandidate]:
    home_domain = canonical_domain(homepage_url)
    seen: set[str] = set()
    ranked: list[tuple[int, int, LinkCandidate]] = []
    for index, link in enumerate(links):
        try:
            url = normalize_url(link.url)
        except ValueError:
            continue
        if canonical_domain(url) != home_domain or url in seen:
            continue
        seen.add(url)
        page_type = classify_page(url, link.text, link.context, link.title)
        if page_type is PageType.OTHER:
            continue
        ranked.append(
            (PRIORITY[page_type], -index, LinkCandidate(url, link.text, link.context, link.title))
        )
    ranked.sort(reverse=True, key=lambda item: (item[0], item[1]))
    selected: list[LinkCandidate] = []
    used_types: set[PageType] = set()
    for _, _, candidate in ranked:
        page_type = classify_page(candidate.url, candidate.text, candidate.context, candidate.title)
        if page_type in used_types:
            continue
        selected.append(candidate)
        used_types.add(page_type)
        if len(selected) >= limit:
            break
    return selected
