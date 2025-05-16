from datetime import date, datetime

import pytest

from stock_tracker.config import AppConfig
from stock_tracker.models import CorporateAction, FxRate, Stock, StockInfo, StockOrder
from stock_tracker.repositories.corporate_actions_repository import CorporateActionRepository
from stock_tracker.repositories.fx_rate_repository import FxRateRepository
from stock_tracker.repositories.order_repository import OrderRepository
from stock_tracker.repositories.stock_info_repository import StockInfoRepository
from stock_tracker.repositories.stock_repository import StockRepository


@pytest.fixture()
def stock_obj(app_config: AppConfig, stock_repo: StockRepository) -> Stock:
    stock: Stock = Stock(
        id=None,
        ticker="MSFT",
        exchange="NASDAQ",
        currency="USD",
        name="Microsoft Corp",
        yfinance_ticker="MSFT",
    )
    stock.id = stock_repo.insert(stock)  # Store stock ID
    return stock


@pytest.fixture()
def stock_obj_2(app_config: AppConfig, stock_repo: StockRepository) -> Stock:
    stock: Stock = Stock(
        id=None,
        ticker="AAPL",
        exchange="NASDAQ",
        currency="USD",
        name="Apple Corp",
        yfinance_ticker="AAPL",
    )
    stock.id = stock_repo.insert(stock)  # Store stock ID
    return stock


class TestStockRepository:
    def test_insert_and_get(self, app_config: AppConfig, stock_repo: StockRepository):
        stock: Stock = Stock(
            id=None,
            ticker="AAPL",
            exchange="NASDAQ",
            currency="USD",
            name="Apple Inc.",
            yfinance_ticker="AAPL",
        )
        stock_id: int = stock_repo.insert(stock)
        assert isinstance(stock_id, int)
        assert stock.id == stock_id

        # Retrieve by id
        fetched: Stock | None = stock_repo.get_by_id(stock_id)
        assert fetched == stock

        # Retrieve by ticker/exchange
        fetched2: Stock | None = stock_repo.get_by_ticker_exchange("AAPL", "NASDAQ")
        assert fetched2 == stock

    def test_upsert_new_and_existing(
        self,
        app_config: AppConfig,
        stock_repo: StockRepository,
        stock_obj: Stock,
        stock_obj_2: Stock,
    ):
        first_id: int = stock_repo.upsert(stock_obj)
        assert first_id == stock_obj.id

        second_id: int = stock_repo.upsert(stock_obj)
        assert second_id == first_id
        assert stock_obj.id == first_id


class TestOrderRepository:
    def test_insert_and_get_orders(
        self, app_config: AppConfig, order_repo: OrderRepository, stock_obj: Stock
    ):
        if stock_obj.id is None:
            raise ValueError("stock_id has not been properly initialised.")
        order: StockOrder = StockOrder(
            id=None,
            stock_id=stock_obj.id,
            purchase_datetime=datetime(2025, 1, 1, 9, 30),
            quantity=5,
            price_paid=200.0,
            fee=1.0,
            note="Test order",
        )
        order_id: int = order_repo.insert(order)
        assert isinstance(order_id, int)
        assert order.id == order_id

        orders: list[StockOrder] = order_repo.get_orders_for_stock(stock_obj.id)
        assert len(orders) == 1
        assert orders[0] == order

    def test_calculate_capital_gains(
        self, app_config: AppConfig, order_repo: OrderRepository, stock_obj: Stock
    ):
        if stock_obj.id is None:
            raise ValueError("stock_id has not been properly initialised.")

        # Insert two orders
        orders: list[StockOrder] = [
            StockOrder(
                id=None,
                stock_id=stock_obj.id,
                purchase_datetime=datetime(2025, 1, 1, 9, 30),
                quantity=2,
                price_paid=100.0,
            ),
            StockOrder(
                id=None,
                stock_id=stock_obj.id,
                purchase_datetime=datetime(2025, 1, 2, 9, 30),
                quantity=3,
                price_paid=150.0,
            ),
        ]
        for o in orders:
            _ = order_repo.insert(o)
        gains: float = order_repo.calculate_capital_gains(stock_obj.id)
        # Expected: 2*100 + 3*150 = 200 + 450 = 650
        assert gains == pytest.approx(650.0)


