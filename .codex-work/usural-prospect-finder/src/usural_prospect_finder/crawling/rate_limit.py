"""Rate-limit configuration."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RateLimitPolicy:
    global_concurrency: int = 10
    domain_concurrency: int = 2
    minimum_domain_delay_seconds: float = 0.0
