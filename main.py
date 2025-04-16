# Import libraries
import csv
from typing import Any
import requests
import json
from datetime import datetime

from requests.exceptions import RequestException
import keys


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


def get_stock_price(symbol: str) -> tuple[float | None, str | None]:
    """
    Retrieves the latest stock price for a given symbol using the Alpha Vantage API.
    Returns a tuple: (price: float or None, error: str or None).
    """
    # TODO: Specify the currency, and convert it if necessary
    # TODO: Ensure can hangle stocks with the same ticker, that are listed in different exchanges
    if not keys.ALPHAVANTAGE_API_KEY:
        raise ValueError("Please set the ALPHAVANTAGE_API_KEY environment variable.")

    base_url = "https://www.alphavantage.co/query"
    params: dict[str, str] = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
        "apikey": keys.ALPHAVANTAGE_API_KEY,
    }
    try:
        response: requests.Response = requests.get(url=base_url, params=params)
        response.raise_for_status()  # Raise an exception for bad status codes
        data: dict[str, Any] = response.json()
        if "Global Quote" in data and "05. price" in data["Global Quote"]:
            return float(data["Global Quote"]["05. price"]), None
        else:
            return None, f"Could not retrieve price for {symbol}. Response: {data}"
    except requests.exceptions.RequestException as e:
        return None, f"Error during API request: {e}"
    except json.JSONDecodeError:
        return None, "Error decoding JSON response."


# def calculate_order_gains(order, current_price) -> float:
# Basic gain calculation
# Diff between order price and current price
# date,exchange,ticker,quantity,price_paid


def main() -> None:
    orders = parse_orders("orders.csv")
    for order in orders:
        price, error = get_stock_price(order["ticker"])
        if not error:
            print(f"{order['ticker']}: price: {price}")
        else:
            print(f"Error: {error}")

    print("Complete!")


# current_price = get_current_price(order["ticker"])
# gain = calculate_gains(order, current_price)
# print(f"{order['ticker']}: {gain}")


if __name__ == "__main__":
    _ = main()
