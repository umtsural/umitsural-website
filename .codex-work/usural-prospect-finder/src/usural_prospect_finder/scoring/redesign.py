"""Deterministic Phase 4 website redesign analysis from persisted Phase 3 evidence."""

from __future__ import annotations

import hashlib
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from ..models import LeadQuality, ModernizationEstimate, Score, ScoreType, Signal
from ..models.common import JsonValue
from ..utils.serialization import dumps_json
from .base import ScoringContext

SCORER_VERSION = "4.0.0"


@dataclass(frozen=True, slots=True)
class EvidenceReason:
    signal_id: str
    signal_name: str
    text: str
    source_url: str | None
    audit_id: str | None
    confidence: float
    evidence: str | None

    def as_json(self) -> dict[str, JsonValue]:
        return {
            "signal_id": self.signal_id,
            "signal_name": self.signal_name,
            "text": self.text,
            "source_url": self.source_url,
            "audit_id": self.audit_id,
            "confidence": self.confidence,
            "evidence": self.evidence,
        }


@dataclass(frozen=True, slots=True)
class RedesignAnalysis:
    audit_id: str
    modernity_score: Score
    redesign_need_score: Score
    lead_quality: LeadQuality
    modernization_estimate: ModernizationEstimate
    dimensions: dict[str, float]
    reasons: tuple[EvidenceReason, ...]
    counter_signals: tuple[EvidenceReason, ...]
    evidence_coverage: float
    supporting_groups: int


