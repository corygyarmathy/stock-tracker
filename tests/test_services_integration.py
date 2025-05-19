import pytest
from datetime import datetime, date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import yfinance as yf

from stock_tracker.config import AppConfig
from stock_tracker.db import Database
from stock_tracker.models import Stock, StockOrder, StockInfo, Dividend, PortfolioPerformance
from stock_tracker.repositories.dividend_repository import DividendRepository
from stock_tracker.repositories.order_repository import OrderRepository
from stock_tracker.repositories.stock_info_repository import StockInfoRepository
from stock_tracker.repositories.stock_repository import StockRepository
from stock_tracker.services.dividend_service import DividendService
from stock_tracker.services.portfolio_service import PortfolioService
from stock_tracker.services.ticker_service import TickerService


@pytest.fixture
def mock_yf_ticker():
    """Create a mock yfinance Ticker."""
    with patch("yfinance.Ticker") as mock:
        # Configure the mock ticker
        ticker = MagicMock()
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
        ticker.fast_info.last_price = 190.50

        # Create a pandas Series for dividends
        dates = [
            pd.Timestamp("2023-01-15"),
            pd.Timestamp("2023-04-15"),
            pd.Timestamp("2023-07-15"),
            pd.Timestamp("2023-10-15"),
        ]
        values = [0.23, 0.24, 0.24, 0.25]
        ticker.dividends = pd.Series(values, index=dates)

        mock.return_value = ticker
        yield ticker


@pytest.mark.integration
class TestServicesIntegration:
    """Integration tests for service interactions."""

    @patch("time.sleep")  # Prevent actual sleeping in tests
    def test_import_and_calculate_portfolio(self, mock_sleep, app_config, test_db, mock_yf_ticker):
        """Test the full flow from importing stock data to calculating portfolio performance."""
        # Set up services and repositories
        stock_repo = StockRepository(test_db)
        stock_info_repo = StockInfoRepository(test_db)
        order_repo = OrderRepository(test_db)
        dividend_repo = DividendRepository(test_db)

        dividend_service = DividendService(dividend_repo)
        portfolio_service = PortfolioService(stock_repo, order_repo, stock_info_repo, dividend_repo)

        # 1. Create and store a stock
        with patch("stock_tracker.services.ticker_service.yf.Ticker", return_value=mock_yf_ticker):
            # Use the ticker service to extract models
            stock, stock_info = TickerService.extract_models(mock_yf_ticker)

            # Store the stock
            stock_id = stock_repo.insert(stock)
            stock.id = stock_id

            # Update stock_info with the correct stock_id and store it
            stock_info.stock_id = stock_id
            stock_info_repo.insert(stock_info)

            # Verify stock was stored correctly
            stored_stock = stock_repo.get_by_id(stock_id)
            assert stored_stock is not None
            assert stored_stock.ticker == "AAPL"
            assert stored_stock.exchange == "NASDAQ"

            # 2. Add some orders for the stock
            orders = [
                StockOrder(
                    id=None,
                    stock_id=stock_id,
                    purchase_datetime=datetime(2023, 1, 1, 10, 0),
                    quantity=10,
                    price_paid=150.0,
                    fee=5.0,
                    note="Initial purchase",
                ),
                StockOrder(
                    id=None,
                    stock_id=stock_id,
                    purchase_datetime=datetime(2023, 6, 1, 14, 0),
                    quantity=5,
                    price_paid=170.0,
                    fee=5.0,
                    note="Adding to position",
                ),
            ]

            for order in orders:
                order_id = order_repo.insert(order)
                order.id = order_id

            # Verify orders were stored
            stored_orders = order_repo.get_orders_for_stock(stock_id)
            assert len(stored_orders) == 2

            # 3. Fetch and store dividends
            dividends = dividend_service.fetch_and_store_dividends(stock)

            # Verify dividends were stored
            assert len(dividends) == 4
            stored_dividends = dividend_repo.get_dividends_for_stock(stock_id)
            assert len(stored_dividends) == 4

            # 4. Calculate portfolio performance
            portfolio = portfolio_service.calculate_portfolio_performance()

            # Verify portfolio calculations
            assert isinstance(portfolio, PortfolioPerformance)
            assert len(portfolio.stocks) == 1

            stock_perf = portfolio.stocks[0]
            assert stock_perf.ticker == "AAPL"
            assert stock_perf.total_shares == 15  # 10 + 5

            # Calculate expected values
            expected_total_cost = (10 * 150.0 + 5.0) + (5 * 170.0 + 5.0)
            expected_current_value = 15 * 190.50
            expected_capital_gain = expected_current_value - expected_total_cost

            # Check calculations (using approximate due to floating point)
            assert stock_perf.total_cost == pytest.approx(expected_total_cost)
            assert stock_perf.current_value == pytest.approx(expected_current_value)
            assert stock_perf.capital_gain == pytest.approx(expected_capital_gain)

            # 5. Generate dividend report
            dividend_report = portfolio_service.calculate_dividend_report()

            assert len(dividend_report) == 1
            assert dividend_report[0]["stock"].ticker == "AAPL"
            assert dividend_report[0]["dividends_count"] == 4
            assert dividend_report[0]["total_amount"] == 0.23 + 0.24 + 0.24 + 0.25
            assert dividend_report[0]["last_ex_date"] == date(2023, 10, 15)


