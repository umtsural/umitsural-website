from dataclasses import replace

from typer.testing import CliRunner

from usural_prospect_finder.main import app
from usural_prospect_finder.models import Audit, Business, Page, Signal, SignalCategory, Website
from usural_prospect_finder.models.common import RunStatus
from usural_prospect_finder.pipeline.redesign_scoring_pipeline import RedesignScoringPipeline
from usural_prospect_finder.storage import SQLiteRepository


def seed(repository: SQLiteRepository, business: Business, website: Website) -> Audit:
    repository.add_business(business)
    repository.add_website(website)
    audit = Audit(website.id, "0.3", "0.3", "phase3", status=RunStatus.COMPLETED)
    repository.add_audit(audit)
    for page, (name, value) in enumerate(
        [
            ("jquery_migrate_detected", True),
            ("page_builder_reference", True),
            ("slider_reference", True),
            ("image_total", 10),
            ("srcset_ratio", 0.1),
            ("latest_visible_content_date", "2019-01-01"),
        ],
        1,
    ):
        stored_page = Page(
            website.id,
            f"https://{website.canonical_domain}/{page}",
            audit_id=audit.id,
            id=f"page-{page}",
        )
        repository.add_page(stored_page)
        repository.add_signal(
            Signal(
                name,
                SignalCategory.MODERNITY,
                value,
                website_id=website.id,
                audit_id=audit.id,
                page_id=stored_page.id,
                source_url=f"https://{website.canonical_domain}/{page}",
            )
        )
    return audit


def test_rescore_uses_persisted_signals_and_appends_history(
    repository: SQLiteRepository, business: Business, website: Website
) -> None:
    audit = seed(repository, business, website)
    pipeline = RedesignScoringPipeline(repository)
    first = pipeline.run(website.canonical_domain)
    second = pipeline.run(website.canonical_domain)
    assert len(first) == len(second) == 1
    assert len(repository.list_scores(audit.id)) == 4
    assert (
        first[0].analysis.redesign_need_score.score == second[0].analysis.redesign_need_score.score
    )


def test_rescore_and_inspect_cli_output(
    runner: CliRunner,
    repository: SQLiteRepository,
    business: Business,
    website: Website,
    monkeypatch,
) -> None:
    class NetworkForbidden:
        def __init__(self, *args: object, **kwargs: object) -> None:
            raise AssertionError("rescore must not construct a crawler")

    website = replace(website, canonical_domain="fixture.test", url="https://fixture.test/")
    seed(repository, business, website)
    monkeypatch.setenv("UPF_DATABASE_PATH", str(repository.path))
    monkeypatch.setattr("usural_prospect_finder.main.AsyncHttpCrawler", NetworkForbidden)
    result = runner.invoke(app, ["rescore", "--domain", "fixture.test"])
    assert result.exit_code == 0
    assert "Domains rescored: 1" in result.output
    assert "redesign need" in result.output
    inspected = runner.invoke(app, ["inspect", "fixture.test"])
    assert inspected.exit_code == 0
    assert "Website Modernity:" in inspected.output
    assert "Top Reasons:" in inspected.output
    assert "Opportunity Score" not in inspected.output
