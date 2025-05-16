import logging
import argparse
import time
from pathlib import Path

from stock_tracker.config import AppConfig, ConfigLoader
from stock_tracker.db import Database
from stock_tracker.models import Stock
from stock_tracker.repositories.dividend_repository import DividendRepository
from stock_tracker.repositories.stock_repository import StockRepository
from stock_tracker.services.dividend_service import DividendService
from stock_tracker.utils.setup_logging import setup_logging

logger = logging.getLogger(__name__)


def refresh_dividends(
    db_path: Path,
    batch_size: int = 5,
    delay_seconds: float = 5.0,
    single_stock_id: int | None = None,
) -> int:
    """
    Refresh dividend data for stocks in the portfolio.

    Args:
        db_path: Path to the database file
        batch_size: Number of stocks to process in each batch
        delay_seconds: Delay between batches in seconds
        single_stock_id: If provided, only refresh this specific stock

    Returns:
        Number of new dividend records added
    """
    total_new = 0

    logger.info("Starting dividend data refresh")

    # Connect to database
    with Database(db_path) as db:
        # Initialize repositories and services
        stock_repo = StockRepository(db)
        dividend_repo = DividendRepository(db)
        dividend_service = DividendService(dividend_repo)

        # Ensure the dividend_history table exists
        db.create_tables_if_not_exists()

        # Get stocks to refresh
        if single_stock_id:
            stock = stock_repo.get_by_id(single_stock_id)
            stocks = [stock] if stock else []
            logger.info(f"Refreshing dividends for single stock ID: {single_stock_id}")
        else:
            stocks = stock_repo.get_all()
            logger.info(f"Found {len(stocks)} stocks in portfolio")

        # Process in batches to avoid API rate limits
        for i in range(0, len(stocks), batch_size):
            batch = stocks[i : i + batch_size]
            logger.info(
                f"Processing batch {i // batch_size + 1}/{(len(stocks) - 1) // batch_size + 1}"
            )

            for stock in batch:
                if not stock or not stock.id:
                    logger.warning(f"Skipping invalid stock (no ID)")
                    continue

                logger.info(f"Refreshing dividends for {stock.ticker}.{stock.exchange}")

                # Get existing dividend count
                existing_dividends = dividend_repo.get_dividends_for_stock(stock.id)
                existing_count = len(existing_dividends)

                # Fetch and store latest dividends
                try:
                    dividends = dividend_service.fetch_and_store_dividends(stock)
                    new_count = len(dividends) - existing_count
                    total_new += new_count

                    logger.info(
                        f"Added {new_count} new dividends for {stock.ticker}.{stock.exchange}"
                    )
                except Exception as e:
                    logger.error(
                        f"Error refreshing dividends for {stock.ticker}.{stock.exchange}: {e}"
                    )

            # Add delay between batches
            if i + batch_size < len(stocks):
                logger.debug(f"Sleeping for {delay_seconds} seconds before next batch")
                time.sleep(delay_seconds)

    logger.info(f"Dividend refresh complete. Added {total_new} new dividend records.")
    return total_new


def refresh_stock_info(
    db_path: Path,
    batch_size: int = 3,
    delay_seconds: float = 10.0,
    single_stock_id: int | None = None,
) -> int:
    """
    Refresh current price and other stock info.

    Args:
        db_path: Path to the database file
        batch_size: Number of stocks to process in each batch
        delay_seconds: Delay between batches in seconds
        single_stock_id: If provided, only refresh this specific stock

    Returns:
        Number of stock info records updated
    """
    # For now, this is a placeholder. Implement similar to refresh_dividends
    # but using the ticker service to get updated stock information
    # TODO: impletment this functionality
    return 0


def fetch_splits_and_corporate_actions(
    db_path: Path,
    batch_size: int = 3,
    delay_seconds: float = 10.0,
    single_stock_id: int | None = None,
) -> int:
    """
    Fetch stock splits and corporate actions from yfinance.

    Args:
        db_path: Path to the database file
        batch_size: Number of stocks to process in each batch
        delay_seconds: Delay between batches in seconds
        single_stock_id: If provided, only process this specific stock

    Returns:
        Number of new corporate actions added
    """
    # For now, this is a placeholder. Implement similar to refresh_dividends
    # but fetching split information
    return 0


def main():
    """CLI entry point for data refresh operations."""
    parser = argparse.ArgumentParser(description="Refresh stock data")

    # Add options for what to refresh
    _ = parser.add_argument("--dividends", action="store_true", help="Refresh dividend data")
    _ = parser.add_argument(
        "--stock-info", action="store_true", help="Refresh current stock information"
    )
    _ = parser.add_argument(
        "--splits", action="store_true", help="Refresh stock splits and corporate actions"
    )
    _ = parser.add_argument("--all", action="store_true", help="Refresh all data")

    # Add execution options
    _ = parser.add_argument("--db-path", type=str, help="Path to database file (overrides config)")
    _ = parser.add_argument(
        "--batch-size", type=int, default=5, help="Number of stocks to process per batch"
    )
    _ = parser.add_argument(
        "--delay", type=float, default=5.0, help="Delay between batches in seconds"
    )
    _ = parser.add_argument("--stock-id", type=int, help="Only refresh for this specific stock ID")
    _ = parser.add_argument("--config-dir", type=str, help="Path to config directory")

    args = parser.parse_args()

    # Load config
    config_dir = Path(args.config_dir) if args.config_dir else None
    config = ConfigLoader.load_app_config()
    AppConfig.set(config)

    # Set up logging
    setup_logging(config.log_config_path, config.log_level)

    # Determine database path
    db_path = Path(args.db_path) if args.db_path else config.db_path

    # No options means refresh dividends by default
    if not (args.dividends or args.stock_info or args.splits or args.all):
        args.dividends = True

    # Perform refresh operations
    if args.all or args.dividends:
        _ = refresh_dividends(db_path, args.batch_size, args.delay, args.stock_id)

    if args.all or args.stock_info:
        _ = refresh_stock_info(db_path, args.batch_size, args.delay, args.stock_id)

    if args.all or args.splits:
        _ = fetch_splits_and_corporate_actions(db_path, args.batch_size, args.delay, args.stock_id)


if __name__ == "__main__":
    main()
