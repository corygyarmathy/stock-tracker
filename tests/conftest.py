from pathlib import Path

import pytest
import yaml

from stock_tracker.config import AppConfig


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
