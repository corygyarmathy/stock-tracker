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
from typing import Any

from stock_tracker.commands.base import Command, CommandRegistry
from stock_tracker.config import AppConfig, ConfigLoader
from stock_tracker.container import ServiceContainer
from stock_tracker.db import Database
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


def create_parser() -> argparse.ArgumentParser:
    """
    Create the argument parser with all commands and options.

    Returns:
        Configured ArgumentParser object
    """
    # Create the base parser
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Stock Tracker CLI",
        epilog="Use 'stock-tracker COMMAND --help' for more information on a command.",
    )

    # Add global options (these apply to all commands)
    _ = parser.add_argument("--log-level", help="Set logging level")
    _ = parser.add_argument("--db-path", type=str, help="Database path")

    # Create subparsers for different commands
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser] = parser.add_subparsers(
        dest="command", help="Command to run"
    )

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

    # Parse command line arguments
    parser: argparse.ArgumentParser = create_parser()
    args: argparse.Namespace = parser.parse_args()

    # Check if a command was specified
    if not args.command:
        parser.print_help()
        return 0

    # Convert args to config overrides
    overrides: dict[str, Any] = ConfigLoader.args_to_overrides(args)

    # Load the configuration
    try:
        config: AppConfig = ConfigLoader.load_app_config(overrides=overrides)
        AppConfig.set(config)
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
            container = ServiceContainer(config, db)

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
