import argparse
import os
import tempfile
from pathlib import Path

import pytest
import yaml

from config import AppConfig, ConfigLoader


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
