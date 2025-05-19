"""
Stock Tracker CLI

A command-line interface for tracking stock performance, handling orders,
dividends, and portfolio analysis.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Callable

from stock_tracker.config import AppConfig, ConfigLoader
from stock_tracker.db import Database
from stock_tracker.display import display_dividend_report, display_performance
from stock_tracker.importer import import_valid_orders
from stock_tracker.models import Stock
from stock_tracker.repositories.corporate_actions_repository import CorporateActionRepository
from stock_tracker.repositories.dividend_repository import DividendRepository
from stock_tracker.repositories.fx_rate_repository import FxRateRepository
from stock_tracker.repositories.order_repository import OrderRepository
from stock_tracker.repositories.stock_info_repository import StockInfoRepository
from stock_tracker.repositories.stock_repository import StockRepository
from stock_tracker.services.dividend_service import DividendService
from stock_tracker.services.portfolio_service import PortfolioService
from stock_tracker.utils.setup_logging import setup_logging

logger: logging.Logger = logging.getLogger(__name__)


# Command handler for import command
def cmd_import(args: argparse.Namespace, config: AppConfig, db: Database) -> None:
    """Import stock orders from a CSV file."""
    # Determine the CSV file to import
    csv_path = Path(args.file) if args.file else config.csv_path

    if not csv_path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        print(f"Error: CSV file not found: {csv_path}")
        return

    # Set up repositories
    stock_repo = StockRepository(db)
    stock_info_repo = StockInfoRepository(db)
    order_repo = OrderRepository(db)
    dividend_repo = DividendRepository(db)

    # Run the import with interactive mode if specified
    logger.info(f"Importing orders from {csv_path}")
    print(f"Importing orders from {csv_path}...")

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


# Command handler for refresh command
def cmd_refresh(args: argparse.Namespace, config: AppConfig, db: Database) -> None:
    """Refresh stock data like prices, dividends, etc."""
    refresh_type = args.type

    # Set up repositories
    stock_repo = StockRepository(db)
    stock_info_repo = StockInfoRepository(db)
    dividend_repo = DividendRepository(db)

    # Refresh dividends
    if refresh_type in ["dividends", "all"]:
        dividend_service = DividendService(dividend_repo)
        print("Refreshing dividend data...")
        stocks: list[Stock] = stock_repo.get_all()
        total_dividends = 0

        for stock in stocks:
            if stock.id:
                logger.info(f"Refreshing dividend data for {stock.ticker}.{stock.exchange}")
                print(f"Refreshing dividends for {stock.ticker}.{stock.exchange}...", end="")

                # Get existing dividend count
                existing_dividends = dividend_repo.get_dividends_for_stock(stock.id)
                existing_count = len(existing_dividends)

                # Fetch and store latest dividends
                dividends = dividend_service.fetch_and_store_dividends(stock)
                new_count = len(dividends) - existing_count

                total_dividends += new_count
                print(f" added {new_count} new records.")

        print(f"Dividend refresh complete. Added {total_dividends} new dividend records.")

    # Refresh stock prices
    if refresh_type in ["prices", "all"]:
        print("Refreshing stock prices...")
        # TODO: implement refreshing stock price: utils.refresh_stock_info()
        # Implementation for refreshing stock prices would go here
        # This could use the StockService to fetch current prices
        print("Price refresh not yet implemented.")

    # Refresh splits
    if refresh_type in ["splits", "all"]:
        print("Refreshing stock splits...")
        # TODO: implement refreshing stock price: utils.refresh_stock_info()
        print("Stock split refresh has not yet been implemented.")


# Command handler for report command
def cmd_report(args: argparse.Namespace, config: AppConfig, db: Database) -> None:
    """Generate various reports."""
    report_type = args.type

    # Set up repositories and services
    stock_repo = StockRepository(db)
    order_repo = OrderRepository(db)
    stock_info_repo = StockInfoRepository(db)
    dividend_repo = DividendRepository(db)

    portfolio_service = PortfolioService(stock_repo, order_repo, stock_info_repo, dividend_repo)

    # Portfolio performance report
    if report_type == "performance":
        print("Generating portfolio performance report...")
        performance = portfolio_service.calculate_portfolio_performance()
        display_performance(performance)

    # Dividend report
    elif report_type == "dividends":
        print("Generating dividend report...")
        portfolio_service = PortfolioService(stock_repo, order_repo, stock_info_repo, dividend_repo)

        # Get dividend report data from service
        dividend_data = portfolio_service.calculate_dividend_report()

        # Display the report
        display_dividend_report(dividend_data)

    # Capital gains report
    elif report_type == "gains":
        print("Generating capital gains report...")
        # Implementation for capital gains report
        print("Capital gains report not yet implemented.")


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser with all commands and options."""
    # Create the base parser
    parser = argparse.ArgumentParser(
        description="Stock Tracker CLI",
        epilog="Use 'stock-tracker COMMAND --help' for more information on a command.",
    )

    # Add global options (these apply to all commands)
    _ = parser.add_argument("--log-level", help="Set logging level")
    _ = parser.add_argument("--db-path", type=str, help="Database path")

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Import command
    import_parser = subparsers.add_parser("import", help="Import stock orders from CSV")
    _ = import_parser.add_argument(
        "file", nargs="?", help="CSV file to import (defaults to config.csv_path if not specified)"
    )
    _ = import_parser.add_argument(
        "--interactive",
        action="store_true",
        help="Enable interactive mode for resolving ticker issues",
    )
    _ = import_parser.add_argument(
        "--batch-size", type=int, default=2, help="Number of tickers to validate in each batch"
    )

    # Refresh command
    refresh_parser = subparsers.add_parser("refresh", help="Refresh stock data")
    _ = refresh_parser.add_argument(
        "type", choices=["dividends", "prices", "splits", "all"], help="Type of data to refresh"
    )

    # Report command
    report_parser = subparsers.add_parser("report", help="Generate reports")
    _ = report_parser.add_argument(
        "type", choices=["performance", "dividends", "gains"], help="Type of report to generate"
    )

    # Interactive mode command (for menu-based interface)
    interactive_parser = subparsers.add_parser("interactive", help="Launch interactive menu mode")

    return parser


