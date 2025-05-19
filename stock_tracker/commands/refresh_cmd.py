"""Refresh command implementation."""

import argparse
import logging
from typing import override

from yfinance import Ticker

from stock_tracker.commands.base import Command, CommandRegistry
from stock_tracker.config import AppConfig
from stock_tracker.container import ServiceContainer
from stock_tracker.db import Database
from stock_tracker.models import CorporateAction, Dividend, Stock, StockInfo
from stock_tracker.repositories.corporate_actions_repository import CorporateActionRepository
from stock_tracker.repositories.dividend_repository import DividendRepository
from stock_tracker.repositories.stock_info_repository import StockInfoRepository
from stock_tracker.repositories.stock_repository import StockRepository
from stock_tracker.services.dividend_service import DividendService
from stock_tracker.services.ticker_service import TickerService

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
        stock_id: int | None = getattr(args, "stock_id", None)
        if stock_id:
            stock_id = int(stock_id)

        # Get repositories and services from the container
        stock_repo: StockRepository = self.container.get_repository(StockRepository)
        stock_info_repo: StockInfoRepository = self.container.get_repository(StockInfoRepository)
        dividend_repo: DividendRepository = self.container.get_repository(DividendRepository)
        corp_action_repo: CorporateActionRepository = self.container.get_repository(
            CorporateActionRepository
        )
        dividend_service: DividendService = self.container.get_service(DividendService)

        result = 0  # Track overall success (0 = success, non-zero = failure)

        # Refresh dividends
        if refresh_type in ["dividends", "all"]:
            dividend_result = self._refresh_dividends(
                dividend_service, stock_repo, dividend_repo, stock_id
            )
            result = result or dividend_result  # Update result if there was an error

        # Refresh stock prices
        if refresh_type in ["prices", "all"]:
            price_result = self._refresh_prices(
                stock_repo=stock_repo, stock_info_repo=stock_info_repo, stock_id=stock_id
            )
            result = result or price_result  # Update result if there was an error

        # Refresh splits
        if refresh_type in ["splits", "all"]:
            splits_result = self._refresh_splits(
                stock_repo=stock_repo, corp_action_repo=corp_action_repo, stock_id=stock_id
            )
            result = result or splits_result  # Update result if there was an error

        return result

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

    def _refresh_prices(
        self,
        stock_repo: StockRepository,
        stock_info_repo: StockInfoRepository,
        stock_id: int | None = None,
    ) -> int:
        """Refresh stock price data."""
        print("Refreshing stock prices...")

        # Get stocks to refresh
        if stock_id:
            stock: Stock | None = stock_repo.get_by_id(stock_id)
            if not stock:
                logger.error(f"Stock with ID {stock_id} not found")
                print(f"Error: Stock with ID {stock_id} not found")
                return 1
            stocks: list[Stock] = [stock]
            logger.info(f"Refreshing price data for single stock ID: {stock_id}")
        else:
            stocks = stock_repo.get_all()
            logger.info(f"Refreshing price data for all {len(stocks)} stocks")

        # Process stocks in batches to respect API limits
        batch_size = 5
        total_updated = 0

        for i in range(0, len(stocks), batch_size):
            batch: list[Stock] = stocks[i : i + batch_size]
            batch_num: int = i // batch_size + 1
            total_batches: int = (len(stocks) - 1) // batch_size + 1

            print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} stocks)...")

            for stock in batch:
                if not stock.id:
                    logger.warning(f"Skipping stock without ID: {stock.ticker}.{stock.exchange}")
                    continue

                print(f"Refreshing price data for {stock.ticker}.{stock.exchange}...", end="")
                try:
                    ticker: Ticker | None = TickerService.get_ticker_for_stock(stock)

                    if not ticker:
                        print(" failed (invalid ticker)")
                        logger.error(
                            f"Failed to get valid ticker for {stock.ticker}.{stock.exchange}"
                        )
                        continue

                    # Extract stock info from ticker
                    _, stock_info = TickerService.extract_models(ticker)
                    stock_info.stock_id = stock.id

                    # Update or insert stock info
                    stock_info_repo.upsert(stock_info)

                    print(f" updated (price: {stock_info.current_price:.2f})")
                    total_updated += 1

                except Exception as e:
                    print(f" error: {e}")
                    logger.error(
                        f"Error refreshing price data for {stock.ticker}.{stock.exchange}: {e}"
                    )

            # Add delay between batches to respect API rate limits
            if batch_num < total_batches:
                delay = 5  # seconds
                print(f"Waiting {delay} seconds before next batch...")
                import time

                time.sleep(delay)

        print(f"Price refresh complete. Updated {total_updated} stocks.")
        return 0

    def _refresh_splits(
        self,
        stock_repo: StockRepository,
        corp_action_repo: CorporateActionRepository,
        stock_id: int | None = None,
    ) -> int:
        """Refresh stock split and corporate action data."""
        print("Refreshing stock splits and corporate actions...")

        # Get stocks to refresh
        if stock_id:
            stock: Stock | None = stock_repo.get_by_id(stock_id)
            if not stock:
                logger.error(f"Stock with ID {stock_id} not found")
                print(f"Error: Stock with ID {stock_id} not found")
                return 1
            stocks: list[Stock] = [stock]
            logger.info(f"Refreshing splits for single stock ID: {stock_id}")
        else:
            stocks = stock_repo.get_all()
            logger.info(f"Refreshing splits for all {len(stocks)} stocks")

        # Process stocks in batches to respect API limits
        batch_size = 5
        total_actions = 0

        for i in range(0, len(stocks), batch_size):
            batch: list[Stock] = stocks[i : i + batch_size]
            batch_num: int = i // batch_size + 1
            total_batches: int = (len(stocks) - 1) // batch_size + 1

            print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} stocks)...")

            for stock in batch:
                if not stock.id:
                    logger.warning(f"Skipping stock without ID: {stock.ticker}.{stock.exchange}")
                    continue

                print(f"Checking splits for {stock.ticker}.{stock.exchange}...", end="")
                try:
                    # Get existing corporate actions for this stock
                    existing_actions: list[CorporateAction] = corp_action_repo.get_by_stock_id(
                        stock.id
                    )
                    existing_dates = {action.action_date for action in existing_actions}

                    ticker: Ticker | None = TickerService.get_ticker_for_stock(stock)

                    if not ticker:
                        print(" failed (invalid ticker)")
                        logger.error(
                            f"Failed to get valid ticker for {stock.ticker}.{stock.exchange}"
                        )
                        continue

                    # Fetch splits from yfinance
                    # TODO: This is a simplified example - to implement the actual yfinance split data extraction
                    try:
                        splits = ticker.splits  # This is a pandas Series from yfinance
                        if splits.empty:
                            print(" no splits found.")
                            continue

                        new_actions = 0

                        # Process each split
                        for split_date, ratio in splits.items():
                            split_date = split_date.date()

                            # Skip if we already have this action
                            if split_date in existing_dates:
                                continue

                            action: CorporateAction = CorporateAction(
                                id=None,
                                stock_id=stock.id,
                                action_type="split",
                                action_date=split_date,
                                ratio=float(ratio),
                                target_stock_id=stock.id,  # Same stock for splits
                            )

                            _ = corp_action_repo.insert(action)
                            new_actions += 1

                        print(f" found {new_actions} new splits")
                        total_actions += new_actions

                    except AttributeError:
                        print(" no split data available")
                        logger.warning(
                            f"No split data available for {stock.ticker}.{stock.exchange}"
                        )

                except Exception as e:
                    print(f" error: {e}")
                    logger.error(
                        f"Error refreshing splits for {stock.ticker}.{stock.exchange}: {e}"
                    )

            # Add delay between batches to respect API rate limits
            if batch_num < total_batches:
                delay = 5  # seconds
                print(f"Waiting {delay} seconds before next batch...")
                import time

                time.sleep(delay)

        print(f"Split refresh complete. Found {total_actions} new corporate actions.")
        return 0
