import sqlite3
from contextlib import closing
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from usural_prospect_finder.models import (
    Audit,
    Business,
    Score,
    ScoreType,
    Signal,
    SignalCategory,
    Website,
)
from usural_prospect_finder.storage import RepositoryConflictError, SQLiteRepository


def test_database_initializes_all_tables(repository: SQLiteRepository) -> None:
    with closing(sqlite3.connect(repository.path)) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    assert {
        "businesses",
        "websites",
        "pages",
        "contacts",
        "audits",
        "signals",
        "scores",
        "discovery_candidates",
    } <= tables


def test_initialization_is_idempotent_and_records_each_migration_once(
    repository: SQLiteRepository,
) -> None:
    repository.initialize()
    with closing(sqlite3.connect(repository.path)) as connection:
        history = connection.execute(
            "SELECT version, COUNT(*) FROM schema_migrations GROUP BY version ORDER BY version"
        ).fetchall()
        foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()[0]
        journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
    assert history == [(1, 1), (2, 1), (3, 1), (4, 1), (5, 1)]
    # Foreign keys are connection-local and enabled by the adapter; raw connections default off.
    assert foreign_keys == 0
    assert journal_mode == "wal"


def test_repository_persists_evidence_chain(
    repository: SQLiteRepository, business: Business, website: Website
) -> None:
    repository.add_business(business)
    repository.add_website(website)
    audit = Audit(
        website_id=website.id,
        crawler_version="0.1",
        analyzer_version="0.1",
        configuration_hash="abc",
    )
    repository.add_audit(audit)
    signal = Signal(
        name="fixture",
        category=SignalCategory.MODERNITY,
        value={"detected": True},
        business_id=business.id,
        website_id=website.id,
        audit_id=audit.id,
    )
    repository.add_signal(signal)
    score = Score(
        audit_id=audit.id,
        score_type=ScoreType.MODERNIZATION_GAP,
        score=42,
        confidence=0.8,
        top_positive_signals=(signal.id,),
    )
    repository.add_score(score)
    assert repository.get_business(business.id) == business
    assert repository.get_audit(audit.id) == audit
    assert repository.list_signals(audit.id) == [signal]
    assert repository.get_score(audit.id, ScoreType.MODERNIZATION_GAP) == score


def test_business_crud(repository: SQLiteRepository, business: Business) -> None:
    repository.add_business(business)
    updated = replace(business, name="Updated Fixture Studio")
    repository.update_business(updated)
    assert repository.get_business(business.id) == updated
    assert repository.delete_business(business.id)
    assert repository.get_business(business.id) is None


def test_transaction_rolls_back_all_writes(
    repository: SQLiteRepository, business: Business, website: Website
) -> None:
    with pytest.raises(RuntimeError, match="abort"), repository.transaction() as transaction:
        transaction.add_business(business)
        transaction.add_website(website)
        raise RuntimeError("abort")
    assert repository.get_business(business.id) is None


def test_canonical_domain_uniqueness_uses_neutral_error(
    repository: SQLiteRepository, business: Business, website: Website
) -> None:
    repository.add_business(business)
    repository.add_website(website)
    duplicate = replace(website, id="different", url="http://www.example.com/en")
    with pytest.raises(RepositoryConflictError):
        repository.add_website(duplicate)


def test_foreign_keys_are_enforced_through_adapter(
    repository: SQLiteRepository, website: Website
) -> None:
    with pytest.raises(RepositoryConflictError):
        repository.add_website(website)


def test_audit_and_score_history_remains_attributable(
    repository: SQLiteRepository, business: Business, website: Website
) -> None:
    repository.add_business(business)
    repository.add_website(website)
    january = Audit(
        website_id=website.id,
        crawler_version="0.1",
        analyzer_version="0.1",
        configuration_hash="one",
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    march = replace(
        january,
        id="march-audit",
        configuration_hash="two",
        started_at=january.started_at + timedelta(days=60),
    )
    repository.add_audit(january)
    repository.add_audit(march)
    january_score = Score(
        audit_id=january.id,
        score_type=ScoreType.OPPORTUNITY,
        score=82,
        confidence=0.9,
    )
    march_score = replace(january_score, id="march-score", audit_id=march.id, score=61)
    repository.add_score(january_score)
    repository.add_score(march_score)
    assert repository.list_audits(website.id) == [january, march]
    assert repository.list_scores(january.id) == [january_score]
    assert repository.list_scores(march.id) == [march_score]


def test_rescoring_appends_history_and_latest_score_wins(
    repository: SQLiteRepository, business: Business, website: Website
) -> None:
    repository.add_business(business)
    repository.add_website(website)
    audit = Audit(website.id, "0.3", "0.3", "audit-config")
    repository.add_audit(audit)
    first = Score(audit.id, ScoreType.REDESIGN_NEED, 61, 0.7, scorer_version="4.0.0")
    second = replace(first, id="second-score", score=72, configuration_version="2")
    repository.add_score(first)
    repository.add_score(second)
    assert repository.list_scores(audit.id) == [first, second]
    assert repository.latest_score(audit.id, ScoreType.REDESIGN_NEED) == second


def test_signal_datetime_and_enum_round_trip(
    repository: SQLiteRepository, business: Business, website: Website
) -> None:
    repository.add_business(business)
    repository.add_website(website)
    audit = Audit(
        website_id=website.id,
        crawler_version="0.1",
        analyzer_version="0.1",
        configuration_hash="hash",
    )
    repository.add_audit(audit)
    signal = Signal(
        name="last_activity",
        category=SignalCategory.CONTENT_FRESHNESS,
        value=datetime(2026, 8, 9, 12, tzinfo=UTC),
        metadata={"published": True, "date": datetime(2025, 1, 1, tzinfo=UTC)},
        website_id=website.id,
        audit_id=audit.id,
    )
    repository.add_signal(signal)
    restored = repository.list_signals(audit.id)[0]
    assert restored == signal
    assert restored.category is SignalCategory.CONTENT_FRESHNESS
