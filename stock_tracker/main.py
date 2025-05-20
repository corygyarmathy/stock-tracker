"""
Stock Tracker CLI

A command-line interface for tracking stock performance, handling orders,
dividends, and portfolio analysis.
"""

import argparse
import importlib
import logging
import pkgutil
import sys
from pathlib import Path
from typing import Any

from stock_tracker.commands.base import Command, CommandRegistry
from stock_tracker.config import AppConfig, ConfigLoader, get_env
from stock_tracker.container import ServiceContainer
from stock_tracker.db import Database
from stock_tracker.utils.parser_utils import add_config_options
from stock_tracker.utils.setup_logging import setup_logging

logger = logging.getLogger(__name__)


def load_commands() -> None:
    """
    Dynamically import all command modules to register commands.

    This function finds and imports all modules in the commands package
    to ensure all command classes are registered with the CommandRegistry.
    """
    # Import the base module first
    import stock_tracker.commands.base

    # Dynamically import all other modules in the commands package
    for _, name, _ in pkgutil.iter_modules(stock_tracker.commands.__path__):
        if name != "base":  # Skip base module as we already imported it
            importlib.import_module(f"stock_tracker.commands.{name}")

    logger.debug(f"Loaded {len(CommandRegistry.get_commands())} commands")


def create_parser(env: str) -> argparse.ArgumentParser:
    """Create the argument parser with all commands and options."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Stock Tracker CLI",
        epilog="Use 'stock-tracker COMMAND --help' for more information on a command.",
    )

    # Add global options
    global_group = parser.add_argument_group("Global Options")

    # For development/testing only
    if env == "test" or env == "dev":
        _ = global_group.add_argument(
            "--env",
            help="Environment to use (dev, test, prod). Default: prod",
            choices=["dev", "test", "prod"],
        )

    # Add configuration options (these apply to all commands)
    add_config_options(global_group)

    # Add config file option (better user experience than environments)
    _ = global_group.add_argument(
        "--config-file", help="Path to specific configuration file to use", type=str
    )

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Register all command parsers
    for name, command_class in CommandRegistry.get_commands().items():
        command_class.setup_parser(subparsers)

    return parser


def main() -> int:
    """
    Main entry point for the stock-tracker CLI application.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Load all command modules
    load_commands()

    env = get_env()

    # Parse command line arguments
    parser: argparse.ArgumentParser = create_parser(env)
    args: argparse.Namespace = parser.parse_args()

    # Check if a command was specified
    if not args.command:
        parser.print_help()
        return 0

    # Handle environment override from CLI (development only)
    if (env == "dev" or env == "test") and hasattr(args, "env") and args.env:
        env = args.env

    # Convert args to config overrides
    overrides: dict[str, Any] = ConfigLoader.args_to_overrides(args)

    # Handle custom config file
    config_file: Path | None = Path(args.config_file) if args.config_file else None

    # Load the configuration
    try:
        config: AppConfig = ConfigLoader.load_app_config(
            overrides=overrides, env=env, config_file=config_file
        )
    except Exception as e:
        # Print error and exit if config loading fails
        print(f"Error loading configuration: {e}", file=sys.stderr)
        return 1

    # Set up logging
    setup_logging(config.log_config_path, config.log_level)

    # Create database connection and ensure tables exist
    try:
        with Database(config.db_path) as db:
            db.create_tables_if_not_exists()

            # Create service container object
            container: ServiceContainer = ServiceContainer(config, db)

            # Find and instantiate the requested command
            command_classes: dict[str, type[Command]] = CommandRegistry.get_commands()
            if args.command in command_classes:
                command_class: type[Command] = command_classes[args.command]
                command: Command = command_class(config, db, container)

                # Execute the command
                return command.execute(args)
            else:
                logger.error(f"Unknown command: {args.command}")
                print(f"Error: Unknown command: {args.command}", file=sys.stderr)
                return 1
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
