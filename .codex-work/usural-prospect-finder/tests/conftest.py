from pathlib import Path

import pytest
from typer.testing import CliRunner

from usural_prospect_finder.models import Business, Website
from usural_prospect_finder.models.common import Location
from usural_prospect_finder.storage import SQLiteRepository


@pytest.fixture
def repository(tmp_path: Path) -> SQLiteRepository:
    repo = SQLiteRepository(tmp_path / "test.sqlite3")
    repo.initialize()
    return repo


@pytest.fixture
def business() -> Business:
    return Business(
        name="Fixture Studio",
        category="architects",
        location=Location("Barcelona", city="Barcelona"),
    )


@pytest.fixture
def website(business: Business) -> Website:
    return Website(
        business_id=business.id,
        url="https://example.com/",
        canonical_domain="example.com",
        scheme="https",
    )


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()
