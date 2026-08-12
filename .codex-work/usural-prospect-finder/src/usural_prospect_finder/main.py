"""Command-line interface and application composition root."""

import asyncio
from pathlib import Path
from typing import Annotated

import typer

from .config import Settings, load_category_config, load_yaml
from .crawling.http import AsyncHttpCrawler
from .discovery import DomainClassification
from .discovery.queries import build_query_plan
from .pipeline.discovery_pipeline import (
    DiscoveryExecutionError,
    DiscoveryPipeline,
    DiscoverySummary,
)
from .pipeline.redesign_scoring_pipeline import RedesignScoringPipeline
from .pipeline.website_audit_pipeline import WebsiteAuditPipeline, WebsiteAuditSummary
from .providers import BraveSearchProvider
from .storage import SQLiteRepository
from .utils.logging import configure_logging

app = typer.Typer(no_args_is_help=True, help="USURAL evidence-driven prospect finder.")


def _later_phase(feature: str) -> None:
    typer.echo(f"{feature} is intentionally unavailable in Phase 1.", err=True)
    raise typer.Exit(code=2)


@app.command("init-db")
def init_db(
    database: Annotated[
        Path | None, typer.Option("--database", help="SQLite database path.")
    ] = None,
) -> None:
    """Initialize or migrate the SQLite database."""
    path = database or Settings.from_env().database_path
    SQLiteRepository(path).initialize()
    typer.echo(f"Database initialized: {path}")


