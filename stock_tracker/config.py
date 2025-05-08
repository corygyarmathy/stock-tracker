# config.py
import logging
import os
import yaml
import argparse
from dataclasses import dataclass, fields, MISSING
from pathlib import Path
from typing import (
    Any,
    ClassVar,
    Self,
    get_origin,
    get_type_hints,
)

from stock_tracker.type_utils import convert_type


logger: logging.Logger = logging.getLogger(__name__)


def load_environment_variables() -> bool:
    """Load environment variables from the appropriate .env file."""
    try:
        from dotenv import load_dotenv

        # Use .env.test when running under pytest
        is_test_environment: bool = bool(os.getenv("PYTEST_CURRENT_TEST"))
        env_file = ".env.test" if is_test_environment else ".env"
        logger.debug(f"env_file is {env_file}")

        # Load the environment file and return success/failure
        return load_dotenv(dotenv_path=env_file)
    except ImportError:
        # Only catch ImportError for dotenv, not other import errors
        return False


# Load environment variables at module import time
_ = load_environment_variables()
logger.debug(f"Loaded environment variables from selected env_file.")


@dataclass
class AppConfig:
    env: str
    db_path: Path
    csv_path: Path
    log_config_path: Path
    log_file_path: Path
    log_level: str
    yf_max_requests: int
    yf_request_interval_seconds: float

    _instance: ClassVar[Self | None] = None  # private singleton instance

    @classmethod
    def get(cls) -> Self:
        """Return the current singleton instance, or raise if not set."""
        if cls._instance is None:
            raise RuntimeError("AppConfig has not been initialised.")
        return cls._instance

    @classmethod
    def set(cls, instance: Self) -> None:
        """Set the singleton instance from an AppConfig object. Can only be set once."""
        if cls._instance is not None:
            logger.error(f"AppConfig.set() called when AppConfig instance was already set.")
            raise RuntimeError("AppConfig.set() called when AppConfig instance was already set.")
        logger.debug("Setting AppConfig._instance")
        cls._instance = instance

    @classmethod
    def _reset(cls) -> None:
        """Testing-only method: reset the singleton instance."""
        if os.getenv("ENV") != "test":
            logger.error(
                "AppConfig._reset() called when ENV != test. Should only be used in testing ENV."
            )
            raise RuntimeError(
                "AppConfig._reset() called when ENV != test. Should only be used in testing ENV."
            )
        logger.debug("Resetting AppConfig._instance")
        cls._instance = None


# TODO: convert into generic ConfigLoader, not just for AppConfig
class ConfigLoader:
    @staticmethod
    def _load_merged_yaml(env: str, config_dir: Path = Path("config")) -> dict[str, Any]:
        """Get appropriate config.{env}.yaml files as a dict, merging nested items."""
        base_path: Path = config_dir / "config.base.yaml"
        env_path: Path = config_dir / f"config.{env}.yaml"

        def load_yaml(path: Path) -> dict[str, Any]:
            if path.exists():
                with open(path, "r") as f:
                    return yaml.safe_load(f) or {}
            return {}

        base_config: dict[str, Any] = load_yaml(base_path)
        env_config: dict[str, Any] = load_yaml(env_path)

        return ConfigLoader._deep_merge(base_config, env_config)

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
    def load_app_config(overrides: dict[str, Any] | None = None) -> AppConfig:
        """Builds an AppConfig object based on the ENV environment variable, set within the .env file"""
        env: str = os.getenv("ENV", "dev").lower()
        merged_config: dict[str, Any] = ConfigLoader._load_merged_yaml(env)

        # If provided CLI overrides, nested (deep) merge with merged_config
        if overrides:
            merged_config = ConfigLoader._deep_merge(merged_config, overrides)

        return ConfigLoader._dict_to_config(merged_config, AppConfig)

    @staticmethod
    def build_arg_parser(config_class: type[AppConfig]) -> argparse.ArgumentParser:
        """Dynamically build an ArgumentParser based on a dataclass like AppConfig."""
        parser: argparse.ArgumentParser = argparse.ArgumentParser(description="Stock Tracker CLI")

        for field in fields(config_class):
            # Skip private fields and ClassVars
            if field.name.startswith("_") or get_origin(field.type) is ClassVar:
                continue

            arg_name: str = f"--{field.name.replace('_', '-')}"  # eg. db_path -> --db-path
            arg_type = field.type

            # Optional:  make type adjustments here as needed
            if arg_type is Path:
                arg_type = str  # Accept paths as strings from CLI
            elif arg_type is bool:
                # Special handling for booleans: use 'store_true' action
                _ = parser.add_argument(arg_name, action="store_true", help=f"Enable {field.name}")
                continue

            _ = parser.add_argument(
                arg_name,
                type=arg_type,
                default=None,  # So you can know if user passed it
                help=f"Override {field.name}",
            )

        return parser

    @staticmethod
    def args_to_overrides(args: argparse.Namespace) -> dict[str, Any]:
        return {k: v for k, v in vars(args).items() if v is not None}
