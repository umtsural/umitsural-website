"""Environment and YAML configuration loading."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .scoring.weights import validate_weights

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VALID_LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}


@dataclass(frozen=True, slots=True)
class Settings:
    environment: str = "development"
    database_path: Path = PROJECT_ROOT / "data/prospects.sqlite3"
    log_level: str = "INFO"
    output_dir: Path = PROJECT_ROOT / "output"
    cache_dir: Path = PROJECT_ROOT / "data/cache"
    log_dir: Path = PROJECT_ROOT / "logs"
    user_agent: str = "USURALProspectFinder/0.1"
    global_concurrency: int = 10
    domain_concurrency: int = 2
    request_timeout: float = 20.0
    max_pages_per_domain: int = 8
    max_redirects: int = 5
    max_response_bytes: int = 2_000_000
    minimum_domain_delay_seconds: float = 0.25
    search_api_key: str | None = None

    def __post_init__(self) -> None:
        if self.global_concurrency <= 0 or self.domain_concurrency <= 0:
            raise ValueError("concurrency values must be greater than zero")
        if self.request_timeout <= 0:
            raise ValueError("request timeout must be greater than zero")
        if self.log_level not in VALID_LOG_LEVELS:
            raise ValueError(f"invalid log level: {self.log_level}")

    @classmethod
    def from_env(cls) -> Settings:
        """Load settings from UPF-prefixed environment variables."""
        return cls(
            environment=os.getenv("UPF_ENV", "development"),
            database_path=_project_path(os.getenv("UPF_DATABASE_PATH", "data/prospects.sqlite3")),
            log_level=os.getenv("UPF_LOG_LEVEL", "INFO").upper(),
            output_dir=_project_path(os.getenv("UPF_OUTPUT_DIR", "output")),
            cache_dir=_project_path(os.getenv("UPF_CACHE_DIR", "data/cache")),
            log_dir=_project_path(os.getenv("UPF_LOG_DIR", "logs")),
            user_agent=os.getenv("UPF_USER_AGENT", "USURALProspectFinder/0.1"),
            global_concurrency=int(os.getenv("UPF_GLOBAL_CONCURRENCY", "10")),
            domain_concurrency=int(os.getenv("UPF_DOMAIN_CONCURRENCY", "2")),
            request_timeout=float(os.getenv("UPF_REQUEST_TIMEOUT", "20")),
            max_pages_per_domain=int(os.getenv("UPF_MAX_PAGES_PER_DOMAIN", "8")),
            max_redirects=int(os.getenv("UPF_MAX_REDIRECTS", "5")),
            max_response_bytes=int(os.getenv("UPF_MAX_RESPONSE_BYTES", "2000000")),
            minimum_domain_delay_seconds=float(
                os.getenv("UPF_MINIMUM_DOMAIN_DELAY_SECONDS", "0.25")
            ),
            search_api_key=os.getenv("UPF_SEARCH_API_KEY") or None,
        )


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML mapping, rejecting non-mapping roots."""
    try:
        with path.open(encoding="utf-8") as stream:
            value = yaml.safe_load(stream) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Expected a YAML mapping in {path}")
    return value


def load_scoring_config(path: Path | None = None) -> dict[str, Any]:
    """Load and validate the extensible scoring configuration."""
    config = load_yaml(path or PROJECT_ROOT / "config/scoring.yaml")
    required = {
        "version",
        "modernization_gap",
        "seo_gap",
        "business_quality",
        "commercial_capacity",
        "contactability",
        "opportunity",
    }
    missing = required - config.keys()
    if missing:
        raise ValueError(f"scoring config missing sections: {', '.join(sorted(missing))}")
    for section in required - {"version", "opportunity"}:
        maximum = config[section].get("max_score")
        if not isinstance(maximum, int | float) or isinstance(maximum, bool) or maximum <= 0:
            raise ValueError(f"{section}.max_score must be a positive number")
    weights = config["opportunity"].get("weights")
    if not isinstance(weights, dict) or any(
        not isinstance(value, int | float) or isinstance(value, bool) for value in weights.values()
    ):
        raise ValueError("opportunity.weights must contain numeric values")
    validate_weights({str(key): float(value) for key, value in weights.items()})
    return config


def load_category_config(path: Path | None = None) -> dict[str, Any]:
    """Load category profiles and validate fields required by future query generation."""
    config = load_yaml(path or PROJECT_ROOT / "config/categories.yaml")
    for key, profile in config.items():
        if not isinstance(profile, dict):
            raise ValueError(f"category {key} must be a mapping")
        labels = profile.get("labels")
        if profile.get("canonical_key") != key:
            raise ValueError(f"category {key} canonical_key must match its mapping key")
        if not isinstance(labels, dict) or not labels:
            raise ValueError(f"category {key} requires localized labels")
        if any(not isinstance(values, list) or not values for values in labels.values()):
            raise ValueError(f"category {key} labels must be non-empty lists")
        templates = profile.get("query_templates")
        if not isinstance(templates, list) or not templates:
            raise ValueError(f"category {key} requires query_templates")
        if any("{label}" not in item or "{location}" not in item for item in templates):
            raise ValueError(f"category {key} query templates require label and location fields")
        for section in ("quality_priorities", "opportunity_priorities"):
            if not isinstance(profile.get(section), dict):
                raise ValueError(f"category {key} requires {section}")
    return config


def _project_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path
