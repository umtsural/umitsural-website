import sqlite3
from contextlib import closing

import pytest

from usural_prospect_finder.storage.migrations import _apply_migration
from usural_prospect_finder.storage.schema import Migration


def test_failed_migration_rolls_back_schema_and_history() -> None:
    with closing(sqlite3.connect(":memory:")) as connection:
        connection.execute(
            "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT)"
        )
        migration = Migration(
            99,
            "intentional_failure",
            "CREATE TABLE temporary_table (id TEXT); INVALID SQL;",
        )
        with pytest.raises(sqlite3.OperationalError):
            _apply_migration(connection, migration)
        table = connection.execute(
            "SELECT name FROM sqlite_master WHERE name='temporary_table'"
        ).fetchone()
        history = connection.execute(
            "SELECT version FROM schema_migrations WHERE version=99"
        ).fetchone()
    assert table is None
    assert history is None
