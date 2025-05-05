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

    # @classmethod
    # def from_env(cls) -> Self:
    #     """Return a new config with values from env."""
    #     instance = cls(
    #         project_root=Path(__file__).parent.parent.resolve(),
    #         env=os.getenv("ENV", "development").lower(),
    #         db_path=Path(os.getenv("DB_PATH", "dev.db")),
    #         csv_path=Path(os.getenv("CSV_PATH", "import.csv")),
    #         log_config_path=Path(
    #             os.path.join(
    #                 AppConfig.project_root,
    #                 os.getenv("LOGGING_CONFIG_PATH", "config/logging_config.yaml"),
    #             )
    #         ),
    #         log_file_path=Path(os.getenv("LOG_FILE_PATH", "app.log")),
    #         log_level=str(os.getenv("LOG_LEVEL", "logging.DEBUG")),
    #         yf_max_requests=str(os.getenv("YF_MAX_REQUESTS", "2")),
    #         yf_request_interval_seconds=str(
    #             os.getenv("YF_REQUEST_INTERVAL_SECONDS", "5")
    #         ),
    #     )
    #     cls._instance = instance
    #     return instance

    # @classmethod
    # def load_from_file(cls, file_path: Path) -> Self:
    #     with file_path.open("r") as f:
    #         raw_data = yaml.safe_load(f)
    #
    #     # Dynamically convert fields to the correct types
    #     init_args = {}
    #     type_hints = get_type_hints(cls)
    #     for field in fields(cls):
    #         name: str = field.name
    #         field_type = type_hints.get(name, Any)
    #         value = raw_data.get(name, MISSING)
    #
    #         if value is MISSING:
    #             if field.default is not MISSING:
    #                 value = field.default
    #             elif field.default_factory is not MISSING:  # type: ignore
    #                 value = field.default_factory()  # type: ignore
    #             else:
    #                 raise ValueError(f"Missing required config field: {name}")
    #
    #         # Type conversion (minimal but safe)
    #         if field_type is Path:
    #             value = Path(value)
    #         elif field_type is int:
    #             value = int(value)
    #         elif field_type is float:
    #             value = float(value)
    #         elif field_type is bool:
    #             value = bool(value)
    #         elif field_type is str:
    #             value = str(value)
    #         # For nested dataclasses or lists, you'd add more logic here
    #
    #         init_args[name] = value
    #
    #     instance = cls(**init_args)
    #     cls._instance = instance
    #     return instance

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
    def _dict_to_config(data: dict[str, Any], config_class: type[Any]) -> AppConfig:
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
