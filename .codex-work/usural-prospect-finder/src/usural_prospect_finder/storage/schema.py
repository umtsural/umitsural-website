"""Ordered, immutable SQLite migration definitions."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Migration:
    """A schema change with an explicit stable version."""

    version: int
    name: str
    sql: str


MIGRATIONS: tuple[Migration, ...] = (
    Migration(
        1,
        "initial_schema",
        """
    CREATE TABLE businesses (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL,
        location_json TEXT NOT NULL, country TEXT, website_id TEXT,
        first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    );
    CREATE TABLE websites (
        id TEXT PRIMARY KEY, business_id TEXT NOT NULL REFERENCES businesses(id),
        url TEXT NOT NULL, canonical_domain TEXT NOT NULL UNIQUE, scheme TEXT NOT NULL,
        status TEXT NOT NULL, first_seen_at TEXT NOT NULL, last_crawled_at TEXT,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    );
    CREATE TABLE pages (
        id TEXT PRIMARY KEY, website_id TEXT NOT NULL REFERENCES websites(id), url TEXT NOT NULL,
        page_type TEXT NOT NULL, status_code INTEGER, content_type TEXT, title TEXT,
        fetched_at TEXT, crawl_status TEXT NOT NULL
    );
    CREATE TABLE contacts (
        id TEXT PRIMARY KEY, business_id TEXT NOT NULL REFERENCES businesses(id),
        website_id TEXT NOT NULL REFERENCES websites(id), type TEXT NOT NULL, value TEXT NOT NULL,
        classification TEXT NOT NULL, source_url TEXT NOT NULL, confidence REAL NOT NULL,
        is_public INTEGER NOT NULL, created_at TEXT NOT NULL
    );
    CREATE TABLE audits (
        id TEXT PRIMARY KEY, website_id TEXT NOT NULL REFERENCES websites(id),
        started_at TEXT NOT NULL, completed_at TEXT, status TEXT NOT NULL,
        crawler_version TEXT NOT NULL, analyzer_version TEXT NOT NULL,
        configuration_hash TEXT NOT NULL, notes TEXT
    );
    CREATE TABLE signals (
        id TEXT PRIMARY KEY, business_id TEXT REFERENCES businesses(id),
        website_id TEXT REFERENCES websites(id), page_id TEXT REFERENCES pages(id),
        audit_id TEXT REFERENCES audits(id), name TEXT NOT NULL, category TEXT NOT NULL,
        value_json TEXT NOT NULL, weight REAL NOT NULL, confidence REAL NOT NULL,
        source_url TEXT, evidence TEXT, metadata_json TEXT NOT NULL, detected_at TEXT NOT NULL
    );
    CREATE TABLE scores (
        id TEXT PRIMARY KEY, audit_id TEXT NOT NULL REFERENCES audits(id),
        score_type TEXT NOT NULL, score REAL NOT NULL CHECK(score BETWEEN 0 AND 100),
        confidence REAL NOT NULL CHECK(confidence BETWEEN 0 AND 1),
        positive_signal_ids_json TEXT NOT NULL, negative_signal_ids_json TEXT NOT NULL,
        reason TEXT, calculated_at TEXT NOT NULL, UNIQUE(audit_id, score_type)
    );
    CREATE TABLE discovery_candidates (
        id TEXT PRIMARY KEY, business_name TEXT NOT NULL, url TEXT NOT NULL, source TEXT NOT NULL,
        query TEXT NOT NULL, position INTEGER NOT NULL, category TEXT NOT NULL,
        location TEXT NOT NULL, discovered_at TEXT NOT NULL
    );
    CREATE INDEX idx_websites_business_id ON websites(business_id);
    CREATE INDEX idx_websites_canonical_domain ON websites(canonical_domain);
    CREATE INDEX idx_pages_website_id ON pages(website_id);
    CREATE INDEX idx_contacts_business_id ON contacts(business_id);
    CREATE INDEX idx_contacts_website_id ON contacts(website_id);
    CREATE INDEX idx_audits_website_id ON audits(website_id);
    CREATE INDEX idx_signals_business_id ON signals(business_id);
    CREATE INDEX idx_signals_website_id ON signals(website_id);
    CREATE INDEX idx_signals_audit_id ON signals(audit_id);
    CREATE INDEX idx_signals_name ON signals(name);
    CREATE INDEX idx_signals_category ON signals(category);
    CREATE INDEX idx_signals_detected_at ON signals(detected_at);
    CREATE INDEX idx_scores_audit_id ON scores(audit_id);
    """,
    ),
    Migration(
        2,
        "signal_query_indexes",
        """
    CREATE INDEX idx_signals_website_category_detected
        ON signals(website_id, category, detected_at DESC);
    CREATE INDEX idx_signals_website_name_detected
        ON signals(website_id, name, detected_at DESC);
    CREATE INDEX idx_audits_website_started
        ON audits(website_id, started_at DESC);
        """,
    ),
    Migration(
        3,
        "discovery_observation_details",
        """
    ALTER TABLE discovery_candidates ADD COLUMN canonical_domain TEXT NOT NULL DEFAULT '';
    ALTER TABLE discovery_candidates ADD COLUMN provider TEXT NOT NULL DEFAULT '';
    ALTER TABLE discovery_candidates ADD COLUMN classification TEXT NOT NULL DEFAULT 'unknown';
    ALTER TABLE discovery_candidates ADD COLUMN filter_reason TEXT;
    ALTER TABLE discovery_candidates ADD COLUMN title TEXT;
    ALTER TABLE discovery_candidates ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}';
    CREATE INDEX idx_discovery_candidates_domain
        ON discovery_candidates(canonical_domain);
    CREATE INDEX idx_discovery_candidates_category_location
        ON discovery_candidates(category, location, discovered_at);
    """,
    ),
    Migration(
        4,
        "phase3_crawl_evidence",
        """
    ALTER TABLE pages ADD COLUMN audit_id TEXT REFERENCES audits(id);
    ALTER TABLE pages ADD COLUMN requested_url TEXT;
    ALTER TABLE pages ADD COLUMN final_url TEXT;
    ALTER TABLE pages ADD COLUMN elapsed_ms REAL;
    ALTER TABLE pages ADD COLUMN content_length INTEGER;
    ALTER TABLE pages ADD COLUMN content_hash TEXT;
    ALTER TABLE pages ADD COLUMN language TEXT;
    ALTER TABLE pages ADD COLUMN redirect_chain_json TEXT NOT NULL DEFAULT '[]';
    ALTER TABLE contacts ADD COLUMN audit_id TEXT REFERENCES audits(id);
    CREATE INDEX idx_pages_audit_id ON pages(audit_id);
    CREATE INDEX idx_contacts_audit_id ON contacts(audit_id);
    """,
    ),
    Migration(
        5,
        "append_only_versioned_scores",
        """
    ALTER TABLE scores RENAME TO scores_v4;
    CREATE TABLE scores (
        id TEXT PRIMARY KEY, audit_id TEXT NOT NULL REFERENCES audits(id),
        score_type TEXT NOT NULL, score REAL NOT NULL CHECK(score BETWEEN 0 AND 100),
        confidence REAL NOT NULL CHECK(confidence BETWEEN 0 AND 1),
        positive_signal_ids_json TEXT NOT NULL, negative_signal_ids_json TEXT NOT NULL,
        reason TEXT, calculated_at TEXT NOT NULL, scorer_version TEXT NOT NULL DEFAULT 'legacy',
        configuration_version TEXT NOT NULL DEFAULT 'legacy',
        configuration_hash TEXT NOT NULL DEFAULT '', metadata_json TEXT NOT NULL DEFAULT '{}'
    );
    INSERT INTO scores (
        id,audit_id,score_type,score,confidence,positive_signal_ids_json,
        negative_signal_ids_json,reason,calculated_at
    ) SELECT id,audit_id,score_type,score,confidence,positive_signal_ids_json,
        negative_signal_ids_json,reason,calculated_at FROM scores_v4;
    DROP TABLE scores_v4;
    CREATE INDEX idx_scores_audit_id ON scores(audit_id);
    CREATE INDEX idx_scores_audit_type_calculated
        ON scores(audit_id,score_type,calculated_at DESC);
    """,
    ),
)
