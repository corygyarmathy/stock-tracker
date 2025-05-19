"""Refresh command implementation."""

import argparse
import logging
from typing import override

from stock_tracker.commands.base import Command, CommandRegistry
from stock_tracker.config import AppConfig
from stock_tracker.container import ServiceContainer
from stock_tracker.db import Database
from stock_tracker.models import Dividend, Stock
from stock_tracker.repositories.dividend_repository import DividendRepository
from stock_tracker.repositories.stock_repository import StockRepository
from stock_tracker.services.dividend_service import DividendService

logger = logging.getLogger(__name__)


@CommandRegistry.register
class RefreshCommand(Command):
    """Command to refresh stock data."""

    name: str = "refresh"
    help: str = "Refresh stock data"

    def __init__(self, config: AppConfig, db: Database, container: ServiceContainer):
        """Initialise the command with config, database connection and service container."""
        super().__init__(config, db, container)

    @override
    @classmethod
    def setup_parser(cls, subparser) -> None:
        """Configure the argument parser for the refresh command."""
        parser: argparse.ArgumentParser = subparser.add_parser(cls.name, help=cls.help)
        _ = parser.add_argument(
            "type", choices=["dividends", "prices", "splits", "all"], help="Type of data to refresh"
        )
        _ = parser.add_argument(
            "--stock-id", type=int, help="Only refresh for this specific stock ID"
        )

    @override
    def execute(self, args: argparse.Namespace) -> int:
        """Execute the refresh command."""
        refresh_type = args.type
        stock_id = getattr(args, "stock_id", None)
        if stock_id:
            stock_id = int(stock_id)
        else:
            raise ValueError("Attr 'stock_id' returned None.")

        # Get repositories and services from the container
        stock_repo: StockRepository = self.container.get_repository(StockRepository)
        dividend_repo: DividendRepository = self.container.get_repository(DividendRepository)
        dividend_service: DividendService = self.container.get_service(DividendService)

        # Refresh dividends
        if refresh_type in ["dividends", "all"]:
            return self._refresh_dividends(dividend_service, stock_repo, dividend_repo, stock_id)

        # Refresh stock prices
        if refresh_type in ["prices", "all"]:
            return self._refresh_prices(stock_id)

        # Refresh splits
        if refresh_type in ["splits", "all"]:
            return self._refresh_splits(stock_id)

        return 0

    def _refresh_dividends(
        self,
        dividend_service: DividendService,
        stock_repo: StockRepository,
        dividend_repo: DividendRepository,
        stock_id: int | None = None,
    ) -> int:
        """Refresh dividend data for stocks."""
        print("Refreshing dividend data...")

        # Get stocks to refresh
        if stock_id:
            stock: Stock | None = stock_repo.get_by_id(stock_id)
            if not stock:
                logger.error(f"Stock with ID {stock_id} not found")
                print(f"Error: Stock with ID {stock_id} not found")
                return 1
            stocks: list[Stock] = [stock]
            logger.info(f"Refreshing dividends for single stock ID: {stock_id}")
        else:
            stocks = stock_repo.get_all()
            logger.info(f"Refreshing dividends for all {len(stocks)} stocks")

        total_dividends = 0

        for stock in stocks:
            if stock.id:
                logger.info(f"Refreshing dividend data for {stock.ticker}.{stock.exchange}")
                print(f"Refreshing dividends for {stock.ticker}.{stock.exchange}...", end="")

                # Get existing dividend count
                existing_dividends: list[Dividend] = dividend_repo.get_dividends_for_stock(stock.id)
                existing_count: int = len(existing_dividends)

                # Fetch and store latest dividends
                try:
                    dividends: list[Dividend] = dividend_service.fetch_and_store_dividends(stock)
                    new_count: int = len(dividends) - existing_count
                    total_dividends += new_count
                    print(f" added {new_count} new records.")
                except Exception as e:
                    logger.error(f"Error refreshing dividends for {stock.ticker}: {e}")
                    print(f" error: {e}")

        print(f"Dividend refresh complete. Added {total_dividends} new dividend records.")
        return 0

    def _refresh_prices(self, stock_id: int | None = None) -> int:
        """Refresh stock price data."""
        print("Refreshing stock prices...")
        # TODO: implement refreshing stock price using container services
        print("Price refresh not yet implemented.")
        return 0

    def _refresh_splits(self, stock_id: int | None = None) -> int:
        """Refresh stock split data."""
        print("Refreshing stock splits...")
        # TODO: implement refreshing stock splits using container services
        print("Stock split refresh has not yet been implemented.")
        return 0