@app.command()
def discover(location: str = typer.Option(...), category: str = typer.Option(...)) -> None:
    """Discover and persist candidate company domains through the configured provider."""
    settings = Settings.from_env()
    configure_logging(settings.log_level, settings.log_dir)
    try:
        profiles = load_category_config()
        plan = build_query_plan(category, location, profiles)
        repository = SQLiteRepository(settings.database_path)
        repository.initialize()
        provider = BraveSearchProvider(
            settings.search_api_key or "", timeout=settings.request_timeout
        )
        pipeline = DiscoveryPipeline(
            provider,
            repository,
            load_yaml(Path(__file__).resolve().parents[2] / "config/exclusions.yaml"),
            category_hints=profiles[plan.category].get("classification_hints"),
            concurrency=settings.global_concurrency,
        )
        summary = asyncio.run(pipeline.run(plan))
    except (DiscoveryExecutionError, ValueError, OSError) as exc:
        typer.echo(f"Discovery failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    _print_discovery_summary(summary)


def _print_discovery_summary(summary: DiscoverySummary) -> None:
    typer.echo(f"Queries executed: {summary.queries_executed}")
    typer.echo(f"Raw results: {summary.raw_results}")
    typer.echo("Filtered:")
    for classification in DomainClassification:
        if classification is not DomainClassification.COMPANY:
            typer.echo(
                f"  {classification.value.title()}: {summary.filtered.get(classification, 0)}"
            )
    typer.echo(f"Duplicates: {summary.duplicates}")
    typer.echo(f"Company websites: {summary.unique_company_domains}")
    typer.echo(f"Persisted observations: {summary.persisted_observations}")
    typer.echo(f"Unique company domains: {summary.unique_company_domains}")


@app.command()
def audit(domain: str = typer.Option(...)) -> None:
    """Selectively crawl a domain and persist objective Phase 3 evidence."""
    settings = Settings.from_env()
    configure_logging(settings.log_level, settings.log_dir)
    repository = SQLiteRepository(settings.database_path)
    repository.initialize()
    crawler = AsyncHttpCrawler(
        timeout=settings.request_timeout,
        max_redirects=settings.max_redirects,
        max_response_bytes=settings.max_response_bytes,
        user_agent=settings.user_agent,
        global_concurrency=settings.global_concurrency,
    )
    pipeline = WebsiteAuditPipeline(
        crawler,
        repository,
        max_pages_per_domain=settings.max_pages_per_domain,
        user_agent=settings.user_agent,
        minimum_domain_delay_seconds=settings.minimum_domain_delay_seconds,
    )
    try:
        summary = asyncio.run(pipeline.run(domain))
    except (ValueError, OSError) as exc:
        typer.echo(f"Audit failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    _print_audit_summary(summary)


def _print_audit_summary(summary: WebsiteAuditSummary) -> None:
    typer.echo(f"Domain: {summary.domain}")
    typer.echo(f"Homepage: {summary.homepage_url or 'unresolved'}")
    typer.echo(f"Pages selected: {summary.pages_selected}")
    typer.echo(f"Pages fetched: {summary.pages_fetched}")
    typer.echo(f"Pages failed: {summary.pages_failed}")
    typer.echo(f"Email found: {'yes' if summary.email_found else 'no'}")
    typer.echo(f"Phone found: {'yes' if summary.phone_found else 'no'}")
    typer.echo(f"Scripts: {summary.facts.get('script_count', 0)}")
    typer.echo(f"Stylesheets: {summary.facts.get('stylesheet_count', 0)}")
    typer.echo(
        "WordPress-like assets: "
        f"{'yes' if summary.facts.get('wordpress_asset_path_detected') else 'no'}"
    )
    typer.echo(f"Responsive image ratio: {summary.facts.get('srcset_ratio', 0)}")
    typer.echo(f"Latest content date: {summary.latest_content_date or 'none'}")


@app.command()
def run(
    location: str = typer.Option(...), category: str = typer.Option(...), target: int = 100
) -> None:
    """Run the end-to-end workflow (future placeholder)."""
    del location, category, target
    _later_phase("End-to-end prospecting")


@app.command()
def rescore(domain: str | None = typer.Option(None, "--domain")) -> None:
    """Recalculate Phase 4 redesign scores from persisted evidence without network access."""
    settings = Settings.from_env()
    repository = SQLiteRepository(settings.database_path)
    repository.initialize()
    try:
        results = RedesignScoringPipeline(repository).run(domain)
    except ValueError as exc:
        typer.echo(f"Rescore failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Domains rescored: {len(results)}")
    for item in results:
        analysis = item.analysis
        typer.echo(
            f"{item.website.canonical_domain}: modernity "
            f"{analysis.modernity_score.score:.1f}, redesign need "
            f"{analysis.redesign_need_score.score:.1f}, "
            f"confidence {analysis.redesign_need_score.confidence:.2f}, "
            f"{analysis.lead_quality.value}"
        )


@app.command("export")
def export_report(format_: str = typer.Option("csv", "--format")) -> None:
    """Export persisted prospects (future placeholder)."""
    del format_
    _later_phase("Database-backed reporting")


@app.command()
def inspect(domain: str = typer.Argument(...)) -> None:
    """Show the latest persisted Phase 4 redesign analysis for a domain."""
    settings = Settings.from_env()
    repository = SQLiteRepository(settings.database_path)
    repository.initialize()
    website = repository.get_website_by_domain(domain.casefold().removeprefix("www."))
    if website is None:
        typer.echo(f"No website found for {domain}", err=True)
        raise typer.Exit(code=1)
    audits = repository.list_audits(website.id)
    if not audits:
        typer.echo(f"No audits found for {domain}", err=True)
        raise typer.Exit(code=1)
    audit = audits[-1]
    modernity = repository.latest_score(audit.id, "website_modernity")
    redesign = repository.latest_score(audit.id, "redesign_need")
    if modernity is None or redesign is None:
        typer.echo(f"No Phase 4 redesign analysis found for {domain}", err=True)
        raise typer.Exit(code=1)
    metadata = redesign.metadata
    typer.echo(f"Domain: {website.canonical_domain}")
    typer.echo(f"Website Modernity: {modernity.score:.1f} / 100")
    typer.echo(f"Redesign Need: {redesign.score:.1f} / 100")
    typer.echo(f"Confidence: {redesign.confidence:.2f}")
    typer.echo(f"Redesign Lead Quality: {metadata.get('lead_quality', 'UNKNOWN')}")
    typer.echo(f"Modernization Estimate: {metadata.get('modernization_estimate', 'UNKNOWN')}")
    typer.echo("Top Reasons:")
    for reason in _metadata_texts(metadata.get("reasons")):
        typer.echo(f"- {reason}")
    typer.echo("Counter-Signals:")
    for reason in _metadata_texts(metadata.get("counter_signals")):
        typer.echo(f"- {reason}")


def _metadata_texts(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            result.append(item["text"])
    return result


if __name__ == "__main__":
    app()
