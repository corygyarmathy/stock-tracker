# Import libraries
import csv
from typing import Any
import yfinance as yf
import json
import logging
from stock_tracker.db import Database
from stock_tracker.tickers import (
    CachedLimiterSession,
    get_yfinance_session,
)
from stock_tracker.utils import setup_logging

from stock_tracker.config import AppConfig, ConfigLoader

logger: logging.Logger = logging.getLogger("main")


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


def get_stock_price(
    ticker: str, session: CachedLimiterSession, exchange: str | None = None
) -> float:
    """
    Retrieves the latest stock price for a given symbol using the Alpha Vantage API.
    Returns a tuple: (price: float or None, error: str or None).
    """
    # TODO: Specify the currency, and convert it if necessary
    # TODO: Ensure can hangle stocks with the same ticker, that are listed in different exchanges
    try:
        logger.debug(f"Checking {ticker} price in exchange: {exchange}.")
        full_ticker: str = f"{ticker}.{exchange}" if exchange else ticker
        data: yf.Ticker = yf.Ticker(full_ticker, session=session)

        last_price = data.fast_info.last_price
        if last_price is not None:
            logger.debug(f"{ticker} price is: {last_price}.")
            return float(last_price)
        raise ValueError(f"No price found for {full_ticker}")
    except Exception as e:
        raise ValueError(f"Failed to retrieve price for {ticker} at {exchange}: {e}")


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

    setup_logging(config.log_config_path)

    session: CachedLimiterSession = get_yfinance_session()

    with Database(config.db_path) as db:
        _ = db.create_tables_if_not_exists()

    import_valid_tickers(config.csv_path, session)

    # orders: list[dict[str, str]] = parse_orders(csv_path="orders.csv")
    # ticker_splits = yf.Ticker("APPL", session).splits
    # data: yf.Ticker = yf.Ticker("IVV")

    # for order in orders:
    #     print(search_ticker(order["ticker"], session))
    #     print(f"Processing order: {order['ticker']}")
    #     print(f"Quantity purchased: {order['quantity']}")
    #     print(f"Purchase price: {order['price_paid']}")
    #     print(f"Purchase date: {order['date']}")
    #     print(f"Exchange: {order['exchange']}")
    #     current_price, error = get_stock_price(
    #         ticker=order["ticker"], exchange=order["exchange"], session=session
    #     )
    #     if not current_price:
    #         print(f"{error}")
    #         continue
    #
    #     print(f"Current price: {round(current_price, 2)}")
    #     capital_gain: float = calculate_order_capital_gains(order, current_price)
    #     print(f"Capital Gains: {round(capital_gain, 2)}")
    #     print()
    #
    # print("Complete!")
    #

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
