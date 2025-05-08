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


def app_config() -> AppConfig:
    """
    Load the AppConfig through the normal ConfigLoader mechanism using
    the actual config files.
    """
    config: AppConfig = ConfigLoader.load_app_config()
    AppConfig.set(instance=config)
    return AppConfig.get()


@pytest.fixture
def mock_yfinance_session():
    """Create a mocked yfinance session."""
    with patch("stock_tracker.tickers.get_yfinance_session") as mock_session:
        session: MagicMock = MagicMock()
        mock_session.return_value = session
        yield session


@pytest.fixture
def isolated_config_environment(tmp_path: Path, monkeypatch):
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

    # Set ENV to test
    monkeypatch.setenv("ENV", "test")

    # Patch ConfigLoader to use our test directory
    with patch(
        "stock_tracker.config.ConfigLoader._load_merged_yaml",
        side_effect=lambda env, config_dir=None: ConfigLoader._load_merged_yaml(
            env, test_config_dir
        ),
    ):
        yield {"config_dir": test_config_dir, "temp_dir": tmp_path}


