from datetime import datetime
from sqlite3 import Row
from typing import Any, TypeVar

# Generic type for any model class
T = TypeVar("T")


class ModelFactory:
    """Factory class to create domain models from database rows"""

    @staticmethod
    def create_from_row(model_class: type[T], row: Row) -> T:
        """Create a model instance from a database row dictionary"""
        # Copy the row to avoid modifying the original
        processed_data: dict[str, Any] = dict(row)

        # Process date fields
        for key, value in processed_data.items():
            if isinstance(value, str) and (key.endswith("_date") or key == "date"):
                try:
                    processed_data[key] = datetime.strptime(value, "%Y-%m-%d").date()
                except ValueError:
                    # Not a valid date format, keep as is
                    pass
            elif isinstance(value, str) and (key.endswith("_datetime") or key == "datetime"):
                try:
                    processed_data[key] = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    # Not a valid datetime format, keep as is
                    pass
        # Create the model with processed data
        return model_class(**processed_data)

    @staticmethod
    def create_list_from_rows(model_class: type[T], rows: list[Row]) -> list[T]:
        """Create a list of model instances from database rows"""
        return [ModelFactory.create_from_row(model_class, row) for row in rows]
