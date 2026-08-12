"""CSV prospect exporter."""

import csv
import json
from collections.abc import Iterable
from pathlib import Path

from .summaries import CSV_COLUMNS, ProspectSummary


def export_csv(prospects: Iterable[ProspectSummary], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(_csv_row(item) for item in prospects)


def _csv_row(item: ProspectSummary) -> dict[str, object]:
    return {
        key: ""
        if value is None
        else json.dumps(value, ensure_ascii=False, sort_keys=True)
        if isinstance(value, list | tuple | dict)
        else value
        for key, value in item.as_row().items()
    }
