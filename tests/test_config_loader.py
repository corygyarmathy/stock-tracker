import pytest
import yaml

from stock_tracker.config import AppConfig, ConfigLoader


def test_load_app_config(app_config):
    """Test that config is properly loaded from actual files."""
    assert isinstance(app_config, AppConfig)
    assert app_config.log_level == "DEBUG"
    assert app_config.yf_max_requests == 2000
    assert app_config.yf_request_interval_seconds == 1


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
    assert config.yf_max_requests == 5000


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


def test_invalid_type_in_config(isolated_config_environment):
    """Test with missing config files."""
    config_dir = isolated_config_environment["config_dir"]

    # Modify a config file for this specific test
    test_config_path = config_dir / "config.test.yaml"

    with open(test_config_path, "r") as f:
        config_data = yaml.safe_load(f) or {}

    # Set to invalid type
    config_data["yf_max_requests"] = "not-a-number"

    with open(test_config_path, "w") as f:
        yaml.dump(config_data, f)

    with pytest.raises(TypeError):
        _ = ConfigLoader.load_app_config()
