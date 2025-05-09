import pytest
from pytest_mock import MockerFixture

from stock_tracker.config import AppConfig
from stock_tracker.db import Database


def test_create_tables(app_config: AppConfig, test_db: Database):
    """Test tables are created correctly."""
    # Check tables exist by querying sqlite_master
    tables = test_db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    table_names = [table[0] for table in tables]

    assert "stocks" in table_names
    assert "stock_orders" in table_names
    assert "stock_info" in table_names
    assert "corporate_actions" in table_names
    assert "fx_rates" in table_names
