import argparse
import os
import tempfile
from pathlib import Path

import pytest
import yaml

from stock_tracker.config import AppConfig, ConfigLoader


def test_load_app_config(app_config):
    """Test that config is properly loaded from actual files."""
    assert isinstance(app_config, AppConfig)
    assert app_config.env == "test"
    assert app_config.log_level == "DEBUG"
    assert app_config.yf_max_requests == 2000
    assert app_config.yf_request_interval_seconds == 0.1


def test_isolated_config_modifications(isolated_config_environment):
    """Test with modified config files."""
    config_dir = isolated_config_environment["config_dir"]

    # Modify a config file for this specific test
    test_config_path = config_dir / "config.test.yaml"
    with open(test_config_path, "r") as f:
        config_data = yaml.safe_load(f) or {}

    # Change a value
    config_data["log_level"] = "TRACE"

    with open(test_config_path, "w") as f:
        yaml.dump(config_data, f)

    # Now load the config, which will use our modified file
    config: AppConfig = ConfigLoader.load_app_config()
    assert config.log_level == "TRACE"


def test_config_with_cli_overrides(config_with_cli_overrides):
    """Test that CLI arguments properly override config values."""
    overrides: dict[str, str | int] = {"log_level": "CRITICAL", "yf_max_requests": 5000}

    config: AppConfig = config_with_cli_overrides(overrides)

    assert config.log_level == "CRITICAL"

def test_invalid_type_in_config(monkeypatch, tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    (config_dir / "config.base.yaml").write_text("yf_max_requests: not_an_int")
    (config_dir / "config.dev.yaml").write_text("""
env: dev
db_path: ./dev.db
csv_path: ./import.csv
log_config_path: ./config/logging_config.yaml
log_file_path: ./tickers.log
log_level: DEBUG
yf_request_interval_seconds: 1.5
""")

    monkeypatch.setenv("ENV", "dev")
    monkeypatch.chdir(tmp_path)
    assert config.yf_max_requests == 5000

    with pytest.raises(TypeError, match="Invalid type for 'yf_max_requests'"):
def test_missing_required_config(isolated_config_environment):
    """Test with missing config files."""
    config_dir = isolated_config_environment["config_dir"]

    # Modify a config file for this specific test
    test_config_path = config_dir / "config.test.yaml"

    with open(test_config_path, "r") as f:
        config_data = yaml.safe_load(f) or {}

    # Remove a value
    del config_data["db_path"]

    with open(test_config_path, "w") as f:
        yaml.dump(config_data, f)

    with pytest.raises(ValueError, match="Missing required config value: 'db_path'"):
        _ = ConfigLoader.load_app_config()


def test_dict_to_config_success(tmp_path):
    data = {
        "project_root": str(tmp_path),
        "env": "test",
        "db_path": str(tmp_path / "test.db"),
        "csv_path": str(tmp_path / "import.csv"),
        "log_config_path": str(tmp_path / "logconf.yaml"),
        "log_file_path": str(tmp_path / "app.log"),
        "log_level": "INFO",
        "yf_max_requests": 99,
        "yf_request_interval_seconds": 1.0,
    }
    config = ConfigLoader._dict_to_config(data, AppConfig)
    assert isinstance(config, AppConfig)
    assert config.db_path == tmp_path / "test.db"


def test_dict_to_config_invalid_type():
    bad_data = {
        "project_root": "./",
        "env": "test",
        "db_path": "./db.sqlite",
        "csv_path": "./input.csv",
        "log_config_path": "./log.yaml",
        "log_file_path": "./log.txt",
        "log_level": "INFO",
        "yf_max_requests": "not-a-number",
        "yf_request_interval_seconds": 1.0,
    }
    with pytest.raises(TypeError, match="Invalid type for 'yf_max_requests'"):
        _ = ConfigLoader._dict_to_config(bad_data, AppConfig)
