"""Pure signal-to-score contracts."""

from dataclasses import dataclass, field
from typing import Protocol

from ..models import Score, Signal


@dataclass(frozen=True, slots=True)
class ScoringContext:
    audit_id: str
    signals: tuple[Signal, ...]
    configuration: dict[str, object] = field(default_factory=dict)


class Scorer(Protocol):
    name: str
    version: str

    def score(self, context: ScoringContext) -> Score: ...


class EligibilityGate(Protocol):
    """Future composable opportunity eligibility rule."""

    def evaluate(self, context: ScoringContext) -> tuple[bool, str | None]: ...
