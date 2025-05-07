# config.py
import os
import yaml
import argparse
from dataclasses import dataclass, fields, MISSING, replace
from pathlib import Path
from typing import (
    Any,
    ClassVar,
    Self,
    get_origin,
    get_type_hints,
)

from type_utils import convert_type


# Optional: load .env if using python-dotenv
try:
    from dotenv import load_dotenv

    env_file: str = ".env.test" if os.getenv("PYTEST_CURRENT_TEST") else ".env"
    _ = load_dotenv(dotenv_path=env_file)
except ImportError:
    pass


@dataclass
class AppConfig:
    project_root: Path
    env: str
    db_path: Path
    csv_path: Path
    log_config_path: Path
    log_file_path: Path
    log_level: str
    yf_max_requests: str
    yf_request_interval_seconds: str

    _instance: ClassVar[Self | None] = None  # private singleton instance

    @classmethod
    def get(cls) -> Self | None:
        """Return the current singleton instance if initialised, None if not."""
        return cls._instance

    @classmethod
    def set(cls, instance: Self) -> None:
        """Set the singleton instance from an AppConfig object. Can only be set once."""
        if cls._instance is not None:
            raise RuntimeError("AppConfig instance already set.")
        cls._instance = instance

    @classmethod
    def _reset(cls) -> None:
        """Testing-only method: reset the singleton instance."""
        if os.getenv("ENV") != "test":
            raise RuntimeError(
                "AppConfig._reset() should only be used in test environment."
            )
        cls._instance = None


# TODO: convert into generic ConfigLoader, not just for AppConfig
class ConfigLoader:
    @staticmethod
    def _load_merged_yaml(
        env: str, config_dir: Path = Path("config")
    ) -> dict[str, Any]:
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
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = ConfigLoader._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    @staticmethod
    def _dict_to_config(
        data: dict[str, Any], config_class: type[AppConfig]
    ) -> AppConfig:
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
        parser: argparse.ArgumentParser = argparse.ArgumentParser(
            description="Stock Tracker CLI"
        )

        for field in fields(config_class):
            # Skip private fields and ClassVars
            if field.name.startswith("_") or get_origin(field.type) is ClassVar:
                continue

            arg_name: str = (
                f"--{field.name.replace('_', '-')}"  # eg. db_path -> --db-path
            )
            arg_type = field.type

            # Optional:  make type adjustments here as needed
            if arg_type is Path:
                arg_type = str  # Accept paths as strings from CLI
            elif arg_type is bool:
                # Special handling for booleans: use 'store_true' action
                _ = parser.add_argument(
                    arg_name, action="store_true", help=f"Enable {field.name}"
                )
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
