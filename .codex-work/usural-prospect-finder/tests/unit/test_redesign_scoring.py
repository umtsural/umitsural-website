from datetime import date
from pathlib import Path

from usural_prospect_finder.config import load_yaml
from usural_prospect_finder.models import LeadQuality, Signal, SignalCategory
from usural_prospect_finder.scoring.base import ScoringContext
from usural_prospect_finder.scoring.redesign import RedesignScorer

CONFIG = Path(__file__).parents[2] / "config/redesign.yaml"


def signal(name: str, value: bool | int | float | str, page: int = 1) -> Signal:
    return Signal(
        name,
        SignalCategory.MODERNITY,
        value,
        audit_id="audit",
        page_id=f"page-{page}",
        source_url=f"https://example.test/{page}",
        evidence=f"fixture:{name}",
        confidence=0.9,
    )


def analyze(*signals: Signal, config: dict[str, object] | None = None):
    scorer = RedesignScorer(config or load_yaml(CONFIG), as_of=date(2026, 8, 9))
    return scorer.analyze(ScoringContext("audit", tuple(signals), {"audit_status": "completed"}))


def modern_signals() -> list[Signal]:
    return [
        signal("doctype_present", True, 1),
        signal("viewport_meta_present", True, 2),
        signal("module_script_count", 3, 3),
        signal("image_total", 10, 4),
        signal("srcset_ratio", 0.9, 4),
        signal("lazy_loading_ratio", 0.9, 5),
        signal("image_sizes_count", 9, 5),
        signal("image_dimensions_count", 9, 6),
        signal("latest_visible_content_date", "2026-07-01", 6),
        signal("preload_count", 3, 6),
    ]


def legacy_signals(*, recent: bool = False) -> list[Signal]:
    return [
        signal("wordpress_asset_path_detected", True, 1),
        signal("jquery_detected", True, 1),
        signal("jquery_migrate_detected", True, 2),
        signal("page_builder_reference", True, 2),
        signal("slider_reference", True, 3),
        signal("doctype_present", True, 3),
        signal("viewport_meta_present", True, 4),
        signal("image_total", 10, 4),
        signal("srcset_ratio", 0.1, 5),
        signal("lazy_loading_ratio", 0.1, 5),
        signal("script_count", 50, 6),
        signal("latest_visible_content_date", "2026-06-01" if recent else "2019-01-01", 6),
    ]


def test_modern_site_counter_signals_reduce_redesign_need() -> None:
    result = analyze(*modern_signals())
    assert result.modernity_score.score > 70
    assert result.redesign_need_score.score < 35
    assert result.lead_quality is LeadQuality.LOW
    assert len(result.counter_signals) >= 4


def test_legacy_wordpress_combination_is_stronger_than_isolated_signals() -> None:
    combined = analyze(*legacy_signals())
    jquery = analyze(signal("jquery_detected", True), signal("doctype_present", True, 2))
    migrate = analyze(signal("jquery_migrate_detected", True), signal("doctype_present", True, 2))
    builder_slider = analyze(
        signal("page_builder_reference", True),
        signal("slider_reference", True, 2),
        signal("script_count", 10, 3),
    )
    assert combined.redesign_need_score.score > jquery.redesign_need_score.score
    assert combined.redesign_need_score.score > migrate.redesign_need_score.score
    assert (
        combined.dimensions["legacy_technology_risk"]
        > builder_slider.dimensions["legacy_technology_risk"]
    )


def test_responsive_ratios_and_freshness_move_independent_dimensions() -> None:
    weak = analyze(*legacy_signals())
    strong = analyze(*modern_signals())
    recent_legacy = analyze(*legacy_signals(recent=True))
    assert (
        weak.dimensions["responsive_image_modernity"]
        < strong.dimensions["responsive_image_modernity"]
    )
    assert weak.dimensions["content_freshness"] < recent_legacy.dimensions["content_freshness"]
    assert (
        recent_legacy.dimensions["legacy_technology_risk"]
        == weak.dimensions["legacy_technology_risk"]
    )
    assert recent_legacy.redesign_need_score.score < weak.redesign_need_score.score


def test_missing_body_and_invalid_tls_are_insufficient_and_low_confidence() -> None:
    scorer = RedesignScorer(load_yaml(CONFIG), as_of=date(2026, 8, 9))
    result = scorer.analyze(ScoringContext("audit", (), {"audit_status": "failed"}))
    assert result.lead_quality is LeadQuality.INSUFFICIENT_EVIDENCE
    assert result.modernity_score.score == 50
    assert result.redesign_need_score.score == 65
    assert result.redesign_need_score.confidence < 0.4


def test_confidence_and_multigroup_quality_gates() -> None:
    sparse = analyze(signal("jquery_migrate_detected", True))
    covered = analyze(*legacy_signals())
    assert sparse.lead_quality is LeadQuality.INSUFFICIENT_EVIDENCE
    assert covered.redesign_need_score.confidence > sparse.redesign_need_score.confidence
    assert covered.supporting_groups >= 3
    assert covered.lead_quality in {LeadQuality.MEDIUM, LeadQuality.HIGH}


def test_explanations_preserve_signal_provenance() -> None:
    result = analyze(*legacy_signals())
    reason = result.reasons[0]
    assert reason.signal_id
    assert reason.signal_name
    assert reason.source_url == "https://example.test/2"
    assert reason.audit_id == "audit"
    assert reason.evidence


def test_scoring_is_deterministic_and_config_driven() -> None:
    config = load_yaml(CONFIG)
    first = analyze(*legacy_signals(), config=config)
    second = analyze(*legacy_signals(), config=config)
    assert first.redesign_need_score.score == second.redesign_need_score.score
    changed = load_yaml(CONFIG)
    changed["legacy_weights"]["jquery_migrate"] = 0
    third = analyze(*legacy_signals(), config=changed)
    assert third.redesign_need_score.score < first.redesign_need_score.score
    assert (
        third.redesign_need_score.configuration_hash != first.redesign_need_score.configuration_hash
    )
