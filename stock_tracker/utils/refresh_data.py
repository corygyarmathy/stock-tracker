# Write a script like refresh_data.py to:
#     Periodically update stale data
#     Allow full or targeted refreshes
#     Run on a schedule (manual or cron)


from datetime import datetime, timedelta


def is_refresh_needed(last_updated: datetime, ttl_hours: int = 24) -> bool:
    return datetime.now() - last_updated > timedelta(hours=ttl_hours)


import logging
import argparse
from pathlib import Path

from stock_tracker.config import AppConfig, ConfigLoader
from stock_tracker.db import Database
from stock_tracker.repositories.dividend_repository import DividendRepository
from stock_tracker.repositories.stock_repository import StockRepository
from stock_tracker.services.dividend_service import DividendService
from stock_tracker.utils.setup_logging import setup_logging

logger = logging.getLogger(__name__)


def refresh_dividends() -> None:
    """
    Command line tool to refresh dividend data for all stocks in the portfolio.

    This function:
    1. Connects to the database
    2. Gets all stocks in the portfolio
    3. Fetches latest dividend data for each stock
    4. Updates the dividend_history table

    Can be run periodically to keep dividend data up to date.
    """
    # Load config
    parser = argparse.ArgumentParser(description="Refresh dividend data for stocks in portfolio")
    parser.add_argument("--config-dir", type=str, help="Path to config directory")
    args = parser.parse_args()

    # Use specified config dir if provided
    config_dir = Path(args.config_dir) if args.config_dir else Path("config")

    # Load app config
    config = ConfigLoader.load_app_config()
    AppConfig.set(config)

    # Set up logging
    setup_logging(config.log_config_path, config.log_level)

    logger.info("Starting dividend data refresh")

    # Connect to database
    with Database(config.db_path) as db:
        # Initialize repositories and services
        stock_repo = StockRepository(db)
        dividend_repo = DividendRepository(db)
        dividend_service = DividendService(dividend_repo)

        # Ensure the dividend_history table exists
        db.create_tables_if_not_exists()

        # Get all stocks in portfolio
        stocks_rows = db.query_all("SELECT * FROM stocks")
        logger.info(f"Found {len(stocks_rows)} stocks in portfolio")

        total_dividends = 0

        # Process each stock
        for stock_row in stocks_rows:
            stock = stock_repo.get_by_id(stock_row["id"])
            if stock:
                logger.info(f"Refreshing dividend data for {stock.ticker}.{stock.exchange}")

                # Get existing dividend count
                existing_dividends = dividend_repo.get_dividends_for_stock(stock.id)
                existing_count = len(existing_dividends)

                # Fetch and store latest dividends
                dividends = dividend_service.fetch_and_store_dividends(stock)
                new_count = len(dividends) - existing_count

                logger.info(f"Added {new_count} new dividends for {stock.ticker}.{stock.exchange}")
                total_dividends += new_count

        logger.info(f"Dividend refresh complete. Added {total_dividends} new dividend records.")


if __name__ == "__main__":
    refresh_dividends()
