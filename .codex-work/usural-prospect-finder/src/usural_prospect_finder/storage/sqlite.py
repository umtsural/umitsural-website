"""SQLite implementation of the repository port."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from ..discovery.base import DiscoveryCandidate, DomainClassification
from ..models import (
    Audit,
    Business,
    Contact,
    ContactClassification,
    ContactType,
    CrawlStatus,
    Page,
    PageType,
    Score,
    ScoreType,
    Signal,
    SignalCategory,
    Website,
)
from ..models.common import JsonValue, Location, RunStatus
from ..utils.serialization import dumps_json, loads_json
from .errors import RepositoryConflictError
from .migrations import migrate


class SQLiteRepository:
    """Explicit, transaction-safe SQLite adapter."""

    def __init__(
        self, path: Path, *, _transaction_connection: sqlite3.Connection | None = None
    ) -> None:
        self.path = path
        self._transaction_connection = _transaction_connection

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        if self._transaction_connection is not None:
            yield self._transaction_connection
            return
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            migrate(connection)

    @contextmanager
    def transaction(self) -> Iterator[SQLiteRepository]:
        """Yield a repository whose writes commit or roll back as one unit."""
        if self._transaction_connection is not None:
            yield self
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield SQLiteRepository(self.path, _transaction_connection=connection)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _execute(self, sql: str, parameters: tuple[Any, ...]) -> None:
        try:
            with self._connect() as connection:
                connection.execute(sql, parameters)
        except sqlite3.IntegrityError as exc:
            raise RepositoryConflictError(str(exc)) from exc

    def add_business(self, item: Business) -> None:
        self._execute(
            "INSERT INTO businesses VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                item.id,
                item.name,
                item.category,
                dumps_json(asdict(item.location)),
                item.country,
                item.website_id,
                item.first_seen_at.isoformat(),
                item.last_seen_at.isoformat(),
                item.created_at.isoformat(),
                item.updated_at.isoformat(),
            ),
        )

    def get_business(self, business_id: str) -> Business | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM businesses WHERE id=?", (business_id,)
            ).fetchone()
        if row is None:
            return None
        return Business(
            id=row["id"],
            name=row["name"],
            category=row["category"],
            location=Location(**cast(dict[str, Any], loads_json(row["location_json"]))),
            country=row["country"],
            website_id=row["website_id"],
            first_seen_at=datetime.fromisoformat(row["first_seen_at"]),
            last_seen_at=datetime.fromisoformat(row["last_seen_at"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def update_business(self, item: Business) -> None:
        """Update mutable business attributes without changing observation history."""
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE businesses
                SET name=?, category=?, location_json=?, country=?, website_id=?,
                    last_seen_at=?, updated_at=? WHERE id=?""",
                (
                    item.name,
                    item.category,
                    dumps_json(asdict(item.location)),
                    item.country,
                    item.website_id,
                    item.last_seen_at.isoformat(),
                    item.updated_at.isoformat(),
                    item.id,
                ),
            )
            if cursor.rowcount != 1:
                raise KeyError(item.id)

    def delete_business(self, business_id: str) -> bool:
        """Delete a business only when foreign-key relationships permit it."""
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM businesses WHERE id=?", (business_id,))
            return cursor.rowcount == 1

    def add_website(self, item: Website) -> None:
        self._execute(
            "INSERT INTO websites VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                item.id,
                item.business_id,
                item.url,
                item.canonical_domain,
                item.scheme,
                item.status,
                item.first_seen_at.isoformat(),
                _iso(item.last_crawled_at),
                item.created_at.isoformat(),
                item.updated_at.isoformat(),
            ),
        )

    def get_website_by_domain(self, canonical_domain: str) -> Website | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM websites WHERE canonical_domain=?", (canonical_domain,)
            ).fetchone()
        if row is None:
            return None
        return Website(
            id=row["id"],
            business_id=row["business_id"],
            url=row["url"],
            canonical_domain=row["canonical_domain"],
            scheme=row["scheme"],
            status=row["status"],
            first_seen_at=datetime.fromisoformat(row["first_seen_at"]),
            last_crawled_at=_date(row["last_crawled_at"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def list_websites(self) -> list[Website]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM websites ORDER BY canonical_domain").fetchall()
        return [_website_from_row(row) for row in rows]

    def add_page(self, item: Page) -> None:
        self._execute(
            """INSERT INTO pages (
            id,website_id,url,page_type,status_code,content_type,title,fetched_at,crawl_status,
            audit_id,requested_url,final_url,elapsed_ms,content_length,content_hash,language,
            redirect_chain_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                item.id,
                item.website_id,
                item.url,
                item.page_type,
                item.status_code,
                item.content_type,
                item.title,
                _iso(item.fetched_at),
                item.crawl_status,
                item.audit_id,
                item.requested_url,
                item.final_url,
                item.elapsed_ms,
                item.content_length,
                item.content_hash,
                item.language,
                dumps_json(list(item.redirect_chain)),
            ),
        )

    def list_pages(self, audit_id: str) -> list[Page]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM pages WHERE audit_id=? ORDER BY fetched_at,id", (audit_id,)
            ).fetchall()
        return [
            Page(
                id=row["id"],
                website_id=row["website_id"],
                audit_id=row["audit_id"],
                url=row["url"],
                requested_url=row["requested_url"],
                final_url=row["final_url"],
                page_type=PageType(row["page_type"]),
                status_code=row["status_code"],
                content_type=row["content_type"],
                title=row["title"],
                fetched_at=_date(row["fetched_at"]),
                crawl_status=CrawlStatus(row["crawl_status"]),
                elapsed_ms=row["elapsed_ms"],
                content_length=row["content_length"],
                content_hash=row["content_hash"],
                language=row["language"],
                redirect_chain=_string_tuple(loads_json(row["redirect_chain_json"])),
            )
            for row in rows
        ]

    def add_contact(self, item: Contact) -> None:
        self._execute(
            """INSERT INTO contacts (
            id,business_id,website_id,type,value,classification,source_url,confidence,is_public,
            created_at,audit_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                item.id,
                item.business_id,
                item.website_id,
                item.type,
                item.value,
                item.classification,
                item.source_url,
                item.confidence,
                int(item.is_public),
                item.created_at.isoformat(),
                item.audit_id,
            ),
        )

    def list_contacts(self, audit_id: str) -> list[Contact]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM contacts WHERE audit_id=? ORDER BY created_at,id", (audit_id,)
            ).fetchall()
        return [
            Contact(
                id=row["id"],
                business_id=row["business_id"],
                website_id=row["website_id"],
                audit_id=row["audit_id"],
                type=ContactType(row["type"]),
                value=row["value"],
                classification=ContactClassification(row["classification"]),
                source_url=row["source_url"],
                confidence=row["confidence"],
                is_public=bool(row["is_public"]),
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    def add_audit(self, item: Audit) -> None:
        self._execute(
            "INSERT INTO audits VALUES (?,?,?,?,?,?,?,?,?)",
            (
                item.id,
                item.website_id,
                item.started_at.isoformat(),
                _iso(item.completed_at),
                item.status,
                item.crawler_version,
                item.analyzer_version,
                item.configuration_hash,
                item.notes,
            ),
        )

    def update_audit(self, item: Audit) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE audits SET completed_at=?,status=?,notes=? WHERE id=?""",
                (_iso(item.completed_at), item.status, item.notes, item.id),
            )
            if cursor.rowcount != 1:
                raise KeyError(item.id)

    def get_audit(self, audit_id: str) -> Audit | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM audits WHERE id=?", (audit_id,)).fetchone()
        if row is None:
            return None
        return Audit(
            id=row["id"],
            website_id=row["website_id"],
            started_at=datetime.fromisoformat(row["started_at"]),
            completed_at=_date(row["completed_at"]),
            status=RunStatus(row["status"]),
            crawler_version=row["crawler_version"],
            analyzer_version=row["analyzer_version"],
            configuration_hash=row["configuration_hash"],
            notes=row["notes"],
        )

    def list_audits(self, website_id: str) -> list[Audit]:
        """Return all website audits in stable chronological order."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM audits WHERE website_id=? ORDER BY started_at,id", (website_id,)
            ).fetchall()
        return [_audit_from_row(row) for row in rows]

    def add_signal(self, item: Signal) -> None:
        self._execute(
            "INSERT INTO signals VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                item.id,
                item.business_id,
                item.website_id,
                item.page_id,
                item.audit_id,
                item.name,
                item.category,
                dumps_json(item.value),
                item.weight,
                item.confidence,
                item.source_url,
                item.evidence,
                dumps_json(item.metadata),
                item.detected_at.isoformat(),
            ),
        )

    def list_signals(self, audit_id: str) -> list[Signal]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM signals WHERE audit_id=? ORDER BY detected_at,id", (audit_id,)
            ).fetchall()
        return [
            Signal(
                id=r["id"],
                business_id=r["business_id"],
                website_id=r["website_id"],
                page_id=r["page_id"],
                audit_id=r["audit_id"],
                name=r["name"],
                category=SignalCategory(r["category"]),
                value=loads_json(r["value_json"]),
                weight=r["weight"],
                confidence=r["confidence"],
                source_url=r["source_url"],
                evidence=r["evidence"],
                metadata=cast(dict[str, JsonValue], loads_json(r["metadata_json"])),
                detected_at=datetime.fromisoformat(r["detected_at"]),
            )
            for r in rows
        ]

    def add_score(self, item: Score) -> None:
        self._execute(
            """INSERT INTO scores (
            id,audit_id,score_type,score,confidence,positive_signal_ids_json,
            negative_signal_ids_json,reason,calculated_at,scorer_version,
            configuration_version,configuration_hash,metadata_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                item.id,
                item.audit_id,
                item.score_type,
                item.score,
                item.confidence,
                json.dumps(item.top_positive_signals),
                json.dumps(item.top_negative_signals),
                item.reason,
                item.calculated_at.isoformat(),
                item.scorer_version,
                item.configuration_version,
                item.configuration_hash,
                dumps_json(item.metadata),
            ),
        )

    def get_score(self, audit_id: str, score_type: str) -> Score | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM scores WHERE audit_id=? AND score_type=?", (audit_id, score_type)
            ).fetchone()
        if row is None:
            return None
        return _score_from_row(row)

    def list_scores(self, audit_id: str) -> list[Score]:
        """Return the immutable score set associated with one audit."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM scores WHERE audit_id=? ORDER BY score_type,id", (audit_id,)
            ).fetchall()
        return [_score_from_row(row) for row in rows]

    def latest_score(self, audit_id: str, score_type: str) -> Score | None:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT * FROM scores WHERE audit_id=? AND score_type=?
                ORDER BY calculated_at DESC,id DESC LIMIT 1""",
                (audit_id, score_type),
            ).fetchone()
        return _score_from_row(row) if row is not None else None

    def add_discovery_candidate(self, item: DiscoveryCandidate) -> None:
        self._execute(
            """INSERT INTO discovery_candidates (
                id,business_name,url,source,query,position,category,location,discovered_at,
                canonical_domain,provider,classification,filter_reason,title,metadata_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                item.id,
                item.business_name,
                item.url,
                item.source,
                item.query,
                item.position,
                item.category,
                item.location,
                item.discovered_at.isoformat(),
                item.canonical_domain,
                item.provider,
                item.classification,
                item.filter_reason,
                item.title,
                dumps_json(item.metadata),
            ),
        )

    def list_discovery_candidates(
        self, *, category: str | None = None, location: str | None = None
    ) -> list[DiscoveryCandidate]:
        clauses: list[str] = []
        parameters: list[str] = []
        if category is not None:
            clauses.append("category=?")
            parameters.append(category)
        if location is not None:
            clauses.append("location=?")
            parameters.append(location)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM discovery_candidates{where} ORDER BY discovered_at,id",
                parameters,
            ).fetchall()
        return [
            DiscoveryCandidate(
                id=row["id"],
                business_name=row["business_name"],
                url=row["url"],
                source=row["source"],
                query=row["query"],
                position=row["position"],
                category=row["category"],
                location=row["location"],
                discovered_at=datetime.fromisoformat(row["discovered_at"]),
                canonical_domain=row["canonical_domain"],
                provider=row["provider"],
                classification=DomainClassification(row["classification"]),
                filter_reason=row["filter_reason"],
                title=row["title"],
                metadata=cast(dict[str, JsonValue], loads_json(row["metadata_json"])),
            )
            for row in rows
        ]


