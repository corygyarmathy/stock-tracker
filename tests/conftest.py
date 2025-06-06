import os
from pathlib import Path
from typing import Any, Callable
from unittest.mock import MagicMock, patch

import pytest
import yaml

from stock_tracker.config import AppConfig, ConfigLoader
from stock_tracker.db import Database
from stock_tracker.repositories.corporate_actions_repository import CorporateActionRepository
from stock_tracker.repositories.fx_rate_repository import FxRateRepository
from stock_tracker.repositories.order_repository import OrderRepository
from stock_tracker.repositories.stock_info_repository import StockInfoRepository
from stock_tracker.repositories.stock_repository import StockRepository


@pytest.fixture(scope="session", autouse=True)
def env():
    """Ensure we're using the test environment for all tests."""
    env: str = "test"
    return env


@pytest.fixture(scope="function")
def app_config(env: str) -> AppConfig:
    """Load a test configuration"""
    return ConfigLoader.load_app_config(env)


@pytest.fixture
def mock_yfinance_session():
    """Create a mocked yfinance session."""
    with patch("stock_tracker.tickers.get_yfinance_session") as mock_session:
        session: MagicMock = MagicMock()
        mock_session.return_value = session
        yield session


@pytest.fixture
def test_db(app_config: AppConfig):
    """Create an in-memory test database. Prevents the need to reset the DB in-between tests."""
    db_path: Path = app_config.db_path
    with Database(db_path) as db:
        db.create_tables_if_not_exists()
        yield db


@pytest.fixture
def stock_repo(test_db) -> StockRepository:
    return StockRepository(test_db)


@pytest.fixture
def stock_info_repo(test_db) -> StockInfoRepository:
    return StockInfoRepository(test_db)


@pytest.fixture
def order_repo(test_db) -> OrderRepository:
    return OrderRepository(test_db)


@pytest.fixture
def corp_action_repo(test_db) -> CorporateActionRepository:
    return CorporateActionRepository(test_db)


@pytest.fixture
def fx_rate_repo(test_db) -> FxRateRepository:
    return FxRateRepository(test_db)


@pytest.fixture
def isolated_config_environment(tmp_path: Path):
    """
    Create a completely isolated test environment with copied config files.
    Use this when you need to modify config files for specific tests.
    Generator that yields: dict[str,Path]
    - "config_dir": test_config_dir, "temp_dir": tmp_path
    """
    # Create a test config directory
    test_config_dir: Path = tmp_path / "config"
    test_config_dir.mkdir()
    # Path("tests/fixtures").mkdir(parents=True, exist_ok=True)

    # Copy real config files to test directory
    real_config_dir: Path = Path("config")
    for config_file in real_config_dir.glob("config*.yaml"):
        with open(config_file, "r") as src_file:
            content: dict[str, Any] = yaml.safe_load(src_file) or {}

        # Modify paths in the config to use the temp directory
        if "csv_path" in content:
            content["csv_path"] = str(tmp_path / "test_import.csv")
        if "log_file_path" in content:
            content["log_file_path"] = str(tmp_path / "logs/test.log")

        # Write modified config to the test directory
        with open(test_config_dir / config_file.name, "w") as dest_file:
            yaml.dump(content, dest_file)

    # Also copy logging config if it exists
    log_config: Path = real_config_dir / "logging_config.yaml"
    if log_config.exists():
        with open(log_config, "r") as src_file:
            content = yaml.safe_load(src_file) or {}
        with open(test_config_dir / log_config.name, "w") as dest_file:
            yaml.dump(content, dest_file)

    # Store the original method to avoid recursion
    original_load_merged_yaml = ConfigLoader._load_merged_yaml

    # Define a wrapper that uses the test directory
    def custom_load_merged_yaml(env: str, config_dir: Path | None = None, file: Path | None = None):
        return original_load_merged_yaml(env, config_dir=test_config_dir)

    # Patch ConfigLoader to use our test directory
    with patch(
        "stock_tracker.config.ConfigLoader._load_merged_yaml", side_effect=custom_load_merged_yaml
    ):
        yield {"config_dir": test_config_dir, "temp_dir": tmp_path}


@pytest.fixture
def config_with_cli_overrides() -> Callable[..., AppConfig]:
    """Fixture for testing CLI argument overrides."""

    def _config_with_overrides(env: str, overrides: dict[str, Any]) -> AppConfig:
        """Load config with the specified CLI overrides."""
        config: AppConfig = ConfigLoader.load_app_config(env=env, overrides=overrides)
        return config

    return _config_with_overrides


@pytest.fixture(autouse=True)
def no_sleep():
    """Patch time.sleep for all tests to avoid unnecessary waiting."""
    with patch("time.sleep", return_value=None):
        yield