class RedesignScorer:
    name = "website_redesign"
    version = SCORER_VERSION

    def __init__(self, configuration: dict[str, Any], *, as_of: date | None = None) -> None:
        self.configuration = configuration
        self.as_of = as_of or datetime.now(UTC).date()
        self.config_version = str(configuration["version"])
        self.config_hash = hashlib.sha256(dumps_json(configuration).encode()).hexdigest()

    def analyze(self, context: ScoringContext) -> RedesignAnalysis:
        evidence = _Evidence(context.signals)
        thresholds = self.configuration["thresholds"]
        legacy = self._legacy_risk(evidence)
        front_end = self._front_end(evidence)
        responsive = self._responsive(evidence)
        performance = self._performance(evidence)
        freshness = self._freshness(evidence)
        audit_status = str(context.configuration.get("audit_status", "completed"))
        reliability = 90.0 if audit_status == "completed" else 20.0
        dimensions = {
            "legacy_technology_risk": legacy,
            "front_end_modernity": front_end,
            "responsive_image_modernity": responsive,
            "performance_markup": performance,
            "content_freshness": freshness,
            "technical_reliability": reliability,
        }
        reasons = self._reasons(evidence, freshness)
        counters = self._counters(evidence, freshness)
        groups = self._supporting_groups(evidence, freshness, audit_status)
        pages = len({signal.page_id for signal in context.signals if signal.page_id})
        confidence = self._confidence(evidence, groups, pages, audit_status)
        insufficient = pages == 0 or groups < 2
        modernity = self._modernity(dimensions) if not insufficient else 50.0
        need = self._redesign_need(dimensions, evidence) if not insufficient else 65.0
        quality = self._quality(need, confidence, groups, insufficient, thresholds)
        estimate = self._estimate(modernity, legacy, counters, confidence, insufficient)
        metadata: dict[str, JsonValue] = {
            "lead_quality": quality.value,
            "modernization_estimate": estimate.value,
            "dimensions": {name: value for name, value in dimensions.items()},
            "evidence_coverage": confidence,
            "supporting_groups": groups,
            "reasons": [reason.as_json() for reason in reasons],
            "counter_signals": [reason.as_json() for reason in counters],
            "eligibility": "INSUFFICIENT_EVIDENCE" if insufficient else "ELIGIBLE",
            "weights_status": str(self.configuration["status"]),
        }
        reason_ids = tuple(reason.signal_id for reason in reasons)
        counter_ids = tuple(reason.signal_id for reason in counters)
        modernity_score = Score(
            audit_id=context.audit_id,
            score_type=ScoreType.WEBSITE_MODERNITY,
            score=round(modernity, 1),
            confidence=confidence,
            top_positive_signals=counter_ids,
            top_negative_signals=reason_ids,
            reason="; ".join(reason.text for reason in (*counters[:2], *reasons[:2])),
            scorer_version=self.version,
            configuration_version=self.config_version,
            configuration_hash=self.config_hash,
            metadata=metadata,
        )
        redesign_score = Score(
            audit_id=context.audit_id,
            score_type=ScoreType.REDESIGN_NEED,
            score=round(need, 1),
            confidence=confidence,
            top_positive_signals=reason_ids,
            top_negative_signals=counter_ids,
            reason="; ".join(reason.text for reason in (*reasons[:3], *counters[:2])),
            scorer_version=self.version,
            configuration_version=self.config_version,
            configuration_hash=self.config_hash,
            metadata=metadata,
        )
        return RedesignAnalysis(
            context.audit_id,
            modernity_score,
            redesign_score,
            quality,
            estimate,
            dimensions,
            reasons,
            counters,
            confidence,
            groups,
        )

    def _legacy_risk(self, evidence: _Evidence) -> float:
        weights = self.configuration["legacy_weights"]
        risk = 0.0
        wordpress = evidence.flag("wordpress_asset_path_detected")
        jquery = evidence.flag("jquery_detected")
        migrate = evidence.flag("jquery_migrate_detected")
        builder = evidence.flag("page_builder_reference")
        slider = evidence.flag("slider_reference")
        if wordpress:
            risk += float(weights["wordpress_alone"])
        if jquery:
            risk += float(weights["jquery"])
        if migrate:
            risk += float(weights["jquery_migrate"])
        if builder:
            risk += float(weights["page_builder"])
        if slider:
            risk += float(weights["slider"])
        thresholds = self.configuration["thresholds"]
        if evidence.maximum("script_count") > float(thresholds["excessive_scripts"]):
            risk += float(weights["excessive_scripts"])
        if evidence.maximum("stylesheet_count") > float(thresholds["excessive_stylesheets"]):
            risk += float(weights["excessive_stylesheets"])
        if migrate and builder and slider:
            risk += float(weights["migrate_builder_slider_interaction"])
        return min(100.0, risk)

    @staticmethod
    def _front_end(evidence: _Evidence) -> float:
        value = 40.0
        value += 15 if evidence.flag("doctype_present") else 0
        value += 15 if evidence.flag("viewport_meta_present") else 0
        value += 5 if evidence.flag("charset_present") else 0
        value += 15 if evidence.maximum("module_script_count") > 0 else 0
        value += 10 if evidence.has("structured_data_type") else 0
        if evidence.maximum("inline_script_count") > 15:
            value -= 10
        return _bounded(value)

    @staticmethod
    def _responsive(evidence: _Evidence) -> float:
        images = evidence.maximum("image_total")
        if images <= 0:
            return 50.0
        srcset = evidence.maximum("srcset_ratio")
        lazy = evidence.maximum("lazy_loading_ratio")
        sizes = evidence.maximum("image_sizes_count") / images
        dimensions = evidence.maximum("image_dimensions_count") / images
        modern = evidence.maximum("image_modern_format_count") / images
        viewport = 10.0 if evidence.flag("viewport_meta_present") else 0.0
        return _bounded(
            viewport + srcset * 30 + lazy * 25 + sizes * 15 + dimensions * 10 + modern * 10
        )

    @staticmethod
    def _performance(evidence: _Evidence) -> float:
        value = 45.0
        value += min(15.0, evidence.maximum("preload_count") * 3)
        value += min(10.0, evidence.maximum("preconnect_count") * 2)
        value += evidence.maximum("lazy_loading_ratio") * 20
        value += 10 if evidence.maximum("module_script_count") else 0
        if evidence.maximum("script_count") > 40:
            value -= 10
        if evidence.maximum("stylesheet_count") > 20:
            value -= 10
        return _bounded(value)

    def _freshness(self, evidence: _Evidence) -> float:
        latest = evidence.latest_date()
        if latest is None:
            return 50.0
        years = (self.as_of - latest).days / 365.25
        if years <= 1:
            return 90.0
        if years <= 3:
            return 70.0
        if years <= 5:
            return 45.0
        return 15.0

    def _modernity(self, dimensions: dict[str, float]) -> float:
        weights = self.configuration["dimension_weights"]
        values = {
            **dimensions,
            "legacy_technology_risk": 100 - dimensions["legacy_technology_risk"],
        }
        return _bounded(sum(values[name] * float(weight) for name, weight in weights.items()))

    def _redesign_need(self, dimensions: dict[str, float], evidence: _Evidence) -> float:
        value = (
            dimensions["legacy_technology_risk"] * 0.35
            + (100 - dimensions["front_end_modernity"]) * 0.18
            + (100 - dimensions["responsive_image_modernity"]) * 0.22
            + (100 - dimensions["performance_markup"]) * 0.10
            + (100 - dimensions["content_freshness"]) * 0.10
            + (100 - dimensions["technical_reliability"]) * 0.05
        )
        if (
            evidence.flag("jquery_migrate_detected")
            and evidence.flag("page_builder_reference")
            and evidence.flag("slider_reference")
        ):
            value += 8
        return _bounded(value)

    def _confidence(self, evidence: _Evidence, groups: int, pages: int, status: str) -> float:
        cfg = self.configuration["confidence"]
        value = float(cfg["base"]) + groups * float(cfg["per_evidence_group"])
        value += min(pages, int(cfg["max_page_credit"])) * float(cfg["per_page"])
        if evidence.flag("possible_js_rendered_site"):
            value -= float(cfg["js_shell_penalty"])
        if status != "completed":
            value -= float(cfg["incomplete_audit_penalty"])
        return round(max(0.05, min(0.95, value)), 2)

    @staticmethod
    def _supporting_groups(evidence: _Evidence, freshness: float, status: str) -> int:
        return sum(
            (
                any(
                    evidence.has(name)
                    for name in (
                        "jquery_detected",
                        "jquery_migrate_detected",
                        "page_builder_reference",
                        "slider_reference",
                    )
                ),
                any(
                    evidence.has(name)
                    for name in ("doctype_present", "viewport_meta_present", "module_script_count")
                ),
                evidence.has("image_total"),
                any(
                    evidence.has(name)
                    for name in ("preload_count", "preconnect_count", "script_count")
                ),
                freshness != 50.0,
                status != "completed",
            )
        )

    @staticmethod
    def _quality(
        need: float, confidence: float, groups: int, insufficient: bool, thresholds: dict[str, Any]
    ) -> LeadQuality:
        if insufficient:
            return LeadQuality.INSUFFICIENT_EVIDENCE
        if (
            need >= float(thresholds["high_redesign_need"])
            and confidence >= float(thresholds["high_confidence"])
            and groups >= int(thresholds["high_min_groups"])
        ):
            return LeadQuality.HIGH
        if need >= float(thresholds["medium_redesign_need"]) and confidence >= float(
            thresholds["medium_confidence"]
        ):
            return LeadQuality.MEDIUM
        return LeadQuality.LOW

    @staticmethod
    def _estimate(
        modernity: float,
        legacy: float,
        counters: tuple[EvidenceReason, ...],
        confidence: float,
        insufficient: bool,
    ) -> ModernizationEstimate:
        if insufficient or confidence < 0.4:
            return ModernizationEstimate.UNKNOWN
        if legacy >= 70 and modernity < 45:
            return ModernizationEstimate.LEGACY_IMPL
        if modernity >= 75 and len(counters) >= 3:
            return ModernizationEstimate.LIKELY_RECENT
        if modernity >= 58:
            return ModernizationEstimate.LIKELY_2_4_YEARS
        if modernity < 48:
            return ModernizationEstimate.LIKELY_5_PLUS_YEARS
        return ModernizationEstimate.UNKNOWN

    def _reasons(self, evidence: _Evidence, freshness: float) -> tuple[EvidenceReason, ...]:
        items: list[EvidenceReason] = []
        for name, text in (
            ("jquery_migrate_detected", "jQuery Migrate is present"),
            ("page_builder_reference", "Page-builder asset references were detected"),
            ("slider_reference", "Slider asset references were detected"),
        ):
            if evidence.flag(name):
                items.append(evidence.reason(name, text))
        if (
            evidence.maximum("image_total") > 0
            and evidence.has("srcset_ratio")
            and evidence.maximum("srcset_ratio")
            < float(self.configuration["thresholds"]["weak_ratio"])
        ):
            items.append(
                evidence.reason(
                    "srcset_ratio",
                    f"Responsive srcset coverage is {evidence.maximum('srcset_ratio'):.0%}",
                )
            )
        if (
            evidence.maximum("image_total") > 0
            and evidence.has("lazy_loading_ratio")
            and evidence.maximum("lazy_loading_ratio")
            < float(self.configuration["thresholds"]["weak_ratio"])
        ):
            items.append(
                evidence.reason(
                    "lazy_loading_ratio",
                    f"Native lazy-loading coverage is {evidence.maximum('lazy_loading_ratio'):.0%}",
                )
            )
        if freshness <= 45 and evidence.has("latest_visible_content_date"):
            items.append(
                evidence.reason(
                    "latest_visible_content_date",
                    f"Latest observed content activity is {evidence.latest_date()}",
                )
            )
        return tuple(items[:6])

    def _counters(self, evidence: _Evidence, freshness: float) -> tuple[EvidenceReason, ...]:
        items: list[EvidenceReason] = []
        if evidence.flag("viewport_meta_present"):
            items.append(
                evidence.reason("viewport_meta_present", "Responsive viewport metadata is present")
            )
        strong = float(self.configuration["thresholds"]["strong_ratio"])
        if evidence.maximum("srcset_ratio") >= strong:
            items.append(
                evidence.reason(
                    "srcset_ratio",
                    f"Strong responsive-image coverage ({evidence.maximum('srcset_ratio'):.0%})",
                )
            )
        if evidence.maximum("lazy_loading_ratio") >= strong:
            items.append(
                evidence.reason(
                    "lazy_loading_ratio",
                    "Strong native lazy-loading coverage "
                    f"({evidence.maximum('lazy_loading_ratio'):.0%})",
                )
            )
        if evidence.maximum("module_script_count") > 0:
            items.append(evidence.reason("module_script_count", "JavaScript modules are used"))
        if freshness >= 70 and evidence.has("latest_visible_content_date"):
            items.append(
                evidence.reason(
                    "latest_visible_content_date",
                    f"Recent content activity observed ({evidence.latest_date()})",
                )
            )
        return tuple(items[:6])


