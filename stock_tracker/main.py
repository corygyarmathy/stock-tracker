# Import libraries
from argparse import ArgumentParser, Namespace
import logging
from typing import Any

from stock_tracker.config import AppConfig, ConfigLoader
from stock_tracker.db import Database
from stock_tracker.importer import import_valid_orders
from stock_tracker.repositories.corporate_actions_repository import CorporateActionRepository
from stock_tracker.repositories.fx_rate_repository import FxRateRepository
from stock_tracker.repositories.order_repository import OrderRepository
from stock_tracker.repositories.stock_info_repository import StockInfoRepository
from stock_tracker.repositories.stock_repository import StockRepository
from stock_tracker.utils.setup_logging import setup_logging

logger: logging.Logger = logging.getLogger(__name__)


def main() -> None:
    # Construct AppConfig private singelton instance
    parser: ArgumentParser = ConfigLoader.build_arg_parser(AppConfig)
    args: Namespace = parser.parse_args()
    overrides: dict[str, Any] = ConfigLoader.args_to_overrides(args)
    config: AppConfig = ConfigLoader.load_app_config(overrides=overrides)
    AppConfig.set(config)

    # Set up app
    setup_logging(config.log_config_path, config.log_level)

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

    import_valid_orders(config.csv_path, stock_repo, order_repo)
    # performance = calculate_portfolio_performance(db, session)

    # Display results
    # display_performance(performance)


# INFO: yf.Ticker("IVV")
# ticker str = 'IVV'

# INFO: yf.Ticker.fast_info Example ("IVV.AX")
# currency str = 'AUD'
# day_high float = 55.939998626708984
# day_low float = 55.119998931884766
# exchange str = 'ASX'
# fifty_day_average float = 60.607799987792966
# last_price float = 55.939998626708984
# last_volume int = 441315
# market_cap NoneType = None
# open float = 55.189998626708984
# previous_close float = 55.79999923706055
# proxy NoneType = None
# quote_type str = 'ETF'
# regular_market_previous_close float = 55.79999923706055
# shares NoneType = None
# ten_day_average_volume int = 1779005
# three_month_average_volume int = 596180
# timezone str = 'Australia/Sydney'
# two_hundred_day_average float = 59.271899967193605
# year_change float = 0.08368848865194049
# year_high float = 65.2699966430664
# year_low float = 51.369998931884766


if __name__ == "__main__":
    main()
