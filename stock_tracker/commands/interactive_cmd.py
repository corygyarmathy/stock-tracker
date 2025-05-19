"""Interactive command implementation."""

import argparse
import logging
from typing import Callable, override

from stock_tracker.commands.base import Command, CommandRegistry
from stock_tracker.config import AppConfig
from stock_tracker.container import ServiceContainer
from stock_tracker.db import Database

logger = logging.getLogger(__name__)


@CommandRegistry.register
class InteractiveCommand(Command):
    """Command to launch interactive menu mode."""

    name: str = "interactive"
    help: str = "Launch interactive menu mode"

    def __init__(self, config: AppConfig, db: Database, container: ServiceContainer):
        """Initialise the command with config and database connection."""
        super().__init__(config, db, container)

    @override
    @classmethod
    def setup_parser(cls, subparser) -> None:
        """Configure the argument parser for the interactive command."""
        _ = subparser.add_parser(cls.name, help=cls.help)
        # No additional arguments needed

    @override
    def execute(self, args: argparse.Namespace) -> int:
        """Execute the interactive command."""
        return self._run_interactive_mode()

    def _run_interactive_mode(self) -> int:
        """Run the application in interactive menu mode."""
        # Import other command classes
        from stock_tracker.commands.import_cmd import ImportCommand
        from stock_tracker.commands.refresh_cmd import RefreshCommand
        from stock_tracker.commands.report_cmd import ReportCommand

        # Create command instances
        import_cmd: Command = ImportCommand(self.config, self.db, self.container)
        refresh_cmd: Command = RefreshCommand(self.config, self.db, self.container)
        report_cmd: Command = ReportCommand(self.config, self.db, self.container)

        # Dictionary mapping menu options to handler functions
        handlers: dict[str, Callable[[], int]] = {
            "1": lambda: import_cmd.execute(
                argparse.Namespace(file=None, interactive=True, batch_size=2)
            ),
            "2": lambda: refresh_cmd.execute(argparse.Namespace(type="all", stock_id=None)),
            "3": lambda: report_cmd.execute(argparse.Namespace(type="performance")),
            "4": lambda: report_cmd.execute(argparse.Namespace(type="dividends")),
        }

        while True:
            # Display menu
            print("\n=== Stock Tracker Menu ===")
            print("1. Import Orders from CSV")
            print("2. Refresh Stock Data")
            print("3. View Portfolio Performance")
            print("4. View Dividend Report")
            print("0. Exit")

            # Get user choice
            choice: str = input("\nEnter your choice (0-4): ")

            if choice == "0":
                print("Exiting Stock Tracker. Goodbye!")
                break

            # Execute handler if valid choice
            handler = handlers.get(choice)
            if handler:
                try:
                    exit_code = handler()
                    if exit_code != 0:
                        print(f"\nCommand completed with exit code {exit_code}")
                except Exception as e:
                    print(f"\nError: {e}")
                    logger.error(f"Error in interactive mode: {e}", exc_info=True)
            else:
                print("Invalid choice. Please try again.")

        return 0
