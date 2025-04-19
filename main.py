# Import libraries
import csv
from typing import Any
import yfinance as yf
import json

from API import CachedLimiterSession, get_yfinance_session


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
    ticker: str, exchange: str | None = None
) -> tuple[float | None, str | None]:
    """
    Retrieves the latest stock price for a given symbol using the Alpha Vantage API.
    Returns a tuple: (price: float or None, error: str or None).
    """
    # TODO: Specify the currency, and convert it if necessary
    # TODO: Ensure can hangle stocks with the same ticker, that are listed in different exchanges
    try:
        session: CachedLimiterSession = get_yfinance_session()
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


def main() -> None:
    orders: list[dict[str, str]] = parse_orders(csv_path="orders.csv")
    for order in orders:
        print(f"Processing order: {order['ticker']}")
        print(f"Quantity purchased: {order['quantity']}")
        print(f"Purchase price: {order['price_paid']}")
        print(f"Purchase date: {order['date']}")
        print(f"Exchange: {order['exchange']}")
        current_price, error = get_stock_price(
            ticker=order["ticker"], exchange=order["exchange"]
        )
        if not current_price:
            print(f"{error}")
            continue

        print(f"Current price: {round(current_price, 2)}")
        capital_gain: float = calculate_order_capital_gains(order, current_price)
        print(f"Capital Gains: {round(capital_gain, 2)}")
        print()

    print("Complete!")


if __name__ == "__main__":
    _ = main()
