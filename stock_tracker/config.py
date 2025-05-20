# config.py
import logging
import os
import yaml
import argparse
from dataclasses import dataclass, fields, MISSING
from pathlib import Path
from typing import (
    Any,
    get_type_hints,
    override,
)

from stock_tracker.utils.type_utils import convert_type


logger: logging.Logger = logging.getLogger(__name__)


def get_env() -> str:
    # Try to get ENV from environment variable, default to 'prod'
    is_test_environment: bool = bool(os.getenv("PYTEST_CURRENT_TEST"))
    env: str = "test" if is_test_environment else os.getenv("STOCK_TRACKER_ENV", "prod").lower()
    logger.debug(f"Using environment: {env}")
    return env


@dataclass
class AppConfig:
    db_path: Path
    csv_path: Path
    log_config_path: Path
    log_file_path: Path
    log_level: str
    yf_max_requests: int
    yf_request_interval_seconds: int
    yf_cache_path: str
    yf_cache_expiry: int


class ConfigLoader:
    """Load and manage application configuration from multiple sources."""

    @staticmethod
    def _find_config_directory() -> Path:
        """Find a valid configuration directory from several possible locations."""
        possible_config_dirs: list[Path] = [
            Path("config"),  # Current directory
            Path.home() / ".stock-tracker" / "config",  # User's home directory
            Path("/etc/stock-tracker/config"),  # System-wide config
            Path(__file__).parent.parent / "config",  # Package directory
        ]

        # Use the first existing directory, or fall back to 'config'
        for directory in possible_config_dirs:
            if directory.exists():
                logger.debug(f"Using config directory: {directory}")
                return directory

        # If no config directory exists, return the default
        logger.warning("No config directory found, using 'config'")
        return Path("config")

    @staticmethod
    def _load_merged_yaml(
        env: str, config_dir: Path | None = None, file: Path | None = None
    ) -> dict[str, Any]:
        """Get appropriate config files as a dict, merging nested items."""
        if config_dir is None:
            config_dir: Path = ConfigLoader._find_config_directory()

        def load_yaml(path: Path) -> dict[str, Any]:
            if path.exists():
                with open(path, "r") as f:
                    return yaml.safe_load(f) or {}
            else:
                logger.debug(f"Config file not found: {path}")
                return {}

        base_path: Path = config_dir / "config.base.yaml"
        base_config: dict[str, Any] = load_yaml(base_path)

        env_path: Path = config_dir / f"config.{env}.yaml"
        env_config = load_yaml(env_path)

        # If neither config file exists, use default minimal config
        if not base_config and not env_config:
            logger.warning(f"No config files found. Using built-in defaults.")
            print(f"No config files found. Using built-in defaults.")
            return ConfigLoader._get_default_config()

        merged_config = ConfigLoader._deep_merge(base_config, env_config)
        if file:
            override_config: dict[str, Any] = load_yaml(file)
            merged_config = ConfigLoader._deep_merge(merged_config, override_config)

        return merged_config

    @staticmethod
    def _get_default_config() -> dict[str, Any]:
        """Return sensible default configuration values if no config files exist."""
        return {
            "db_path": "stocktracker.db",
            "csv_path": "import.csv",
            "log_config_path": "logging_config.yaml",
            "log_file_path": "stock_tracker.log",
            "log_level": "INFO",
            "yf_max_requests": 2,
            "yf_request_interval_seconds": 10,
            "yf_cache_path": "yfinance.cache",
            "yf_cache_expiry": 86400,  # 24 hours
        }

    @staticmethod
    def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """Recursively merge two dictionaries. Values in `override` take precedence."""
        result: dict[str, Any] = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigLoader._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    @staticmethod
    def _dict_to_config(data: dict[str, Any], config_class: type[AppConfig]) -> AppConfig:
        """Build AppConfig class object from input dict, validating and coercing data to fit the defined parameter types."""
        type_hints: dict[str, Any] = get_type_hints(config_class)
        init_args: dict[str, Any] = {}

        for field in fields(config_class):
            name: str = field.name
            expected_type = type_hints.get(name, Any)
            value = data.get(name, MISSING)

            if value is MISSING:
                if field.default is not MISSING:
                    value = field.default
                elif field.default_factory is not MISSING:  # type: ignore
                    value = field.default_factory()  # type: ignore
                else:
                    raise ValueError(f"Missing required config value: '{name}'")

            try:
                init_args[name] = convert_type(value, expected_type)
            except Exception as e:
                raise TypeError(
                    f"Invalid type for '{name}': expected {expected_type}, got {type(value)}. Error: {e}"
                )

        return config_class(**init_args)

    @staticmethod
    def load_app_config(
        env: str, overrides: dict[str, Any] | None = None, config_file: Path | None = None
    ) -> AppConfig:
        """
        Builds an AppConfig object with smart environment detection.

        The configuration is loaded in this order of precedence:
        1. Default built-in values
        2. Base config file (config.base.yaml)
        3. Environment-specific config file (config.{env}.yaml)
        4. Custom config file (if specified)
        5. CLI argument overrides

        For development purposes only, environment can be selected with STOCK_TRACKER_ENV variable.

        Args:
            overrides: Optional dictionary of configuration overrides (typically from CLI)
            config_file: Optional path to a specific config file to use

        Returns:
            An AppConfig object with the merged configuration
        """

        # Load and merge YAML configurations
        merged_config: dict[str, Any] = ConfigLoader._load_merged_yaml(env, file=config_file)

        # If provided CLI overrides, merge with config
        if overrides:
            merged_config = ConfigLoader._deep_merge(merged_config, overrides)

        try:
            return ConfigLoader._dict_to_config(merged_config, AppConfig)
        except TypeError as e:
            raise TypeError(f"{e}")

    @staticmethod
    def args_to_overrides(args: argparse.Namespace) -> dict[str, Any]:
        """Convert argparse Namespace to a dictionary of overrides."""
        return {k: v for k, v in vars(args).items() if v is not None}
