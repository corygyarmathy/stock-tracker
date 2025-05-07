import pytest
from pytest_mock import MockerFixture

from stock_tracker.config import AppConfig
from stock_tracker.db import Database

@pytest.fixture
def test_db():
    db: Database = Database(DEFAULT_DB_NAME)
    with db:
        db.create_tables_if_not_exists()
        yield db
