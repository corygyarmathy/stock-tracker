# Import libraries
from argparse import ArgumentParser, Namespace
import logging
from typing import Any

from stock_tracker.config import AppConfig, ConfigLoader
from stock_tracker.db import Database
from stock_tracker.display import display_performance
from stock_tracker.importer import import_valid_orders
from stock_tracker.repositories.corporate_actions_repository import CorporateActionRepository
from stock_tracker.repositories.dividend_repository import DividendRepository
from stock_tracker.repositories.fx_rate_repository import FxRateRepository
from stock_tracker.repositories.order_repository import OrderRepository
from stock_tracker.repositories.stock_info_repository import StockInfoRepository
from stock_tracker.repositories.stock_repository import StockRepository
from stock_tracker.services.portfolio_service import PortfolioService
from stock_tracker.utils.setup_logging import setup_logging

logger: logging.Logger = logging.getLogger(__name__)


def main() -> None:
    # Construct AppConfig private singelton instance
    parser: ArgumentParser = ConfigLoader.build_arg_parser(AppConfig)

    # Add subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Add refresh command
    refresh_parser = subparsers.add_parser("refresh", help="Refresh stock data")
    _ = refresh_parser.add_argument(
        "--dividends", action="store_true", help="Refresh dividend data"
    )
    _ = refresh_parser.add_argument(
        "--stock-info", action="store_true", help="Refresh stock information"
    )
    _ = refresh_parser.add_argument(
        "--batch-size", type=int, default=5, help="Batch size for API calls"
    )
    _ = refresh_parser.add_argument(
        "--delay", type=float, default=5.0, help="Delay between batches"
    )
    _ = refresh_parser.add_argument("--stock-id", type=int, help="Only refresh specific stock ID")

    args: Namespace = parser.parse_args()
    overrides: dict[str, Any] = ConfigLoader.args_to_overrides(args)
    config: AppConfig = ConfigLoader.load_app_config(overrides=overrides)
    AppConfig.set(config)

    # Set up app
    setup_logging(config.log_config_path, config.log_level)

    # Handle commands
    if hasattr(args, "command") and args.command == "refresh":
        from stock_tracker.utils.refresh_data import refresh_dividends, refresh_stock_info

        with Database(config.db_path) as db:
            if args.dividends:
                _ = refresh_dividends(
                    config.db_path,
                    batch_size=args.batch_size,
                    delay_seconds=args.delay,
                    single_stock_id=args.stock_id,
                )

            if args.stock_info:
                _ = refresh_stock_info(
                    config.db_path,
                    batch_size=args.batch_size,
                    delay_seconds=args.delay,
                    single_stock_id=args.stock_id,
                )
        return

    # Run app with a single database connection
    with Database(config.db_path) as db:
        run_app(config, db)


def run_app(config: AppConfig, db: Database) -> None:
    """Run the application with explicit dependencies."""
    db.create_tables_if_not_exists()

    stock_repo: StockRepository = StockRepository(db)
    order_repo: OrderRepository = OrderRepository(db)
    stock_info_repo: StockInfoRepository = StockInfoRepository(db)
    corp_action_repo: CorporateActionRepository = CorporateActionRepository(db)
    fx_rate_repo: FxRateRepository = FxRateRepository(db)
    dividend_repo: DividendRepository = DividendRepository(db)

    # Initialise services
    portfolio_service: PortfolioService = PortfolioService(
        stock_repo, order_repo, stock_info_repo, dividend_repo
    )

    # Import orders if needed
    import_valid_orders(config.csv_path, stock_repo, stock_info_repo, order_repo, dividend_repo)

    # Calculate portfolio performance
    logger.info("Calculating portfolio performance...")
    performance = portfolio_service.calculate_portfolio_performance()

    # Display results
    display_performance(performance)


if __name__ == "__main__":
    main()