class _Evidence:
    def __init__(self, signals: tuple[Signal, ...]) -> None:
        self.signals = signals
        self.by_name: dict[str, list[Signal]] = {}
        for signal in signals:
            self.by_name.setdefault(signal.name, []).append(signal)

    def has(self, name: str) -> bool:
        return bool(self.by_name.get(name))

    def flag(self, name: str) -> bool:
        return any(signal.value is True for signal in self.by_name.get(name, []))

    def maximum(self, name: str) -> float:
        values = [
            float(signal.value)
            for signal in self.by_name.get(name, [])
            if isinstance(signal.value, int | float) and not isinstance(signal.value, bool)
        ]
        return max(values, default=0.0)

    def latest_date(self) -> date | None:
        values: list[date] = []
        for signal in self.by_name.get("latest_visible_content_date", []):
            if isinstance(signal.value, str):
                with suppress(ValueError):
                    values.append(date.fromisoformat(signal.value[:10]))
        return max(values, default=None)

    def reason(self, name: str, text: str) -> EvidenceReason:
        signal = self.by_name[name][0]
        return EvidenceReason(
            signal.id,
            signal.name,
            text,
            signal.source_url,
            signal.audit_id,
            signal.confidence,
            signal.evidence,
        )


def _bounded(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 1)
