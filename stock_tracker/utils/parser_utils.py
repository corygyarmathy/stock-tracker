"""Utilities for working with argument parsers."""

import argparse
from dataclasses import fields
from typing import Any, get_origin, ClassVar

from stock_tracker.config import AppConfig


def add_config_options(
    parser: argparse.ArgumentParser, config_class: type[AppConfig] = AppConfig
) -> None:
    """
    Dynamically add configuration options to a parser based on a dataclass.

    Args:
        parser: The argument parser to add options to
        config_class: The dataclass to extract fields from (default: AppConfig)
    """
    for field in fields(config_class):
        # Skip private fields and ClassVars
        if field.name.startswith("_") or get_origin(field.type) is ClassVar:
            continue

        arg_name: str = f"--{field.name.replace('_', '-')}"  # eg. db_path -> --db-path
        arg_type: type[Any] = type(field.type)

        # Make type adjustments as needed
        help_text: str = f"Override {field.name} configuration value"

        if arg_type is bool:
            # Special handling for booleans: use 'store_true' action
            _ = parser.add_argument(arg_name, action="store_true", help=help_text)
            continue

        # For all other types, add a standard argument
        _ = parser.add_argument(
            arg_name,
            type=str,  # Accept all as strings initially, convert later
            default=None,  # So we know if user passed it
            metavar=f"{arg_type.__name__}",
            help=help_text,
        )