class TestStockInfoRepository:
    def test_insert_and_get_orders(
        self, app_config: AppConfig, stock_info_repo: StockInfoRepository, stock_obj: Stock
    ) -> None:
        if stock_obj.id is None:
            raise ValueError("stock_id has not been properly initialised.")
        stock_info: StockInfo = StockInfo(
            stock_id=stock_obj.id,
            last_updated_datetime=datetime(2025, 1, 1, 9, 30),
            current_price=200.0,
            market_cap=5000.0,
            pe_ratio=35.0,
            dividend_yield=0.35,
        )
        assert stock_info.stock_id == stock_obj.id

        stock_info_repo.insert(stock_info)

        assert stock_info == stock_info_repo.get_by_stock_id(stock_info.stock_id)

    def test_stock_info_upsert(
        self, app_config: AppConfig, stock_info_repo: StockInfoRepository, stock_obj: Stock
    ) -> None:
        if stock_obj.id is None:
            raise ValueError("stock_id has not been properly initialised.")

        # Create initial stock info
        initial_stock_info: StockInfo = StockInfo(
            stock_id=stock_obj.id,
            last_updated_datetime=datetime(2025, 1, 1, 9, 30),
            current_price=200.0,
            market_cap=5000.0,
            pe_ratio=35.0,
            dividend_yield=0.35,
        )

        # Insert initial record
        stock_info_repo.insert(initial_stock_info)

        # Verify it was inserted
        fetched_info = stock_info_repo.get_by_stock_id(stock_obj.id)
        assert fetched_info is not None
        assert fetched_info.current_price == 200.0

        # Create updated stock info
        updated_stock_info: StockInfo = StockInfo(
            stock_id=stock_obj.id,
            last_updated_datetime=datetime(2025, 1, 2, 10, 0),
            current_price=210.0,  # Changed price
            market_cap=5200.0,  # Changed market cap
            pe_ratio=36.0,  # Changed PE ratio
            dividend_yield=0.36,  # Changed dividend yield
        )

        # Use upsert to update
        stock_info_repo.upsert(updated_stock_info)

        # Verify it was updated
        fetched_updated_info = stock_info_repo.get_by_stock_id(stock_obj.id)
        assert fetched_updated_info is not None
        assert fetched_updated_info.current_price == 210.0
        assert fetched_updated_info.market_cap == 5200.0
        assert fetched_updated_info.pe_ratio == 36.0
        assert fetched_updated_info.dividend_yield == 0.36
        assert fetched_updated_info.last_updated_datetime == datetime(2025, 1, 2, 10, 0)


class TestCorporateActionRepository:
    def test_insert_and_get(
        self, app_config: AppConfig, corp_action_repo: CorporateActionRepository, stock_obj: Stock
    ) -> None:
        if stock_obj.id is None:
            raise ValueError("stock_id has not been properly initialised.")
        corp_action: CorporateAction = CorporateAction(
            id=None,
            stock_id=stock_obj.id,
            action_type="split",
            action_date=date(2025, 1, 1),
            ratio=2.0,
            target_stock_id=stock_obj.id,
        )

        corp_action_id: int = corp_action_repo.insert(corp_action)
        assert isinstance(corp_action_id, int)
        assert corp_action.id == corp_action_id

        corp_actions: list[CorporateAction] = corp_action_repo.get_by_stock_id(stock_obj.id)
        assert len(corp_actions) == 1
        assert corp_actions[0] == corp_action


class TestFxRateRepository:
    def test_insert_and_get_orders(
        self, app_config: AppConfig, fx_rate_repo: FxRateRepository
    ) -> None:
        fx_rate: FxRate = FxRate(
            base_currency="AUD",
            target_currency="USD",
            date=date(2025, 1, 1),
            rate=0.6411,
        )

        fx_rate_repo.insert(fx_rate)

        assert fx_rate == fx_rate_repo.get_rate(
            fx_rate.base_currency, fx_rate.target_currency, fx_rate.date
        )