@pytest.mark.integration
class TestTickerServiceIntegration:
    """Integration tests focusing on the TickerService's interactions."""

    @pytest.mark.skipif(True, reason="Requires internet connection and real API calls")
    @patch("time.sleep")  # Prevent actual sleeping in tests
    def test_real_ticker_api(self, mock_sleep):
        """
        Test the ticker service with a real API call.

        This test makes real API calls and should be skipped by default.
        Run with --run-slow-tests flag to include it.
        """
        # This test skipped by default to avoid API rate limits and required internet
        ticker = TickerService.get_valid_ticker("AAPL", "NASDAQ")

        assert ticker is not None
        assert ticker.ticker == "AAPL"

        # Try getting a real model
        stock, stock_info = TickerService.extract_models(ticker)

        assert stock.ticker == "AAPL"
        assert stock.exchange == "NASDAQ"
        assert stock_info.current_price > 0

    def test_extract_models_integration(self, mock_yf_ticker):
        """Test that model extraction works correctly with mocked ticker data."""
        stock, stock_info = TickerService.extract_models(mock_yf_ticker)

        # Verify stock data
        assert stock.ticker == "AAPL"
        assert stock.exchange == "NASDAQ"
        assert stock.currency == "USD"
        assert stock.name == "Apple Inc."
        assert stock.id is None

        # Verify stock info data
        assert stock_info.stock_id == -1  # Temporary value to be updated
        assert stock_info.current_price == 190.50
        assert stock_info.market_cap == 3000000000000
        assert stock_info.pe_ratio == 30.5
        assert stock_info.dividend_yield == 0.005


@pytest.mark.integration
class TestDividendServiceIntegration:
    """Integration tests focusing on the DividendService's interactions."""

    @patch("time.sleep")  # Prevent actual sleeping in tests
    def test_fetch_and_calculate_dividends(self, mock_sleep, app_config, test_db, mock_yf_ticker):
        """Test fetching dividends and calculating returns."""
        # Set up repositories and services
        stock_repo = StockRepository(test_db)
        dividend_repo = DividendRepository(test_db)
        dividend_service = DividendService(dividend_repo)

        # Create and store a stock
        with patch("stock_tracker.services.ticker_service.yf.Ticker", return_value=mock_yf_ticker):
            # Extract and store stock
            stock = Stock(
                id=None,
                ticker="AAPL",
                exchange="NASDAQ",
                currency="USD",
                name="Apple Inc.",
                yfinance_ticker="AAPL",
            )
            stock_id = stock_repo.insert(stock)
            stock.id = stock_id

            # Fetch and store dividends
            dividends = dividend_service.fetch_and_store_dividends(stock)

            # Verify dividends were stored
            assert len(dividends) == 4
            stored_dividends = dividend_repo.get_dividends_for_stock(stock_id)
            assert len(stored_dividends) == 4

            # Calculate dividends for a specific order
            purchase_date = datetime(2023, 2, 1)  # After the first dividend
            current_date = datetime(2023, 11, 1)  # After all dividends
            quantity = 10.0

            # Should include the last 3 dividends (Apr, Jul, Oct)
            dividends_received = dividend_service.calculate_dividends_for_order(
                stock_id, quantity, purchase_date, current_date
            )

            # Expected: (0.24 + 0.24 + 0.25) * 10 = 7.3
            expected_dividends = (0.24 + 0.24 + 0.25) * 10
            assert dividends_received == pytest.approx(expected_dividends)

            # Try with different date range (only last dividend)
            late_purchase = datetime(2023, 8, 1)  # After July dividend
            dividends_received = dividend_service.calculate_dividends_for_order(
                stock_id, quantity, late_purchase, current_date
            )

            # Expected: 0.25 * 10 = 2.5
            expected_dividends = 0.25 * 10
            assert dividends_received == pytest.approx(expected_dividends)


