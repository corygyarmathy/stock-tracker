# Import libraries
import csv
from typing import Any
import yfinance as yf
import json

import argparse
from tickers import import_valid_tickers
from utils import setup_logging
from tickers import (
    CachedLimiterSession,
    # get_symbol_for_exchange,
    get_yfinance_session,
    is_valid_ticker,
    search_ticker,
)


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
) -> tuple[float | None, str | None]:
    """
    Retrieves the latest stock price for a given symbol using the Alpha Vantage API.
    Returns a tuple: (price: float or None, error: str or None).
    """
    # TODO: Specify the currency, and convert it if necessary
    # TODO: Ensure can hangle stocks with the same ticker, that are listed in different exchanges
    try:
        # stock_ticker = ticker
        if exchange:
            ticker = f"{ticker}.{exchange}"
            print("Formatted ticker " + ticker)
        # if exchange:
        #     stock_ticker, symbol_err = get_symbol_for_exchange(
        #         ticker, exchange, session
        #     )
        #     if not stock_ticker:
        #         print(f"{symbol_err}")
        #         stock_ticker = ticker
        data: yf.Ticker = yf.Ticker(ticker, session)
        if data.fast_info["last_price"]:
            price: float = float(data.fast_info["last_price"])
            return price, None
        else:
            return (
                None,
                f"Could not retrieve price for {ticker} at {exchange}. Retrieved: {data}",
            )
    except Exception as e:
        return None, f"Error retrieving price for {ticker} at {exchange}. Error: {e}"


def calculate_order_capital_gains(order: dict[str, str], current_price: float) -> float:
    # Basic gain calculation
    # Diff between order price and current price
    # date,exchange,ticker,quantity,price_paid
    order_price: float = float(order["price_paid"]) * float(order["quantity"])
    current_total_price: float = current_price * float(order["quantity"])
    return current_total_price - order_price


# def import_valid_tickers(csv_path: str, db_path: str, session: CachedLimiterSession):
#     # Load CSV
#     df: pd.DataFrame = pd.read_csv(csv_path)
#
#     # Connect to (or create) SQLite DB
#     conn: sqlite3.Connection = sqlite3.connect(db_path)
#     cursor: sqlite3.Cursor = conn.cursor()
#
#     # Create table if it doesn't exist
#     _ = cursor.execute("""
#         CREATE TABLE IF NOT EXISTS tickers (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             symbol TEXT NOT NULL,
#             exchange TEXT NOT NULL,
#             full_symbol TEXT UNIQUE NOT NULL
#         );
#     """)
#
#     inserted = 0
#     for _, row in df.iterrows():
#         ticker = str(row["ticker"]).strip()
#         exchange = str(row["exchange"]).strip()
#         full_symbol = f"{ticker}.{exchange}"
#
#         if is_valid_ticker(ticker, exchange, session):
#             try:
#                 _ = cursor.execute(
#                     "INSERT OR IGNORE INTO tickers (symbol, exchange, full_symbol) VALUES (?, ?, ?)",
#                     (ticker, exchange, full_symbol),
#                 )
#                 inserted += 1
#                 print(f"Inserted: {full_symbol}")
#             except Exception as e:
#                 print(f"Failed to insert {full_symbol}: {e}")
#         else:
#             print(f"Invalid: {full_symbol}")
#
#     conn.commit()
#     conn.close()
#     print(f"\nDone! {inserted} valid tickers inserted.")


def main(args: argparse.Namespace) -> None:
    # orders: list[dict[str, str]] = parse_orders(csv_path="orders.csv")
    session: CachedLimiterSession = get_yfinance_session()

    setup_logging(args.log_config)
    import_valid_tickers(args.csv_path, args.db_path, session)

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


if __name__ == "__main__":
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Import tickers from CSV and validate with yfinance."
    )
    _ = parser.add_argument(
        "csv_path", help="Path to input CSV file (must have 'ticker' and 'exchange')"
    )
    _ = parser.add_argument("db_path", help="Path to SQLite DB")
    _ = parser.add_argument(
        "--log-config",
        default="logging_config.yaml",
        help="Path to logging config YAML",
    )
    args: argparse.Namespace = parser.parse_args()

    _ = main(args)
