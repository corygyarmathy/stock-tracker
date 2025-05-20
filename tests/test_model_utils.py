from datetime import datetime, date
import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from stock_tracker.models import Stock, StockOrder
from stock_tracker.utils.model_utils import ModelFactory


class TestModelFactory:
    """Tests for the ModelFactory class."""

    def test_create_from_row(self):
        """Test creating a model instance from a database row."""
        # Create a mock database row
        row_data = {
            "id": 1,
            "ticker": "AAPL",
            "exchange": "NASDAQ",
            "currency": "USD",
            "name": "Apple Inc.",
            "yfinance_ticker": "AAPL",
        }

        # Create a mock of sqlite3.Row that behaves like a dictionary
        mock_row = MagicMock(spec=sqlite3.Row)
        # Configure __getitem__ to act like dict.__getitem__
        mock_row.__getitem__.side_effect = lambda key: row_data[key]
        # Configure keys to return row_data keys
        mock_row.keys.return_value = row_data.keys()

        # Create Stock model from row
        stock = ModelFactory.create_from_row(Stock, mock_row)

        # Verify fields
        assert isinstance(stock, Stock)
        assert stock.id == 1
        assert stock.ticker == "AAPL"
        assert stock.exchange == "NASDAQ"
        assert stock.currency == "USD"
        assert stock.name == "Apple Inc."
        assert stock.yfinance_ticker == "AAPL"

    def test_create_from_row_with_date(self):
        """Test creating a model instance with date field conversion."""
        # Create a row with a date field
        row_data = {
            "id": 1,
            "stock_id": 1,
            "action_type": "split",
            "action_date": "2023-05-15",  # Date as string
            "ratio": 2.0,
            "target_stock_id": 1,
        }

        # Mock sqlite3.Row
        mock_row = MagicMock(spec=sqlite3.Row)
        mock_row.__getitem__.side_effect = lambda key: row_data[key]
        mock_row.keys.return_value = row_data.keys()

        # Create model from row with date conversion
        from stock_tracker.models import CorporateAction

        action = ModelFactory.create_from_row(CorporateAction, mock_row)

        # Verify fields, especially date conversion
        assert isinstance(action, CorporateAction)
        assert action.id == 1
        assert action.action_type == "split"
        assert isinstance(action.action_date, date)
        assert action.action_date == date(2023, 5, 15)
        assert action.ratio == 2.0

    def test_create_from_row_with_datetime(self):
        """Test creating a model instance with datetime field conversion."""
        # Create a row with a datetime field
        row_data = {
            "id": 1,
            "stock_id": 1,
            "purchase_datetime": "2023-05-15 10:30:45",  # Datetime as string
            "quantity": 10,
            "price_paid": 150.25,
            "fee": 4.99,
            "note": "Test purchase",
        }

        # Mock sqlite3.Row
        mock_row = MagicMock(spec=sqlite3.Row)
        mock_row.__getitem__.side_effect = lambda key: row_data[key]
        mock_row.keys.return_value = row_data.keys()

        # Create model from row with datetime conversion
        order = ModelFactory.create_from_row(StockOrder, mock_row)

        # Verify fields, especially datetime conversion
        assert isinstance(order, StockOrder)
        assert order.id == 1
        assert isinstance(order.purchase_datetime, datetime)
        assert order.purchase_datetime == datetime(2023, 5, 15, 10, 30, 45)
        assert order.quantity == 10
        assert order.price_paid == 150.25

    def test_create_list_from_rows(self):
        """Test creating a list of model instances from database rows."""
        # Create mock row data
        rows_data = [
            {
                "id": 1,
                "ticker": "AAPL",
                "exchange": "NASDAQ",
                "currency": "USD",
                "name": "Apple Inc.",
                "yfinance_ticker": "AAPL",
            },
            {
                "id": 2,
                "ticker": "MSFT",
                "exchange": "NASDAQ",
                "currency": "USD",
                "name": "Microsoft Corp",
                "yfinance_ticker": "MSFT",
            },
            {
                "id": 3,
                "ticker": "GOOG",
                "exchange": "NASDAQ",
                "currency": "USD",
                "name": "Alphabet Inc.",
                "yfinance_ticker": "GOOG",
            },
        ]

        # Convert to mock sqlite3.Row objects
        mock_rows = []
        for row_data in rows_data:
            mock_row = MagicMock(spec=sqlite3.Row)
            mock_row.__getitem__.side_effect = lambda key, data=row_data: data[key]
            mock_row.keys.return_value = row_data.keys()
            mock_rows.append(mock_row)

        # Create list of models
        stocks = ModelFactory.create_list_from_rows(Stock, mock_rows)

        # Verify results
        assert len(stocks) == 3
        assert all(isinstance(stock, Stock) for stock in stocks)
        assert [stock.ticker for stock in stocks] == ["AAPL", "MSFT", "GOOG"]
        assert [stock.id for stock in stocks] == [1, 2, 3]

    def test_invalid_date_format(self):
        """Test handling of invalid date format."""
        row_data = {
            "id": 1,
            "stock_id": 1,
            "action_type": "split",
            "action_date": "not-a-date",  # Invalid date format
            "ratio": 2.0,
            "target_stock_id": 1,
        }

        # Mock sqlite3.Row
        mock_row = MagicMock(spec=sqlite3.Row)
        mock_row.__getitem__.side_effect = lambda key: row_data[key]
        mock_row.keys.return_value = row_data.keys()

        # Create model from row - should keep invalid date as string
        from stock_tracker.models import CorporateAction

        action = ModelFactory.create_from_row(CorporateAction, mock_row)

        # String should be preserved as is
        assert action.action_date == "not-a-date"
