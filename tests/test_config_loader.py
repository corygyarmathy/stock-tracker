import argparse
import os
import tempfile
from pathlib import Path

import pytest
import yaml

from stock_tracker.config import AppConfig, ConfigLoader


def test_load_app_config(monkeypatch, temp_config_dir):
    monkeypatch.setenv("ENV", "dev")
    monkeypatch.chdir(temp_config_dir.parent)

    config = ConfigLoader.load_app_config()
    assert isinstance(config, AppConfig)
    assert config.env == "dev"
    assert config.log_level == "DEBUG"  # overridden
    assert config.yf_max_requests == 100
    assert config.yf_request_interval_seconds == 1.5


def test_config_with_cli_overrides(monkeypatch, temp_config_dir):
    monkeypatch.setenv("ENV", "dev")
    monkeypatch.chdir(temp_config_dir.parent)

    overrides = argparse.Namespace(
        db_path="./cli_override.db",
        log_level="WARNING",
        yf_max_requests=None,
        env=None,
        csv_path=None,
        log_config_path=None,
        log_file_path=None,
        yf_request_interval_seconds=None,
        project_root=None,
    )
    override_dict = {k: v for k, v in vars(overrides).items() if v is not None}
    config = ConfigLoader.load_app_config(overrides=override_dict)

    assert config.db_path == Path("./cli_override.db")
    assert config.log_level == "WARNING"
    assert config.yf_max_requests == 100


def test_missing_required_config(monkeypatch, tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.base.yaml").write_text("")
    (config_dir / "config.dev.yaml").write_text("env: dev")

    monkeypatch.setenv("ENV", "dev")
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="Missing required config value: 'db_path'"):
        _ = ConfigLoader.load_app_config()


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

    with pytest.raises(TypeError, match="Invalid type for 'yf_max_requests'"):
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
