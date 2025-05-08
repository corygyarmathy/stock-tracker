from pathlib import Path

import pytest
import yaml

from stock_tracker.config import AppConfig
@pytest.fixture(scope="session", autouse=True)
def ensure_test_environment(monkeypatch):
    """Ensure we're using the test environment for all tests."""
    # This will override any ENV setting from .env.test if needed
    monkeypatch.setenv("ENV", "test")

    # Create required test fixtures directory if it doesn't exist
    # Path("tests/fixtures").mkdir(parents=True, exist_ok=True)

    yield


@pytest.fixture(scope="function", autouse=True)
def reset_app_config():
    """Reset AppConfig singleton before and after each test."""
    # Reset the singleton before test
    if hasattr(AppConfig, "_instance") and AppConfig._instance is not None:
        AppConfig._reset()

    yield

    # Reset after test
    if hasattr(AppConfig, "_instance") and AppConfig._instance is not None:
        AppConfig._reset()
@pytest.fixture
def temp_config_dir(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    (config_dir / "config.base.yaml").write_text(
        yaml.dump(
            {
                "log_level": "INFO",
                "yf_max_requests": 100,
                "yf_request_interval_seconds": 1.5,
            }
        )
    )
    (config_dir / "config.dev.yaml").write_text(
        yaml.dump(
            {
                "env": "dev",
                "db_path": "./dev.db",
                "csv_path": "./import.csv",
                "log_config_path": "./config/logging.yaml",
                "log_file_path": "./tickers.log",
                "log_level": "DEBUG",
            }
        )
    )

    return config_dir
def app_config() -> AppConfig:
    """
    Load the AppConfig through the normal ConfigLoader mechanism using
    the actual config files.
    """
    config: AppConfig = ConfigLoader.load_app_config()
    AppConfig.set(instance=config)
    return AppConfig.get()


