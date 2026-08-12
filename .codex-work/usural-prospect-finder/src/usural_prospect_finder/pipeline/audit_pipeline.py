"""Audit pipeline skeleton."""

from dataclasses import dataclass

from ..analyzers import AnalysisContext, Analyzer
from ..models import Signal
from ..storage import Repository


@dataclass(slots=True)
class AuditPipeline:
    analyzers: tuple[Analyzer, ...]
    repository: Repository

    async def analyze(self, context: AnalysisContext) -> list[Signal]:
        signals: list[Signal] = []
        for analyzer in self.analyzers:
            signals.extend(await analyzer.analyze(context))
        for signal in signals:
            self.repository.add_signal(signal)
        return signals
