import csv
import json
from typing import Any


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
