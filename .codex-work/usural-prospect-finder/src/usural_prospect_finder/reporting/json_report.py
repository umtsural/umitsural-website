"""JSON prospect exporter."""

import json
from collections.abc import Iterable
from pathlib import Path

from .summaries import ProspectSummary


def export_json(prospects: Iterable[ProspectSummary], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    data = [item.as_row() for item in prospects]
    destination.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
