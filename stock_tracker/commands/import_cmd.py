"""Import command implementation."""

import argparse
import logging
from pathlib import Path
from typing import override

from stock_tracker.commands.base import Command, CommandRegistry
from stock_tracker.config import AppConfig
from stock_tracker.container import ServiceContainer
from stock_tracker.db import Database
from stock_tracker.importer import import_valid_orders
from stock_tracker.repositories.dividend_repository import DividendRepository
from stock_tracker.repositories.order_repository import OrderRepository
from stock_tracker.repositories.stock_info_repository import StockInfoRepository
from stock_tracker.repositories.stock_repository import StockRepository

logger = logging.getLogger(__name__)


@CommandRegistry.register
class ImportCommand(Command):
    """Command to import stock orders from a CSV file."""

    name: str = "import"
    help: str = "Import stock orders from CSV"

    def __init__(self, config: AppConfig, db: Database, container: ServiceContainer):
        """Initialise the command with config and database connection."""
        super().__init__(config, db, container)

    @classmethod
    def setup_parser(cls, subparser) -> None:
        """Configure the argument parser for the import command."""
        parser: argparse.ArgumentParser = subparser.add_parser(cls.name, help=cls.help)
        _ = parser.add_argument(
            "file",
            nargs="?",
            help="CSV file to import (defaults to config.csv_path if not specified)",
        )
        _ = parser.add_argument(
            "--interactive",
            action="store_true",
            help="Enable interactive mode for resolving ticker issues",
        )
        _ = parser.add_argument(
            "--batch-size", type=int, default=2, help="Number of tickers to validate in each batch"
        )

    @override
    def execute(self, args: argparse.Namespace) -> int:
        """Execute the import command."""
        # Determine the CSV file to import
        csv_path: Path = Path(args.file) if args.file else self.config.csv_path

        if not csv_path.exists():
            logger.error(f"CSV file not found: {csv_path}")
            print(f"Error: CSV file not found: {csv_path}")
            return 1

        # Get repositories from the container
        stock_repo: StockRepository = self.container.get_repository(StockRepository)
        stock_info_repo: StockInfoRepository = self.container.get_repository(StockInfoRepository)
        order_repo: OrderRepository = self.container.get_repository(OrderRepository)
        dividend_repo: DividendRepository = self.container.get_repository(DividendRepository)

        # Run the import with interactive mode if specified
        logger.info(f"Importing orders from {csv_path}")
        print(f"Importing orders from {csv_path}...")

        try:
            import_valid_orders(
                csv_path=csv_path,
                stock_repo=stock_repo,
                stock_info_repo=stock_info_repo,
                order_repo=order_repo,
                interactive=args.interactive,
                batch_size=args.batch_size,
                dividend_repo=dividend_repo,
            )
            print("Import completed.")
            return 0
        except Exception as e:
            logger.error(f"Import failed: {e}", exc_info=True)
            print(f"Error: Import failed: {e}")
            return 1
