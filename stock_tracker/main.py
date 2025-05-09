# Import libraries
import csv
import json
import logging
from typing import Any

import yfinance as yf
from stock_tracker.db import Database
from stock_tracker.tickers import (
    import_valid_tickers,
)

from stock_tracker.config import AppConfig, ConfigLoader
from stock_tracker.utils.setup_logging import setup_logging
from stock_tracker.yfinance_api import get_yfinance_session, CachedLimiterSession


logger: logging.Logger = logging.getLogger(__name__)


def parse_orders(csv_path: str) -> list[dict[str, str]]:
    orders: list[dict[str, str]] = []
    with open(file=csv_path, mode="r") as file:
        reader: csv.DictReader[str] = csv.DictReader(file)
        for row in reader:
            # Process each row
            orders.append(row)
    return orders


def write_json_to_file(data: dict[Any, Any], filename: str) -> None:
    """Writes Python dictionary data to a JSON file.

    Args:
      data (dict): The Python dictionary to be written to the file.
      filename (str): The name of the JSON file to create or overwrite.
    """
    try:
        with open(filename, "w") as json_file:
            json.dump(data, json_file, indent=4)
        print(f"Data successfully written to '{filename}'")
    except IOError as e:
        print(f"Error writing to file '{filename}': {e}")


def calculate_order_capital_gains(order: dict[str, str], current_price: float) -> float:
    # Basic gain calculation
    # Diff between order price and current price
    # date,exchange,ticker,quantity,price_paid
    order_price: float = float(order["price_paid"]) * float(order["quantity"])
    current_total_price: float = current_price * float(order["quantity"])
    return current_total_price - order_price


def main() -> None:
    # Construct AppConfig private singelton instance
    parser = ConfigLoader.build_arg_parser(AppConfig)
    args = parser.parse_args()
    overrides = ConfigLoader.args_to_overrides(args)
    config = ConfigLoader.load_app_config(overrides=overrides)
    AppConfig.set(config)

    # Set up app
    setup_logging(config.log_config_path)
    session: CachedLimiterSession = get_yfinance_session()
    db: Database = Database(config.db_path)

    run_app(config, session, db)


def run_app(config: AppConfig, session: CachedLimiterSession, db: Database):
    """Run the application with explicit dependencies."""
    try:
        db.create_tables_if_not_exists()

        import_valid_tickers(config.csv_path, session)
        # performance = calculate_portfolio_performance(db, session)

        # Display results
        # display_performance(performance)
    finally:
        db.close()


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
