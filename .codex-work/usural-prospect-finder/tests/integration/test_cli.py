from pathlib import Path

import pytest
from typer.testing import CliRunner

from usural_prospect_finder import main
from usural_prospect_finder.main import app
from usural_prospect_finder.providers.search import SearchResult


def test_init_db(runner: CliRunner, tmp_path: Path) -> None:
    database = tmp_path / "cli.sqlite3"
    result = runner.invoke(app, ["init-db", "--database", str(database)])
    assert result.exit_code == 0
    assert database.exists()
    second = runner.invoke(app, ["init-db", "--database", str(database)])
    assert second.exit_code == 0


@pytest.mark.parametrize(
    "arguments",
    [
        ["run", "--location", "Barcelona", "--category", "architects"],
        ["export", "--format", "csv"],
    ],
)
def test_placeholders_are_explicit(runner: CliRunner, arguments: list[str]) -> None:
    result = runner.invoke(app, arguments)
    assert result.exit_code == 2
    assert "Phase 1" in result.output


@pytest.mark.parametrize(
    "arguments",
    [
        ["--help"],
        ["init-db", "--help"],
        ["discover", "--help"],
        ["audit", "--help"],
        ["run", "--help"],
        ["rescore", "--help"],
        ["export", "--help"],
        ["inspect", "--help"],
    ],
)
def test_help_is_available_without_tracebacks(runner: CliRunner, arguments: list[str]) -> None:
    result = runner.invoke(app, arguments)
    assert result.exit_code == 0
    assert "Traceback" not in result.output


def test_audit_cli_prints_objective_summary(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from usural_prospect_finder.pipeline.website_audit_pipeline import WebsiteAuditSummary

    async def fake_run(self: object, domain: str) -> WebsiteAuditSummary:
        del self
        return WebsiteAuditSummary(
            domain=domain,
            audit_id="audit",
            homepage_url=f"https://{domain}/",
            pages_selected=3,
            pages_fetched=2,
            pages_failed=1,
            company_name="Fixture Law",
            email_found=True,
            phone_found=True,
            team_page_found=True,
            services_page_found=False,
            latest_content_date="2026-01-02",
            facts={"script_count": 2, "stylesheet_count": 1, "srcset_ratio": 0.5},
            issues=(),
        )

    monkeypatch.setenv("UPF_DATABASE_PATH", str(tmp_path / "audit.sqlite3"))
    monkeypatch.setattr(main.WebsiteAuditPipeline, "run", fake_run)
    result = runner.invoke(app, ["audit", "--domain", "fixture.example"])
    assert result.exit_code == 0
    assert "Pages fetched: 2" in result.output
    assert "Outdated Score" not in result.output


def test_discover_cli_reports_real_fixture_counts(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FakeProvider:
        name = "fixture"

        def __init__(self, api_key: str, *, timeout: float) -> None:
            del api_key, timeout

        async def search(self, query: str, *, limit: int) -> list[SearchResult]:
            del limit
            return [SearchResult("Fixture Law", "https://www.fixture-law.example/team", 1)]

    database = tmp_path / "discover.sqlite3"
    monkeypatch.setenv("UPF_SEARCH_API_KEY", "fixture-key")
    monkeypatch.setenv("UPF_DATABASE_PATH", str(database))
    monkeypatch.setattr(main, "BraveSearchProvider", FakeProvider)
    result = runner.invoke(app, ["discover", "--location", "Barcelona", "--category", "lawyers"])
    assert result.exit_code == 0
    assert "Queries executed: 14" in result.output
    assert "Raw results: 14" in result.output
    assert "Duplicates: 13" in result.output
    assert "Persisted observations: 14" in result.output
    assert "Unique company domains: 1" in result.output
