# Import libraries
import csv
from typing import Any
import requests
import json
from datetime import datetime
import keys


# Define core functions
def parse_orders(csv_path: str) -> list[dict[str, str]]:
    orders: list[dict[str, str]] = []
    with open(file=csv_path, mode="r") as file:
        reader: csv.DictReader[str] = csv.DictReader(file)
        for row in reader:
            # Process each row
            orders.append(row)
    return orders


# def get_current_price(ticker):
#     # API call logic


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


def get_stock_data(symbol: str) -> list[Any] | None:
    # Yahoo Finance API URL
    url: str = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

    # Add parameters for time range, interval etc.
    params: dict[str, str] = {
        "range": "1mo",  # 1 month of data
        "interval": "1d",  # daily data points
        "includePrePost": "false",
    }

    # Set a proper user agent to avoid blocks
    headers: dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    # Make the request
    response: requests.Response = requests.get(url, params=params, headers=headers)

    # Check if request was successful
    if response.status_code == 200:
        # Parse JSON response
        data: dict[Any, Any] = response.json()
        write_json_to_file(data, "data.json")

        # Extract the useful parts
        chart_data = data["chart"]["result"][0]
        timestamps = chart_data["timestamp"]
        quote_data = chart_data["indicators"]["quote"][0]

        # Convert timestamps to dates and create a list of price data
        price_data: list[Any] = []
        for i in range(len(timestamps)):
            date: str = datetime.fromtimestamp(timestamps[i]).strftime("%Y-%m-%d")
            price_data.append(
                {
                    "date": date,
                    "open": quote_data["open"][i],
                    "high": quote_data["high"][i],
                    "low": quote_data["low"][i],
                    "close": quote_data["close"][i],
                    "volume": quote_data["volume"][i],
                }
            )

        return price_data
    else:
        print(f"Error: {response.status_code}")


# def calculate_order_gains(order, current_price) -> float:
# Basic gain calculation
# Diff between order price and current price
# date,exchange,ticker,quantity,price_paid


def main() -> None:
    orders = parse_orders("orders.csv")
    for order in orders:
        get_stock_data(order["ticker"])
        print("Complete!")


# current_price = get_current_price(order["ticker"])
# gain = calculate_gains(order, current_price)
# print(f"{order['ticker']}: {gain}")


if __name__ == "__main__":
    _ = main()
