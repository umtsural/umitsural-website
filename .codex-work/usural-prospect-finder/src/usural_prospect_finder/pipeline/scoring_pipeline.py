"""Pure scoring pipeline skeleton."""

from dataclasses import dataclass

from ..models import Score
from ..scoring import Scorer, ScoringContext
from ..storage import Repository


@dataclass(slots=True)
class ScoringPipeline:
    scorers: tuple[Scorer, ...]
    repository: Repository

    def run(self, context: ScoringContext) -> list[Score]:
        scores = [scorer.score(context) for scorer in self.scorers]
        for score in scores:
            self.repository.add_score(score)
        return scores
