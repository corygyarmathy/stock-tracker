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
        """Return the current singleton instance."""
        # if cls._instance is None:
        #     cls._instance = cls.from_env()
        return cls._instance


class ConfigLoader:
    @staticmethod
    def _load_merged_yaml(
        env: str, config_dir: Path = Path("config")
    ) -> dict[str, Any]:
        base_path: Path = config_dir / "base.yaml"
        env_path: Path = config_dir / f"{env}.yaml"

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
        coerced_data: dict[str, Any] = {}

        for field in fields(config_class):
            name: str = field.name
            expected_type: type[Any] = type(field.type)
            value: Any | None = data.get(name)

            coerced_data[name] = convert_type(value, expected_type)

        return config_class(**coerced_data)

    @staticmethod
    def load_app_config(overrides: dict[str, Any] | None = None) -> AppConfig:
        env: str = os.getenv("ENV", "dev").lower()
        merged_config: dict[str, Any] = ConfigLoader._load_merged_yaml(env)
        if overrides:
            merged_config.update(overrides)

        type_hints: dict[str, Any] = get_type_hints(AppConfig)
        init_args: dict[str, Any] = {}

        for field in fields(AppConfig):
            name: str = field.name
            expected_type = type_hints.get(name, Any)
            value = merged_config.get(name, MISSING)

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

        return AppConfig(**init_args)

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

            # Optional: you can make type adjustments here if needed
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
    def override_from_args(config: AppConfig, args: Any) -> AppConfig:
        """
        Replace config fields from argparse.Namespace or dict-like object.
        Only updates known AppConfig fields.
        """
        update_fields = {}
        for field in fields(config):
            name: str = field.name
            if hasattr(args, name):
                value = getattr(args, name)
                if value is not None:
                    update_fields[name] = value
        return replace(config, **update_fields)
