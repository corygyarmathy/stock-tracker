import pytest
from datetime import datetime, date
from unittest.mock import MagicMock

from stock_tracker.models import (
    Stock,
    StockOrder,
    StockInfo,
    StockPerformance,
    PortfolioPerformance,
    Dividend,
)
from stock_tracker.repositories.dividend_repository import DividendRepository
from stock_tracker.repositories.order_repository import OrderRepository
from stock_tracker.repositories.stock_info_repository import StockInfoRepository
from stock_tracker.repositories.stock_repository import StockRepository
from stock_tracker.services.portfolio_service import PortfolioService


class TestPortfolioService:
    """Tests for the PortfolioService class."""

    @pytest.fixture
    def mock_stock_repo(self):
        """Create a mock stock repository."""
        return MagicMock(spec=StockRepository)

    @pytest.fixture
    def mock_order_repo(self):
        """Create a mock order repository."""
        return MagicMock(spec=OrderRepository)

    @pytest.fixture
    def mock_stock_info_repo(self):
        """Create a mock stock info repository."""
        return MagicMock(spec=StockInfoRepository)

    @pytest.fixture
    def mock_dividend_repo(self):
        """Create a mock dividend repository."""
        return MagicMock(spec=DividendRepository)

    @pytest.fixture
    def portfolio_service(
        self, mock_stock_repo, mock_order_repo, mock_stock_info_repo, mock_dividend_repo
    ):
        """Create a PortfolioService instance with mocked repositories."""
        return PortfolioService(
            mock_stock_repo, mock_order_repo, mock_stock_info_repo, mock_dividend_repo
        )

    @pytest.fixture
    def sample_stocks(self):
        """Create sample stock data."""
        return [
            Stock(
                id=1,
                ticker="AAPL",
                exchange="NASDAQ",
                currency="USD",
                name="Apple Inc.",
                yfinance_ticker="AAPL",
            ),
            Stock(
                id=2,
                ticker="MSFT",
                exchange="NASDAQ",
                currency="USD",
                name="Microsoft Corp",
                yfinance_ticker="MSFT",
            ),
            Stock(
                id=3,
                ticker="GOOGL",
                exchange="NASDAQ",
                currency="USD",
                name="Alphabet Inc.",
                yfinance_ticker="GOOGL",
            ),
        ]

    @pytest.fixture
    def sample_orders(self):
        """Create sample order data for each stock."""
        return {
            1: [  # AAPL orders
                StockOrder(
                    id=1,
                    stock_id=1,
                    purchase_datetime=datetime(2023, 1, 15, 10, 30),
                    quantity=10,
                    price_paid=150.0,
                    fee=5.0,
                ),
                StockOrder(
                    id=2,
                    stock_id=1,
                    purchase_datetime=datetime(2023, 5, 20, 14, 45),
                    quantity=5,
                    price_paid=170.0,
                    fee=5.0,
                ),
            ],
            2: [  # MSFT orders
                StockOrder(
                    id=3,
                    stock_id=2,
                    purchase_datetime=datetime(2023, 2, 10, 9, 15),
                    quantity=8,
                    price_paid=280.0,
                    fee=5.0,
                ),
            ],
            3: [  # GOOGL orders
                StockOrder(
                    id=4,
                    stock_id=3,
                    purchase_datetime=datetime(2023, 3, 5, 11, 0),
                    quantity=4,
                    price_paid=2200.0,
                    fee=5.0,
                ),
            ],
        }

    @pytest.fixture
    def sample_stock_info(self):
        """Create sample stock info data for each stock."""
        return {
            1: StockInfo(
                stock_id=1,
                last_updated_datetime=datetime(2023, 12, 1, 16, 0),
                current_price=190.0,
                market_cap=3000000000000,
                pe_ratio=30.5,
                dividend_yield=0.005,
            ),
            2: StockInfo(
                stock_id=2,
                last_updated_datetime=datetime(2023, 12, 1, 16, 0),
                current_price=330.0,
                market_cap=2500000000000,
                pe_ratio=35.2,
                dividend_yield=0.01,
            ),
            3: StockInfo(
                stock_id=3,
                last_updated_datetime=datetime(2023, 12, 1, 16, 0),
                current_price=2800.0,
                market_cap=1800000000000,
                pe_ratio=25.8,
                dividend_yield=0.0,
            ),
        }

    def test_calculate_portfolio_performance(
        self,
        portfolio_service,
        mock_stock_repo,
        mock_order_repo,
        mock_stock_info_repo,
        mock_dividend_repo,
        sample_stocks,
        sample_orders,
        sample_stock_info,
    ):
        """Test calculating overall portfolio performance."""
        # Setup
        mock_stock_repo.get_all.return_value = sample_stocks

        # Configure order_repo to return appropriate orders for each stock
        mock_order_repo.get_orders_for_stock.side_effect = lambda stock_id: sample_orders.get(
            stock_id, []
        )

        # Configure stock_info_repo to return appropriate info for each stock
        mock_stock_info_repo.get_by_stock_id.side_effect = lambda stock_id: sample_stock_info.get(
            stock_id
        )

        # Configure dividend_repo to return different amounts for each stock
        mock_dividend_repo.calculate_dividends_received.side_effect = lambda stock_id: {
            1: 75.0,
            2: 80.0,
            3: 0.0,
        }.get(stock_id, 0.0)

        # Test
        result = portfolio_service.calculate_portfolio_performance()

        # Assertions
        assert isinstance(result, PortfolioPerformance)
        assert len(result.stocks) == 3

        # Calculate expected totals
        expected_total_cost = (
            (10 * 150.0 + 5.0)
            + (5 * 170.0 + 5.0)  # AAPL
            + (8 * 280.0 + 5.0)  # MSFT
            + (4 * 2200.0 + 5.0)  # GOOGL
        )
        expected_current_value = (
            (10 + 5) * 190.0  # AAPL
            + 8 * 330.0  # MSFT
            + 4 * 2800.0  # GOOGL
        )
        expected_capital_gain = expected_current_value - expected_total_cost
        expected_dividends = 75.0 + 80.0 + 0.0
        expected_total_return = expected_capital_gain + expected_dividends

        # Check portfolio totals
        assert result.total_cost == pytest.approx(expected_total_cost)
        assert result.current_value == pytest.approx(expected_current_value)
        assert result.capital_gain == pytest.approx(expected_capital_gain)
        assert result.dividends_received == pytest.approx(expected_dividends)
        assert result.total_return == pytest.approx(expected_total_return)

        # Calculate expected percentage returns
        expected_capital_gain_pct = expected_capital_gain / expected_total_cost * 100
        expected_total_return_pct = expected_total_return / expected_total_cost * 100

        assert result.capital_gain_percentage == pytest.approx(expected_capital_gain_pct)
        assert result.total_return_percentage == pytest.approx(expected_total_return_pct)

        # Check individual stock performances
        for stock_perf in result.stocks:
            assert isinstance(stock_perf, StockPerformance)
            if stock_perf.stock_id == 1:  # AAPL
                assert stock_perf.ticker == "AAPL"
                assert stock_perf.total_shares == 15  # 10 + 5
                assert stock_perf.total_cost == pytest.approx(
                    (10 * 150.0 + 5.0) + (5 * 170.0 + 5.0)
                )
                assert stock_perf.current_value == pytest.approx(15 * 190.0)
                assert stock_perf.dividends_received == pytest.approx(75.0)

    def test_calculate_portfolio_performance_empty(self, portfolio_service, mock_stock_repo):
        """Test calculating portfolio performance with no stocks."""
        # Setup
        mock_stock_repo.get_all.return_value = []

        # Test
        result = portfolio_service.calculate_portfolio_performance()

        # Assertions
        assert isinstance(result, PortfolioPerformance)
        assert len(result.stocks) == 0
        assert result.total_cost == 0.0
        assert result.current_value == 0.0
        assert result.capital_gain == 0.0
        assert result.capital_gain_percentage == 0.0
        assert result.dividends_received == 0.0
        assert result.total_return == 0.0
        assert result.total_return_percentage == 0.0

    def test_calculate_portfolio_performance_missing_data(
        self,
        portfolio_service,
        mock_stock_repo,
        mock_order_repo,
        mock_stock_info_repo,
        sample_stocks,
    ):
        """Test portfolio calculation with missing order or stock info data."""
        # Setup
        mock_stock_repo.get_all.return_value = sample_stocks

        # Return no orders for first stock, normal orders for others
        def mock_get_orders(stock_id):
            if stock_id == 1:
                return []  # No orders for AAPL
            elif stock_id == 2:
                return [
                    StockOrder(
                        id=3,
                        stock_id=2,
                        purchase_datetime=datetime(2023, 2, 10, 9, 15),
                        quantity=8,
                        price_paid=280.0,
                        fee=5.0,
                    )
                ]
            else:
                return [
                    StockOrder(
                        id=4,
                        stock_id=3,
                        purchase_datetime=datetime(2023, 3, 5, 11, 0),
                        quantity=4,
                        price_paid=2200.0,
                        fee=5.0,
                    )
                ]

        mock_order_repo.get_orders_for_stock.side_effect = mock_get_orders

        # Return no stock info for second stock, normal info for others
        def mock_get_stock_info(stock_id):
            if stock_id == 1:
                return StockInfo(
                    stock_id=1,
                    last_updated_datetime=datetime(2023, 12, 1, 16, 0),
                    current_price=190.0,
                    market_cap=3000000000000,
                    pe_ratio=30.5,
                    dividend_yield=0.005,
                )
            elif stock_id == 2:
                return None  # No stock info for MSFT
            else:
                return StockInfo(
                    stock_id=3,
                    last_updated_datetime=datetime(2023, 12, 1, 16, 0),
                    current_price=2800.0,
                    market_cap=1800000000000,
                    pe_ratio=25.8,
                    dividend_yield=0.0,
                )

        mock_stock_info_repo.get_by_stock_id.side_effect = mock_get_stock_info

        # Test
        result = portfolio_service.calculate_portfolio_performance()

        # Assertions
        assert isinstance(result, PortfolioPerformance)
        assert len(result.stocks) == 1  # Only GOOGL has both orders and stock info
        assert result.stocks[0].ticker == "GOOGL"  # Verify it's the right stock

    def test_calculate_stock_performance(
        self, portfolio_service, mock_dividend_repo, sample_stocks, sample_orders, sample_stock_info
    ):
        """Test calculating performance for a single stock."""
        # Setup
        stock = sample_stocks[0]  # AAPL
        orders = sample_orders[1]  # AAPL orders
        stock_info = sample_stock_info[1]  # AAPL stock info

        # Configure dividend repo to return a specific amount
        mock_dividend_repo.calculate_dividends_received.return_value = 75.0

        # Test
        result = portfolio_service._calculate_stock_performance(stock, orders, stock_info)

        # Assertions
        assert isinstance(result, StockPerformance)
        assert result.stock_id == 1
        assert result.ticker == "AAPL"
        assert result.exchange == "NASDAQ"
        assert result.name == "Apple Inc."

        # Calculate expected values
        expected_total_shares = 10 + 5
        expected_total_cost = (10 * 150.0 + 5.0) + (5 * 170.0 + 5.0)
        expected_current_value = 15 * 190.0
        expected_capital_gain = expected_current_value - expected_total_cost
        expected_capital_gain_pct = expected_capital_gain / expected_total_cost * 100
        expected_dividends = 75.0
        expected_total_return = expected_capital_gain + expected_dividends
        expected_total_return_pct = expected_total_return / expected_total_cost * 100

        # Check calculated values
        assert result.total_shares == expected_total_shares
        assert result.total_cost == pytest.approx(expected_total_cost)
        assert result.current_value == pytest.approx(expected_current_value)
        assert result.capital_gain == pytest.approx(expected_capital_gain)
        assert result.capital_gain_percentage == pytest.approx(expected_capital_gain_pct)
        assert result.dividends_received == pytest.approx(expected_dividends)
        assert result.total_return == pytest.approx(expected_total_return)
        assert result.total_return_percentage == pytest.approx(expected_total_return_pct)

        # Verify dividend repo was called correctly
        mock_dividend_repo.calculate_dividends_received.assert_called_once_with(1)

    def test_calculate_stock_performance_zero_cost(
        self, portfolio_service, mock_dividend_repo, sample_stocks
    ):
        """Test calculating performance when cost basis is zero (edge case)."""
        # Setup
        stock = sample_stocks[0]  # AAPL

        # Create an order with zero cost (unrealistic but tests the math)
        orders = [
            StockOrder(
                id=1,
                stock_id=1,
                purchase_datetime=datetime(2023, 1, 15, 10, 30),
                quantity=10,
                price_paid=0.0,
                fee=0.0,
            ),
        ]

        stock_info = StockInfo(
            stock_id=1,
            last_updated_datetime=datetime(2023, 12, 1, 16, 0),
            current_price=190.0,
            market_cap=3000000000000,
            pe_ratio=30.5,
            dividend_yield=0.005,
        )

        mock_dividend_repo.calculate_dividends_received.return_value = 75.0

        # Test
        result = portfolio_service._calculate_stock_performance(stock, orders, stock_info)

        # Assertions - percentages should be 0.0 when cost is zero
        assert result.total_cost == 0.0
        assert result.current_value == pytest.approx(10 * 190.0)
        assert result.capital_gain_percentage == 0.0
        assert result.total_return_percentage == 0.0

    def test_calculate_dividend_report(
        self, portfolio_service, mock_stock_repo, mock_dividend_repo, sample_stocks
    ):
        """Test calculating the dividend report."""
        # Setup
        mock_stock_repo.get_all.return_value = sample_stocks

        # Create sample dividends for each stock
        dividends = {
            1: [  # AAPL dividends
                Dividend(
                    id=1,
                    stock_id=1,
                    ex_date=date(2023, 2, 9),
                    payment_date=date(2023, 2, 24),
                    amount=0.23,
                    currency="USD",
                ),
                Dividend(
                    id=2,
                    stock_id=1,
                    ex_date=date(2023, 5, 11),
                    payment_date=date(2023, 5, 26),
                    amount=0.24,
                    currency="USD",
                ),
                Dividend(
                    id=3,
                    stock_id=1,
                    ex_date=date(2023, 8, 10),
                    payment_date=date(2023, 8, 25),
                    amount=0.24,
                    currency="USD",
                ),
                Dividend(
                    id=4,
                    stock_id=1,
                    ex_date=date(2023, 11, 9),
                    payment_date=date(2023, 11, 24),
                    amount=0.25,
                    currency="USD",
                ),
            ],
            2: [  # MSFT dividends
                Dividend(
                    id=5,
                    stock_id=2,
                    ex_date=date(2023, 2, 15),
                    payment_date=date(2023, 3, 9),
                    amount=0.68,
                    currency="USD",
                ),
                Dividend(
                    id=6,
                    stock_id=2,
                    ex_date=date(2023, 5, 17),
                    payment_date=date(2023, 6, 8),
                    amount=0.68,
                    currency="USD",
                ),
                Dividend(
                    id=7,
                    stock_id=2,
                    ex_date=date(2023, 8, 16),
                    payment_date=date(2023, 9, 14),
                    amount=0.75,
                    currency="USD",
                ),
                Dividend(
                    id=8,
                    stock_id=2,
                    ex_date=date(2023, 11, 15),
                    payment_date=date(2023, 12, 14),
                    amount=0.75,
                    currency="USD",
                ),
            ],
            3: [],  # GOOGL has no dividends
        }

        # Configure dividend_repo to return appropriate dividends for each stock
        mock_dividend_repo.get_dividends_for_stock.side_effect = lambda stock_id: dividends.get(
            stock_id, []
        )

        # Test
        result = portfolio_service.calculate_dividend_report()

        # Assertions
        assert len(result) == 2  # Only AAPL and MSFT have dividends

        # Check each entry in the report
        for entry in result:
            stock = entry["stock"]
            if stock.ticker == "AAPL":
                assert entry["total_amount"] == 0.23 + 0.24 + 0.24 + 0.25
                assert entry["last_ex_date"] == date(2023, 11, 9)
                assert entry["dividends_count"] == 4
            elif stock.ticker == "MSFT":
                assert entry["total_amount"] == 0.68 + 0.68 + 0.75 + 0.75
                assert entry["last_ex_date"] == date(2023, 11, 15)
                assert entry["dividends_count"] == 4

    def test_calculate_dividend_report_empty(
        self, portfolio_service, mock_stock_repo, mock_dividend_repo
    ):
        """Test dividend report with no stocks."""
        # Setup
        mock_stock_repo.get_all.return_value = []

        # Test
        result = portfolio_service.calculate_dividend_report()

        # Assertions
        assert result == []

    def test_calculate_dividend_report_no_dividends(
        self, portfolio_service, mock_stock_repo, mock_dividend_repo, sample_stocks
    ):
        """Test dividend report when no stocks have dividends."""
        # Setup
        mock_stock_repo.get_all.return_value = sample_stocks
        mock_dividend_repo.get_dividends_for_stock.return_value = []

        # Test
        result = portfolio_service.calculate_dividend_report()

        # Assertions
        assert result == []
