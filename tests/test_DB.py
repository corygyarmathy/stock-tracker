from config import DEFAULT_DB_NAME
from db import Database
import pytest
from pytest_mock import MockerFixture


@pytest.fixture
def test_db():
    db: Database = Database(DEFAULT_DB_NAME)
    with db:
        db.create_tables_if_not_exists()
        yield db
