from .base import EligibilityGate
from .outdated import ModernizationGapScorer


class OpportunityScorer(ModernizationGapScorer):
    name = "opportunity"

    def __init__(self, gates: tuple[EligibilityGate, ...] = ()) -> None:
        self.gates = gates