def _audit_from_row(row: sqlite3.Row) -> Audit:
    return Audit(
        id=row["id"],
        website_id=row["website_id"],
        started_at=datetime.fromisoformat(row["started_at"]),
        completed_at=_date(row["completed_at"]),
        status=RunStatus(row["status"]),
        crawler_version=row["crawler_version"],
        analyzer_version=row["analyzer_version"],
        configuration_hash=row["configuration_hash"],
        notes=row["notes"],
    )


def _string_tuple(value: JsonValue) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, str))


def _score_from_row(row: sqlite3.Row) -> Score:
    return Score(
        id=row["id"],
        audit_id=row["audit_id"],
        score_type=ScoreType(row["score_type"]),
        score=row["score"],
        confidence=row["confidence"],
        top_positive_signals=tuple(json.loads(row["positive_signal_ids_json"])),
        top_negative_signals=tuple(json.loads(row["negative_signal_ids_json"])),
        reason=row["reason"],
        calculated_at=datetime.fromisoformat(row["calculated_at"]),
        scorer_version=row["scorer_version"],
        configuration_version=row["configuration_version"],
        configuration_hash=row["configuration_hash"],
        metadata=cast(dict[str, JsonValue], loads_json(row["metadata_json"])),
    )


def _website_from_row(row: sqlite3.Row) -> Website:
    return Website(
        id=row["id"],
        business_id=row["business_id"],
        url=row["url"],
        canonical_domain=row["canonical_domain"],
        scheme=row["scheme"],
        status=row["status"],
        first_seen_at=datetime.fromisoformat(row["first_seen_at"]),
        last_crawled_at=_date(row["last_crawled_at"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _date(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None