@pytest.mark.integration
class TestPortfolioServiceIntegration:
    """Integration tests focusing on the PortfolioService's interactions."""

    def test_portfolio_calculations_with_real_db(self, app_config, test_db):
        """Test portfolio calculations using the actual database."""
        # Set up repositories and services
        stock_repo = StockRepository(test_db)
        stock_info_repo = StockInfoRepository(test_db)
        order_repo = OrderRepository(test_db)
        dividend_repo = DividendRepository(test_db)
        portfolio_service = PortfolioService(stock_repo, order_repo, stock_info_repo, dividend_repo)

        # Create two stocks
        stock1 = Stock(
            id=None,
            ticker="AAPL",
            exchange="NASDAQ",
            currency="USD",
            name="Apple Inc.",
            yfinance_ticker="AAPL",
        )
        stock1_id = stock_repo.insert(stock1)
        stock1.id = stock1_id

        stock2 = Stock(
            id=None,
            ticker="MSFT",
            exchange="NASDAQ",
            currency="USD",
            name="Microsoft Corp",
            yfinance_ticker="MSFT",
        )
        stock2_id = stock_repo.insert(stock2)
        stock2.id = stock2_id

        # Create stock info for both
        stock_info1 = StockInfo(
            stock_id=stock1_id,
            last_updated_datetime=datetime(2023, 12, 1, 16, 0),
            current_price=190.50,
            market_cap=3000000000000,
            pe_ratio=30.5,
            dividend_yield=0.005,
        )
        stock_info_repo.insert(stock_info1)

        stock_info2 = StockInfo(
            stock_id=stock2_id,
            last_updated_datetime=datetime(2023, 12, 1, 16, 0),
            current_price=330.0,
            market_cap=2500000000000,
            pe_ratio=35.2,
            dividend_yield=0.010,
        )
        stock_info_repo.insert(stock_info2)

        # Create orders for both stocks
        orders = [
            # AAPL orders
            StockOrder(
                id=None,
                stock_id=stock1_id,
                purchase_datetime=datetime(2023, 1, 1, 10, 0),
                quantity=10,
                price_paid=150.0,
                fee=5.0,
                note="AAPL Initial purchase",
            ),
            StockOrder(
                id=None,
                stock_id=stock1_id,
                purchase_datetime=datetime(2023, 6, 1, 14, 0),
                quantity=5,
                price_paid=170.0,
                fee=5.0,
                note="AAPL Adding to position",
            ),
            # MSFT orders
            StockOrder(
                id=None,
                stock_id=stock2_id,
                purchase_datetime=datetime(2023, 2, 10, 9, 15),
                quantity=8,
                price_paid=280.0,
                fee=5.0,
                note="MSFT Initial purchase",
            ),
        ]

        for order in orders:
            order_repo.insert(order)

        # Create dividends
        dividends = [
            # AAPL dividends
            Dividend(
                id=None,
                stock_id=stock1_id,
                ex_date=date(2023, 2, 9),
                payment_date=date(2023, 2, 24),
                amount=0.23,
                currency="USD",
            ),
            Dividend(
                id=None,
                stock_id=stock1_id,
                ex_date=date(2023, 5, 11),
                payment_date=date(2023, 5, 26),
                amount=0.24,
                currency="USD",
            ),
            Dividend(
                id=None,
                stock_id=stock1_id,
                ex_date=date(2023, 8, 10),
                payment_date=date(2023, 8, 25),
                amount=0.24,
                currency="USD",
            ),
            Dividend(
                id=None,
                stock_id=stock1_id,
                ex_date=date(2023, 11, 9),
                payment_date=date(2023, 11, 24),
                amount=0.25,
                currency="USD",
            ),
            # MSFT dividends
            Dividend(
                id=None,
                stock_id=stock2_id,
                ex_date=date(2023, 2, 15),
                payment_date=date(2023, 3, 9),
                amount=0.68,
                currency="USD",
            ),
            Dividend(
                id=None,
                stock_id=stock2_id,
                ex_date=date(2023, 5, 17),
                payment_date=date(2023, 6, 8),
                amount=0.68,
                currency="USD",
            ),
            Dividend(
                id=None,
                stock_id=stock2_id,
                ex_date=date(2023, 8, 16),
                payment_date=date(2023, 9, 14),
                amount=0.75,
                currency="USD",
            ),
            Dividend(
                id=None,
                stock_id=stock2_id,
                ex_date=date(2023, 11, 15),
                payment_date=date(2023, 12, 14),
                amount=0.75,
                currency="USD",
            ),
        ]

        for dividend in dividends:
            dividend_repo.insert(dividend)

        # Test portfolio performance calculation
        portfolio = portfolio_service.calculate_portfolio_performance()

        # Verify portfolio totals
        assert isinstance(portfolio, PortfolioPerformance)
        assert len(portfolio.stocks) == 2

        # Calculate expected values
        aapl_cost = (10 * 150.0 + 5.0) + (5 * 170.0 + 5.0)
        msft_cost = 8 * 280.0 + 5.0
        total_cost = aapl_cost + msft_cost

        aapl_value = 15 * 190.50
        msft_value = 8 * 330.0
        total_value = aapl_value + msft_value

        capital_gain = total_value - total_cost

        # Test dividend report calculation
        dividend_report = portfolio_service.calculate_dividend_report()

        assert len(dividend_report) == 2

        # Find AAPL entry
        aapl_entry = next(
            (entry for entry in dividend_report if entry["stock"].ticker == "AAPL"), None
        )
        assert aapl_entry is not None
        assert aapl_entry["total_amount"] == 0.23 + 0.24 + 0.24 + 0.25
        assert aapl_entry["dividends_count"] == 4

        # Find MSFT entry
        msft_entry = next(
            (entry for entry in dividend_report if entry["stock"].ticker == "MSFT"), None
        )
        assert msft_entry is not None
        assert msft_entry["total_amount"] == 0.68 + 0.68 + 0.75 + 0.75
        assert msft_entry["dividends_count"] == 4