def run_interactive_mode(config: AppConfig, db: Database) -> None:
    """Run the application in interactive menu mode."""
    # Dictionary mapping menu options to handler functions
    handlers: dict[str, Callable[[AppConfig, Database], None]] = {
        "1": lambda cfg, db: cmd_import(
            argparse.Namespace(file=None, interactive=True, batch_size=2), cfg, db
        ),
        "2": lambda cfg, db: cmd_refresh(argparse.Namespace(type="all"), cfg, db),
        "3": lambda cfg, db: cmd_report(argparse.Namespace(type="performance"), cfg, db),
        "4": lambda cfg, db: cmd_report(argparse.Namespace(type="dividends"), cfg, db),
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
        choice = input("\nEnter your choice (0-4): ")

        if choice == "0":
            print("Exiting Stock Tracker. Goodbye!")
            break

        # Execute handler if valid choice
        handler = handlers.get(choice)
        if handler:
            try:
                handler(config, db)
            except Exception as e:
                print(f"\nError: {e}")
                logger.error(f"Error in interactive mode: {e}", exc_info=True)
        else:
            print("Invalid choice. Please try again.")


def main() -> None:
    """Main entry point for the stock-tracker CLI application."""
    # Parse command line arguments
    parser: argparse.ArgumentParser = create_parser()
    args: argparse.Namespace = parser.parse_args()

    # Convert args to config overrides
    overrides: dict[str, Any] = ConfigLoader.args_to_overrides(args)

    # Load the configuration
    try:
        config: AppConfig = ConfigLoader.load_app_config(overrides=overrides)
        AppConfig.set(config)
    except Exception as e:
        # Print error and exit if config loading fails
        print(f"Error loading configuration: {e}", file=sys.stderr)
        sys.exit(1)

    # Set up logging
    setup_logging(config.log_config_path, config.log_level)

    # Create database tables if they don't exist
    try:
        with Database(config.db_path) as db:
            db.create_tables_if_not_exists()

            # Execute the requested command
            if args.command == "import":
                cmd_import(args, config, db)
            elif args.command == "refresh":
                cmd_refresh(args, config, db)
            elif args.command == "report":
                cmd_report(args, config, db)
            elif args.command == "interactive":
                run_interactive_mode(config, db)
            else:
                # No command provided, show help
                parser.print_help()
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
