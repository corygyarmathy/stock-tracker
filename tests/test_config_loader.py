import argparse
import os
import tempfile
from pathlib import Path

import pytest
import yaml

from config import AppConfig, ConfigLoader


def test_load_app_config(monkeypatch, temp_config_dir):
    # Set ENV to dev
    monkeypatch.setenv("ENV", "dev")

    # Override config path lookup in ConfigLoader
    monkeypatch.setattr(
        "stock_tracker.config_loader.Path", lambda p=".": temp_config_dir / p
    )

    config: AppConfig = ConfigLoader.load_app_config()

    assert isinstance(config, AppConfig)
    assert config.env == "dev"
    assert config.db_path == Path("./dev.db")
    assert config.csv_path == Path("./import.csv")
    assert config.log_file_path == Path("./tickers.log")
    assert config.log_level == "DEBUG"  # overridden
    assert config.yf_max_requests == 100
    assert config.yf_request_interval_seconds == 1.5


def test_config_with_cli_overrides(monkeypatch, temp_config_dir):
    # Simulate ENV=dev
    monkeypatch.setenv("ENV", "dev")

    # Redirect config path logic to test config directory
    monkeypatch.setattr(
        "stock_tracker.config_loader.Path", lambda p=".": temp_config_dir / p
    )

    # Simulated CLI override (e.g., from argparse)
    overrides = argparse.Namespace(
        db_path="./cli_override.db",
        log_level="WARNING",  # Overrides 'DEBUG'
        yf_max_requests=None,  # Let it fall back to YAML
    )

    # Convert Namespace to dict for use in loader
    override_dict = {k: v for k, v in vars(overrides).items() if v is not None}

    config = ConfigLoader.load_app_config(overrides=override_dict)

    assert config.db_path == Path("./cli_override.db")
    assert config.log_level == "WARNING"
    assert config.csv_path == Path("./import.csv")  # from YAML
    assert config.yf_max_requests == 100  # from base.yaml


def test_missing_required_config(monkeypatch, temp_config_dir):
    # Redirect config path logic to test config directory
    monkeypatch.setattr(
        "stock_tracker.config_loader.Path", lambda p=".": temp_config_dir / p
    )

    # Missing required field: `db_path`
    (temp_config_dir / "base.yaml").write_text(yaml.dump({}))
    (temp_config_dir / "dev.yaml").write_text(
        yaml.dump(
            {
                "env": "dev"
                # Intentionally leaving out db_path, csv_path, etc.
            }
        )
    )

    monkeypatch.setenv("ENV", "dev")
    monkeypatch.setattr(
        "stock_tracker.config_loader.Path", lambda p=".": temp_config_dir / p
    )

    with pytest.raises(ValueError, match="Missing config value for 'db_path'"):
        _ = ConfigLoader.load_app_config()


def test_invalid_type_in_config(monkeypatch, temp_config_dir):
    # Redirect config path logic to test config directory
    monkeypatch.setattr(
        "stock_tracker.config_loader.Path", lambda p=".": temp_config_dir / p
    )

    # `yf_max_requests` should be an int, not a string
    (temp_config_dir / "base.yaml").write_text(
        yaml.dump({"yf_max_requests": "not_an_int"})
    )
    (temp_config_dir / "dev.yaml").write_text(
        yaml.dump(
            {
                "env": "dev",
                "db_path": "./dev.db",
                "csv_path": "./import.csv",
                "log_file_path": "./tickers.log",
                "log_level": "DEBUG",
                "yf_request_interval_seconds": 1.5,
            }
        )
    )

    monkeypatch.setenv("ENV", "dev")
    monkeypatch.setattr(
        "stock_tracker.config_loader.Path", lambda p=".": temp_config_dir / p
    )

    with pytest.raises(ValueError, match="invalid literal for int()"):
        _ = ConfigLoader.load_app_config()
