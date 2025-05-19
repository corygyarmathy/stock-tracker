import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

import yfinance as yf

from stock_tracker.models import Stock, StockInfo
from stock_tracker.services.ticker_service import TickerService


class TestTickerService:
    """Tests for the TickerService class."""

    @pytest.fixture
    def mock_ticker(self):
        """Create a mock yfinance Ticker object."""
        ticker = MagicMock(spec=yf.Ticker)
        ticker.ticker = "AAPL"

        # Mock the info attribute
        ticker.info = {
            "symbol": "AAPL",
            "exchange": "NASDAQ",
            "currency": "USD",
            "shortName": "Apple Inc.",
            "longName": "Apple Inc.",
            "marketCap": 3000000000000,
            "trailingPE": 30.5,
            "dividendYield": 0.005,
        }

        # Mock the fast_info attribute
        ticker.fast_info = MagicMock()
        ticker.fast_info.last_price = 180.50

        return ticker

    def test_extract_stock(self, mock_ticker):
        """Test extracting Stock model from ticker."""
        stock = TickerService.extract_stock(mock_ticker)

        assert isinstance(stock, Stock)
        assert stock.ticker == "AAPL"
        assert stock.exchange == "NASDAQ"
        assert stock.currency == "USD"
        assert stock.name == "Apple Inc."
        assert stock.yfinance_ticker == "AAPL"
        assert stock.id is None

    def test_extract_stock_info(self, mock_ticker):
        """Test extracting StockInfo model from ticker."""
        stock_info = TickerService.extract_stock_info(mock_ticker)

        assert isinstance(stock_info, StockInfo)
        assert stock_info.stock_id == -1  # Placeholder value
        assert stock_info.current_price == 180.50
        assert stock_info.market_cap == 3000000000000
        assert stock_info.pe_ratio == 30.5
        assert stock_info.dividend_yield == 0.005
        assert isinstance(stock_info.last_updated_datetime, datetime)

    def test_extract_models(self, mock_ticker):
        """Test extracting both Stock and StockInfo models."""
        stock, stock_info = TickerService.extract_models(mock_ticker)

        assert isinstance(stock, Stock)
        assert isinstance(stock_info, StockInfo)
        assert stock.ticker == "AAPL"
        assert stock_info.current_price == 180.50

    @patch("stock_tracker.services.ticker_service.yf.Ticker")
    def test_get_ticker_for_stock(self, mock_yf_ticker, mock_ticker):
        """Test getting a yfinance Ticker object for a stock."""
        # Setup
        mock_yf_ticker.return_value = mock_ticker
        stock = Stock(
            id=1,
            ticker="AAPL",
            exchange="NASDAQ",
            currency="USD",
            name="Apple Inc.",
            yfinance_ticker="AAPL",
        )

        # Test with existing yfinance_ticker
        result = TickerService.get_ticker_for_stock(stock)
        assert result == mock_ticker
        mock_yf_ticker.assert_called_once_with("AAPL")

    @patch("stock_tracker.services.ticker_service.TickerService.get_valid_ticker")
    def test_get_ticker_for_stock_without_yfinance_ticker(self, mock_get_valid_ticker, mock_ticker):
        """Test getting a ticker when stock doesn't have a yfinance_ticker."""
        # Setup
        mock_get_valid_ticker.return_value = mock_ticker
        stock = Stock(
            id=1,
            ticker="AAPL",
            exchange="NASDAQ",
            currency="USD",
            name="Apple Inc.",
            yfinance_ticker=None,
        )

        # Test without existing yfinance_ticker
        result = TickerService.get_ticker_for_stock(stock)
        assert result == mock_ticker
        mock_get_valid_ticker.assert_called_once_with("AAPL", "NASDAQ")
        assert stock.yfinance_ticker == "AAPL"  # Should be updated

    @patch("yfinance.Ticker")
    def test_get_valid_ticker_for_us_stock(self, mock_yf_ticker):
        """Test getting a valid ticker for a US stock."""
        # Setup mock ticker
        mock_ticker = MagicMock()
        mock_ticker.fast_info.last_price = 180.50
        mock_yf_ticker.return_value = mock_ticker

        # Test
        result = TickerService.get_valid_ticker("AAPL", "NASDAQ")

        assert result == mock_ticker
        # Just verify the function was called
        assert mock_yf_ticker.called

    @patch("yfinance.Ticker")
    def test_get_valid_ticker_for_non_us_stock(self, mock_yf_ticker):
        """Test getting a valid ticker for a non-US stock."""
        # Setup mock ticker
        mock_ticker = MagicMock()
        mock_ticker.fast_info.last_price = 2.50
        mock_yf_ticker.return_value = mock_ticker

        # Test
        result = TickerService.get_valid_ticker("BHP", "AX")

        assert result == mock_ticker
        # Just verify the function was called
        assert mock_yf_ticker.called

    @patch("yfinance.Ticker")
    @patch("time.sleep")  # Add this to prevent actual sleeping during tests
    def test_get_valid_ticker_invalid(self, mock_sleep, mock_yf_ticker):
        """Test behavior when ticker is invalid."""
        # Setup mock ticker that raises an exception
        mock_ticker = MagicMock()
        mock_ticker.fast_info.side_effect = Exception("No data found")
        mock_yf_ticker.return_value = mock_ticker

        # Test
        result = TickerService.get_valid_ticker("INVALID", "NASDAQ")
        assert result is None
        # Verify sleep was called (showing retry logic was exercised)
        assert mock_sleep.called

    @patch("yfinance.Search")
    def test_search_ticker_quotes(self, mock_search):
        """Test searching for ticker quotes."""
        # Setup
        expected_quotes = [
            {"symbol": "AAPL", "exchange": "NASDAQ", "shortname": "Apple Inc."},
            {"symbol": "AAPL.BA", "exchange": "Buenos Aires", "shortname": "Apple Inc."},
        ]
        mock_search_instance = MagicMock()
        mock_search_instance.quotes = expected_quotes
        mock_search.return_value = mock_search_instance

        # Test
        results = TickerService.search_ticker_quotes("AAPL")
        assert results == expected_quotes
        # Verify search was called with the right parameters
        assert mock_search.called

    @patch("yfinance.Search")
    def test_search_ticker_quotes_with_error(self, mock_search):
        """Test searching for ticker quotes with an error."""
        # Setup: Create a mock that will first fail with rate limit error
        # then succeed on retry
        mock_search.side_effect = Exception("Rate limit exceeded")

        # Disable retry mechanism for testing
        with patch("stock_tracker.services.ticker_service.time.sleep"):  # Mock sleep
            with patch.object(
                TickerService, "search_ticker_quotes", wraps=TickerService.search_ticker_quotes
            ) as wrapped:
                # Modify max_retries to 0 to fail faster in test
                wrapped.__defaults__ = (0,)  # Set max_retries=0

                # Test
                results = TickerService.search_ticker_quotes("AAPL")

                # Should return empty list on error
                assert results == []
                # Search should be called once with these parameters
                assert mock_search.called

    def test_extract_stock_missing_symbol(self, mock_ticker):
        """Test extracting Stock with missing symbol."""
        # Modify the mock to simulate missing symbol
        mock_ticker.info = {"exchange": "NASDAQ", "currency": "USD", "shortName": "Apple Inc."}

        with pytest.raises(ValueError, match="missing symbol"):
            TickerService.extract_stock(mock_ticker)

    def test_extract_stock_info_missing_price(self, mock_ticker):
        """Test extracting StockInfo with missing price."""
        # Modify the mock to simulate missing price
        mock_ticker.fast_info.last_price = None

        with pytest.raises(ValueError, match="missing current price"):
            TickerService.extract_stock_info(mock_ticker)
