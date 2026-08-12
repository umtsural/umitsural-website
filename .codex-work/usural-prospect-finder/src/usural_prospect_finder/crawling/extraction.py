"""Objective HTML, business, contact, and technology evidence extraction."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from ..models import ContactClassification, ContactType
from .page_selector import LinkCandidate

EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d .()/-]{7,}\d)")
DATE_RE = re.compile(r"\b(20\d{2})[-/.](0?[1-9]|1[0-2])[-/.]([0-2]?\d|3[01])\b")
MONTH_DATE_RE = re.compile(
    r"(?i)\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+([0-2]?\d|3[01]),?\s+(20\d{2})\b"
)
MONTHS = {
    name.casefold(): index
    for index, name in enumerate(
        [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ],
        1,
    )
}
COPYRIGHT_RE = re.compile(r"(?i)(?:©|copyright)\s*(20\d{2})")
PLACEHOLDER_EMAILS = {"example@example.com", "test@test.com", "name@example.com"}
SOCIAL_HOSTS = {
    "linkedin.com": "linkedin",
    "instagram.com": "instagram",
    "facebook.com": "facebook",
    "youtube.com": "youtube",
    "x.com": "x",
    "twitter.com": "x",
    "tiktok.com": "tiktok",
}


@dataclass(frozen=True, slots=True)
class ExtractedContact:
    type: ContactType
    value: str
    classification: ContactClassification
    confidence: float


@dataclass(slots=True)
class HtmlEvidence:
    title: str | None = None
    language: str | None = None
    company_name: str | None = None
    address: str | None = None
    links: list[LinkCandidate] = field(default_factory=list)
    contacts: list[ExtractedContact] = field(default_factory=list)
    facts: dict[str, object] = field(default_factory=dict)
    schema_types: set[str] = field(default_factory=set)
    dates: list[str] = field(default_factory=list)


class EvidenceParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.result = HtmlEvidence(
            facts={
                "doctype_present": False,
                "viewport_meta_present": False,
                "charset_present": False,
                "canonical_present": False,
                "stylesheet_count": 0,
                "script_count": 0,
                "module_script_count": 0,
                "inline_script_count": 0,
                "inline_style_count": 0,
                "preload_count": 0,
                "preconnect_count": 0,
                "dns_prefetch_count": 0,
                "image_total": 0,
                "image_dimensions_count": 0,
                "image_srcset_count": 0,
                "image_sizes_count": 0,
                "image_lazy_count": 0,
                "image_modern_format_count": 0,
                "image_missing_alt_count": 0,
                "large_declared_image_count": 0,
                "wordpress_asset_path_detected": False,
                "theme_asset_path_detected": False,
                "plugin_asset_path_detected": False,
                "jquery_detected": False,
                "jquery_migrate_detected": False,
                "fontawesome_reference": False,
                "slider_reference": False,
                "page_builder_reference": False,
                "possible_js_rendered_site": False,
                "hreflang_count": 0,
            }
        )
        self._title = False
        self._script_type: str | None = None
        self._script_text: list[str] = []
        self._anchor_url: str | None = None
        self._anchor_text: list[str] = []
        self._texts: list[str] = []

    def handle_decl(self, decl: str) -> None:
        if decl.casefold().startswith("doctype html"):
            self.result.facts["doctype_present"] = True

    def _count(self, key: str) -> int:
        value = self.result.facts.get(key, 0)
        return value if isinstance(value, int) and not isinstance(value, bool) else 0

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = {key.casefold(): value or "" for key, value in attrs_list}
        if tag == "html":
            self.result.language = attrs.get("lang") or None
        elif tag == "title":
            self._title = True
        elif tag == "meta":
            name = attrs.get("name", "").casefold()
            prop = attrs.get("property", "").casefold()
            if name == "viewport":
                self.result.facts["viewport_meta_present"] = True
            if "charset" in attrs:
                self.result.facts["charset_present"] = True
            if name == "generator":
                self.result.facts["generator_meta"] = attrs.get("content", "")
            if prop == "og:site_name" and attrs.get("content"):
                self.result.company_name = attrs["content"].strip()
            if name in {
                "date",
                "datepublished",
                "datemodified",
                "article:published_time",
            } and attrs.get("content"):
                self.result.dates.append(attrs["content"][:10])
        elif tag == "link":
            rel = attrs.get("rel", "").casefold()
            href = attrs.get("href", "")
            if "stylesheet" in rel:
                self.result.facts["stylesheet_count"] = self._count("stylesheet_count") + 1
            if "canonical" in rel:
                self.result.facts["canonical_present"] = True
            if "alternate" in rel and attrs.get("hreflang"):
                self.result.facts["hreflang_count"] = self._count("hreflang_count") + 1
            for relation in ("preload", "preconnect", "dns-prefetch"):
                if relation in rel:
                    key = relation.replace("-", "_") + "_count"
                    self.result.facts[key] = self._count(key) + 1
            self._asset_flags(href)
        elif tag == "script":
            self.result.facts["script_count"] = self._count("script_count") + 1
            self._script_type = attrs.get("type", "").casefold()
            self._script_text = []
            if attrs.get("type", "").casefold() == "module":
                self.result.facts["module_script_count"] = self._count("module_script_count") + 1
            if not attrs.get("src"):
                self.result.facts["inline_script_count"] = self._count("inline_script_count") + 1
            self._asset_flags(attrs.get("src", ""))
        elif tag == "style":
            self.result.facts["inline_style_count"] = self._count("inline_style_count") + 1
        elif tag == "a" and attrs.get("href"):
            href = attrs["href"].strip()
            self._anchor_url = urljoin(self.base_url, href)
            self._anchor_text = []
            if href.casefold().startswith("mailto:"):
                self._add_email(href[7:].split("?", 1)[0], 0.98)
            elif href.casefold().startswith("tel:"):
                self.result.contacts.append(
                    ExtractedContact(
                        ContactType.PHONE, href[4:].strip(), ContactClassification.UNKNOWN, 0.98
                    )
                )
            else:
                self._add_social(self._anchor_url)
        elif tag == "img":
            self._image(attrs)
        elif tag == "time" and attrs.get("datetime"):
            self.result.dates.append(attrs["datetime"][:10])

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._title = False
        elif tag == "a" and self._anchor_url:
            self.result.links.append(
                LinkCandidate(self._anchor_url, " ".join(self._anchor_text).strip())
            )
            self._anchor_url = None
        elif tag == "script":
            if "ld+json" in (self._script_type or ""):
                self._parse_jsonld("".join(self._script_text))
            self._script_type = None

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if not text:
            return
        self._texts.append(text)
        if self._title:
            self.result.title = ((self.result.title or "") + " " + text).strip()
        if self._anchor_url:
            self._anchor_text.append(text)
        if self._script_type is not None:
            self._script_text.append(data)

    def finish(self) -> HtmlEvidence:
        visible = " ".join(self._texts)
        for email in EMAIL_RE.findall(visible):
            self._add_email(email, 0.72)
        for phone in PHONE_RE.findall(visible):
            self.result.contacts.append(
                ExtractedContact(
                    ContactType.PHONE, phone.strip(), ContactClassification.UNKNOWN, 0.65
                )
            )
        self.result.dates = sorted(
            {"-".join((y, m.zfill(2), d.zfill(2))) for y, m, d in DATE_RE.findall(visible)}
        )
        for match in MONTH_DATE_RE.finditer(visible):
            month_name = match.group(0).split()[0].casefold()
            day = int(match.group(1))
            year = int(match.group(2))
            self.result.dates.append(f"{year:04d}-{MONTHS[month_name]:02d}-{day:02d}")
        self.result.dates = sorted(set(self.result.dates))
        years = [int(value) for value in COPYRIGHT_RE.findall(visible)]
        if years:
            self.result.facts["copyright_year"] = max(years)
        scripts = self._count("script_count")
        if scripts >= 3 and len(visible) < 200:
            self.result.facts["possible_js_rendered_site"] = True
        images = self._count("image_total")
        if images:
            self.result.facts["srcset_ratio"] = round(self._count("image_srcset_count") / images, 3)
            self.result.facts["lazy_loading_ratio"] = round(
                self._count("image_lazy_count") / images, 3
            )
        return self.result

    def _asset_flags(self, value: str) -> None:
        lowered = value.casefold()
        checks = {
            "wordpress_asset_path_detected": "wp-content",
            "theme_asset_path_detected": "/themes/",
            "plugin_asset_path_detected": "/plugins/",
            "jquery_migrate_detected": "jquery-migrate",
            "jquery_detected": "jquery",
            "fontawesome_reference": "font-awesome",
            "slider_reference": "slider",
            "page_builder_reference": "elementor",
        }
        for key, token in checks.items():
            if token in lowered:
                self.result.facts[key] = True
        if any(token in lowered for token in ("wpbakery", "visual-composer", "revslider")):
            self.result.facts["page_builder_reference"] = True

    def _image(self, attrs: dict[str, str]) -> None:
        facts = self.result.facts
        facts["image_total"] = self._count("image_total") + 1
        if attrs.get("width") and attrs.get("height"):
            facts["image_dimensions_count"] = self._count("image_dimensions_count") + 1
            try:
                if int(attrs["width"]) * int(attrs["height"]) > 4_000_000:
                    facts["large_declared_image_count"] = (
                        self._count("large_declared_image_count") + 1
                    )
            except ValueError:
                pass
        if attrs.get("srcset"):
            facts["image_srcset_count"] = self._count("image_srcset_count") + 1
        if attrs.get("sizes"):
            facts["image_sizes_count"] = self._count("image_sizes_count") + 1
        if attrs.get("loading", "").casefold() == "lazy":
            facts["image_lazy_count"] = self._count("image_lazy_count") + 1
        if not attrs.get("alt"):
            facts["image_missing_alt_count"] = self._count("image_missing_alt_count") + 1
        if any(
            ext in (attrs.get("src", "") + attrs.get("srcset", "")).casefold()
            for ext in (".webp", ".avif")
        ):
            facts["image_modern_format_count"] = self._count("image_modern_format_count") + 1

    def _add_email(self, value: str, confidence: float) -> None:
        email = value.strip().casefold()
        local = email.split("@", 1)[0] if "@" in email else ""
        if email in PLACEHOLDER_EMAILS or local in {"example", "test"}:
            classification = ContactClassification.PLACEHOLDER
        elif not EMAIL_RE.fullmatch(email):
            classification = ContactClassification.INVALID
        elif local in {"webmaster", "admin", "developer", "dev"}:
            classification = ContactClassification.TECHNICAL
        elif local in {"info", "contact", "contacto", "hola", "office"}:
            classification = ContactClassification.GENERIC_BUSINESS
        elif local in {"support", "soporte"}:
            classification = ContactClassification.SUPPORT
        elif local in {"marketing", "press", "prensa"}:
            classification = ContactClassification.MARKETING
        elif "." in local:
            classification = ContactClassification.PERSONAL_BUSINESS
        else:
            classification = ContactClassification.UNKNOWN
        self.result.contacts.append(
            ExtractedContact(ContactType.EMAIL, email, classification, confidence)
        )

    def _add_social(self, url: str) -> None:
        host = (urlsplit(url).hostname or "").removeprefix("www.").casefold()
        if any(host == social or host.endswith("." + social) for social in SOCIAL_HOSTS):
            path = urlsplit(url).path.casefold()
            if not any(token in path for token in ("/share", "/sharer", "/intent")):
                self.result.contacts.append(
                    ExtractedContact(ContactType.SOCIAL, url, ContactClassification.UNKNOWN, 0.9)
                )

    def _parse_jsonld(self, raw: str) -> None:
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return
        nodes = payload if isinstance(payload, list) else [payload]
        for node in nodes:
            if not isinstance(node, dict):
                continue
            graph = node.get("@graph")
            if isinstance(graph, list):
                nodes.extend(item for item in graph if isinstance(item, dict))
            types = node.get("@type", [])
            for item in (
                [types] if isinstance(types, str) else types if isinstance(types, list) else []
            ):
                self.result.schema_types.add(str(item))
            if isinstance(node.get("name"), str) and any(
                t in self.result.schema_types
                for t in ("Organization", "LocalBusiness", "LegalService", "ProfessionalService")
            ):
                self.result.company_name = node["name"].strip()
            for key in ("email", "telephone"):
                if isinstance(node.get(key), str):
                    if key == "email":
                        self._add_email(node[key].removeprefix("mailto:"), 0.96)
                    else:
                        self.result.contacts.append(
                            ExtractedContact(
                                ContactType.PHONE, node[key], ContactClassification.UNKNOWN, 0.96
                            )
                        )
            if isinstance(node.get("address"), str):
                self.result.address = node["address"]
            elif isinstance(node.get("address"), dict):
                self.result.address = ", ".join(
                    str(node["address"].get(k))
                    for k in ("streetAddress", "postalCode", "addressLocality", "addressCountry")
                    if node["address"].get(k)
                )
            for key in ("datePublished", "dateModified"):
                if isinstance(node.get(key), str):
                    self.result.dates.append(node[key][:10])


def extract_html(html: str, base_url: str) -> HtmlEvidence:
    parser = EvidenceParser(base_url)
    parser.feed(html)
    parser.close()
    return parser.finish()
