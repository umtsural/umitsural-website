"""Stable reporting projection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

CSV_COLUMNS = (
    "Company",
    "Website",
    "Domain",
    "Category",
    "Location",
    "Email",
    "Email Type",
    "Phone",
    "WordPress",
    "WordPress Confidence",
    "Detected Theme",
    "Detected Plugins",
    "Last Activity Date",
    "Last Update Estimate",
    "Outdated Score",
    "Outdated Confidence",
    "SEO Health Score",
    "SEO Gap Score",
    "SEO Confidence",
    "Business Quality Score",
    "Commercial Capacity Score",
    "Contactability Score",
    "Opportunity Score",
    "Opportunity Confidence",
    "Lead Quality",
    "Primary Opportunity",
    "Secondary Opportunity",
    "Reason",
    "Top Signals",
    "Notes",
    "Discovery Sources",
    "First Seen",
    "Last Audited",
)


@dataclass(frozen=True, slots=True)
class ProspectSummary:
    """Exporter-facing projection that can grow independently of persistence."""

    values: dict[str, Any]

    def as_row(self) -> dict[str, Any]:
        return {column: self.values.get(column, "") for column in CSV_COLUMNS}
