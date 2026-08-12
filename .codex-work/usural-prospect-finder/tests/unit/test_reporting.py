import csv
import json
from pathlib import Path

from usural_prospect_finder.reporting.csv_report import export_csv
from usural_prospect_finder.reporting.json_report import export_json
from usural_prospect_finder.reporting.summaries import CSV_COLUMNS, ProspectSummary


def test_csv_and_json_export(tmp_path: Path) -> None:
    rows = [
        ProspectSummary(
            {
                "Company": "Ümit, Estudi d'Arquitectura\nMünchen — São Paulo",
                "Domain": "example.com",
                "Detected Plugins": ["plugin-b", "plugin-a"],
                "Notes": None,
            }
        )
    ]
    csv_path, json_path = tmp_path / "report.csv", tmp_path / "report.json"
    export_csv(rows, csv_path)
    export_json(rows, json_path)
    with csv_path.open(encoding="utf-8-sig") as stream:
        csv_rows = list(csv.DictReader(stream))
    assert tuple(csv_rows[0]) == CSV_COLUMNS
    assert csv_rows[0]["Company"].startswith("Ümit,")
    assert csv_rows[0]["Detected Plugins"] == '["plugin-b", "plugin-a"]'
    assert csv_rows[0]["Notes"] == ""
    json_row = json.loads(json_path.read_text(encoding="utf-8"))[0]
    assert json_row["Domain"] == "example.com"
    assert json_row["Detected Plugins"] == ["plugin-b", "plugin-a"]
    assert json_row["Notes"] is None
