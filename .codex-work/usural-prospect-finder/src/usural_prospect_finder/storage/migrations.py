"""Small transactional migration runner."""

import sqlite3

from .schema import MIGRATIONS, Migration


def migrate(connection: sqlite3.Connection) -> None:
    """Apply all pending migrations atomically and record their versions."""
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute(
        """CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    connection.commit()
    versions = [migration.version for migration in MIGRATIONS]
    if versions != sorted(versions) or len(versions) != len(set(versions)):
        raise RuntimeError("migration versions must be unique and ordered")
    applied = {row[0] for row in connection.execute("SELECT version FROM schema_migrations")}
    unknown = applied - set(versions)
    if unknown:
        raise RuntimeError(f"database contains unknown migration versions: {sorted(unknown)}")
    for migration in MIGRATIONS:
        if migration.version not in applied:
            _apply_migration(connection, migration)


def _apply_migration(connection: sqlite3.Connection, migration: Migration) -> None:
    """Apply schema statements and history insertion in one transaction."""
    try:
        connection.execute("BEGIN IMMEDIATE")
        for statement in _statements(migration.sql):
            connection.execute(statement)
        connection.execute(
            "INSERT INTO schema_migrations(version) VALUES (?)", (migration.version,)
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def _statements(script: str) -> list[str]:
    """Split complete SQLite statements without relying on filenames or ordering."""
    statements: list[str] = []
    buffer = ""
    for character in script:
        buffer += character
        if sqlite3.complete_statement(buffer):
            if statement := buffer.strip():
                statements.append(statement)
            buffer = ""
    if buffer.strip():
        raise ValueError("migration contains an incomplete SQL statement")
    return statements
