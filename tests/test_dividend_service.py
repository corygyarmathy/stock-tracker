import pytest
from datetime import datetime, date, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import yfinance as yf

from stock_tracker.models import Stock, Dividend
from stock_tracker.repositories.dividend_repository import DividendRepository
from stock_tracker.services.dividend_service import DividendService


class TestDividendService:
    """Tests for the DividendService class."""

    @pytest.fixture
    def mock_dividend_repo(self):
        """Create a mock dividend repository."""
        return MagicMock(spec=DividendRepository)

    @pytest.fixture
    def dividend_service(self, mock_dividend_repo):
        """Create a DividendService instance with mocked repository."""
        return DividendService(mock_dividend_repo)

    @pytest.fixture
    def stock(self):
        """Create a sample Stock object."""
        return Stock(
            id=1,
            ticker="AAPL",
            exchange="NASDAQ",
            currency="USD",
            name="Apple Inc.",
            yfinance_ticker="AAPL",
        )

    @pytest.fixture
    def mock_ticker_with_dividends(self):
        """Create a mock yfinance Ticker with dividend data."""
        ticker = MagicMock(spec=yf.Ticker)
        ticker.ticker = "AAPL"

        # Create a pandas Series for dividends
        dates = [
            pd.Timestamp("2023-01-15"),
            pd.Timestamp("2023-04-15"),
            pd.Timestamp("2023-07-15"),
            pd.Timestamp("2023-10-15"),
        ]
        values = [0.23, 0.24, 0.24, 0.25]
        ticker.dividends = pd.Series(values, index=dates)

        return ticker

    @pytest.fixture
    def mock_ticker_no_dividends(self):
        """Create a mock yfinance Ticker without dividend data."""
        ticker = MagicMock(spec=yf.Ticker)
        ticker.ticker = "NODIV"

        # Empty pandas Series for dividends
        ticker.dividends = pd.Series([])

        return ticker

    @patch("stock_tracker.services.dividend_service.TickerService.get_ticker_for_stock")
    def test_fetch_and_store_dividends_success(
        self,
        mock_get_ticker,
        mock_ticker_with_dividends,
        stock,
        dividend_service,
        mock_dividend_repo,
    ):
        """Test fetching and storing dividends with successful API call."""
        # Setup
        mock_get_ticker.return_value = mock_ticker_with_dividends

        # The dividend repo should report no existing dividends for these ex-dates
        mock_dividend_repo.get_dividend_by_ex_date.return_value = None

        # Test
        dividends = dividend_service.fetch_and_store_dividends(stock)

        # Assertions
        assert len(dividends) == 4
        for div in dividends:
            assert isinstance(div, Dividend)
            assert div.stock_id == 1

        # Verify repository interactions
        assert mock_dividend_repo.insert.call_count == 4

    @patch("stock_tracker.services.dividend_service.TickerService.get_ticker_for_stock")
    def test_fetch_and_store_dividends_existing(
        self,
        mock_get_ticker,
        mock_ticker_with_dividends,
        stock,
        dividend_service,
        mock_dividend_repo,
    ):
        """Test fetching dividends when some already exist in the database."""
        # Setup
        mock_get_ticker.return_value = mock_ticker_with_dividends

        # Mock existing dividend for the first two dates
        existing_div1 = Dividend(
            id=101,
            stock_id=1,
            ex_date=date(2023, 1, 15),
            payment_date=date(2023, 1, 30),
            amount=0.23,
            currency="USD",
        )
        existing_div2 = Dividend(
            id=102,
            stock_id=1,
            ex_date=date(2023, 4, 15),
            payment_date=date(2023, 4, 30),
            amount=0.24,
            currency="USD",
        )

        # First two calls return existing dividends, last two return None
        mock_dividend_repo.get_dividend_by_ex_date.side_effect = [
            existing_div1,
            existing_div2,
            None,
            None,
        ]

        # Test
        dividends = dividend_service.fetch_and_store_dividends(stock)

        # Assertions
        assert len(dividends) == 4

        # Should only insert the last two dividends (not the existing ones)
        assert mock_dividend_repo.insert.call_count == 2

    @patch("stock_tracker.services.dividend_service.TickerService.get_ticker_for_stock")
    def test_fetch_and_store_dividends_no_dividends(
        self, mock_get_ticker, mock_ticker_no_dividends, stock, dividend_service
    ):
        """Test fetching dividends when no dividends are available."""
        # Setup
        mock_get_ticker.return_value = mock_ticker_no_dividends

        # Test
        dividends = dividend_service.fetch_and_store_dividends(stock)

        # Assertions
        assert dividends == []  # Should be empty list

    @patch("stock_tracker.services.dividend_service.TickerService.get_ticker_for_stock")
    def test_fetch_and_store_dividends_no_ticker(self, mock_get_ticker, stock, dividend_service):
        """Test behavior when ticker cannot be obtained."""
        # Setup
        mock_get_ticker.return_value = None

        # Test
        dividends = dividend_service.fetch_and_store_dividends(stock)

        # Assertions
        assert dividends == []  # Should be empty list

    @patch("stock_tracker.services.dividend_service.TickerService.get_ticker_for_stock")
    def test_fetch_and_store_dividends_api_error(self, mock_get_ticker, stock, dividend_service):
        """Test behavior when API call raises an exception."""
        # Setup
        mock_ticker = MagicMock("test")
        mock_ticker.dividends = MagicMock(side_effect=Exception("API Error"))
        mock_get_ticker.return_value = mock_ticker

        # Test
        dividends = dividend_service.fetch_and_store_dividends(stock)

        # Assertions
        assert dividends == []  # Should be empty list

    def test_calculate_dividends_for_order(self, dividend_service, mock_dividend_repo):
        """Test calculating dividends for a specific order."""
        # Setup
        stock_id = 1
        quantity = 100.0
        purchase_date = datetime(2023, 1, 1)
        current_date = datetime(2023, 12, 31)

        # Create sample dividends
        dividends = [
            Dividend(
                id=1,
                stock_id=1,
                ex_date=date(2023, 2, 15),
                payment_date=date(2023, 3, 1),
                amount=0.23,
                currency="USD",
            ),
            Dividend(
                id=2,
                stock_id=1,
                ex_date=date(2023, 5, 15),
                payment_date=date(2023, 6, 1),
                amount=0.24,
                currency="USD",
            ),
            Dividend(
                id=3,
                stock_id=1,
                ex_date=date(2023, 8, 15),
                payment_date=date(2023, 9, 1),
                amount=0.24,
                currency="USD",
            ),
            Dividend(
                id=4,
                stock_id=1,
                ex_date=date(2023, 11, 15),
                payment_date=date(2023, 12, 1),
                amount=0.25,
                currency="USD",
            ),
        ]

        mock_dividend_repo.get_dividends_in_date_range.return_value = dividends

        # Test
        total_dividends = dividend_service.calculate_dividends_for_order(
            stock_id, quantity, purchase_date, current_date
        )

        # Assertions
        expected_total = (0.23 + 0.24 + 0.24 + 0.25) * 100.0
        assert total_dividends == pytest.approx(expected_total)
        mock_dividend_repo.get_dividends_in_date_range.assert_called_once_with(
            stock_id, purchase_date.date(), current_date.date()
        )

    def test_calculate_dividends_for_order_no_dividends(self, dividend_service, mock_dividend_repo):
        """Test calculating dividends when there are none."""
        # Setup
        stock_id = 1
        quantity = 100.0
        purchase_date = datetime(2023, 1, 1)
        current_date = datetime(2023, 12, 31)

        mock_dividend_repo.get_dividends_in_date_range.return_value = []

        # Test
        total_dividends = dividend_service.calculate_dividends_for_order(
            stock_id, quantity, purchase_date, current_date
        )

        # Assertions
        assert total_dividends == 0.0

    def test_estimate_payment_date(self, dividend_service):
        """Test estimating payment date from ex-date."""
        # Test
        ex_date = date(2023, 5, 15)
        payment_date = dividend_service._estimate_payment_date(ex_date)

        # Assertions
        expected_date = ex_date + timedelta(days=15)
        assert payment_date == expected_date

    def test_fetch_and_store_dividends_missing_stock_id(self, dividend_service):
        """Test behavior when stock has no ID."""
        # Setup
        stock = Stock(
            id=None,  # Missing ID
            ticker="AAPL",
            exchange="NASDAQ",
            currency="USD",
            name="Apple Inc.",
            yfinance_ticker="AAPL",
        )

        # Test
        with pytest.raises(ValueError, match="Cannot fetch dividends for stock without ID"):
            dividend_service.fetch_and_store_dividends(stock)

    def test_calculate_dividends_for_order_default_current_date(
        self, dividend_service, mock_dividend_repo
    ):
        """Test that current_date defaults to today when not provided."""
        # Setup
        stock_id = 1
        quantity = 100.0
        purchase_date = datetime(2023, 1, 1)

        mock_dividend_repo.get_dividends_in_date_range.return_value = []

        # Test
        with patch("stock_tracker.services.dividend_service.datetime") as mock_datetime:
            today = datetime(2023, 12, 31)
            mock_datetime.now.return_value = today

            dividend_service.calculate_dividends_for_order(stock_id, quantity, purchase_date)

            # Assert the repository was called with today's date
            mock_dividend_repo.get_dividends_in_date_range.assert_called_once_with(
                stock_id, purchase_date.date(), today.date()
            )
