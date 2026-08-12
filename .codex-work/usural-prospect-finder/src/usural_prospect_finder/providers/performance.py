"""Performance provider port and normalized result."""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PerformanceResult:
    url: str
    metrics: dict[str, float] = field(default_factory=dict)


class PerformanceProvider(Protocol):
    name: str

    async def measure(self, url: str) -> PerformanceResult: ...
