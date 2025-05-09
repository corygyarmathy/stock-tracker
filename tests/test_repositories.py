from datetime import datetime

import pytest

from stock_tracker.config import AppConfig
from stock_tracker.models import Stock, StockInfo, StockOrder
from stock_tracker.repositories.order_repository import OrderRepository
from stock_tracker.repositories.stock_info_repository import StockInfoRepository
from stock_tracker.repositories.stock_repository import StockRepository


@pytest.fixture()
def stock_obj(app_config: AppConfig, stock_repo: StockRepository) -> Stock:
    # Initialise stock before each test
    stock: Stock = Stock(
        id=None, ticker="MSFT", exchange="NASDAQ", currency="USD", name="Microsoft Corp"
    )
    stock.id = stock_repo.insert(stock)  # Store stock ID
    return stock


class TestStockRepository:
    def test_insert_and_get(self, app_config: AppConfig, stock_repo: StockRepository):
        stock: Stock = Stock(
            id=None, ticker="AAPL", exchange="NASDAQ", currency="USD", name="Apple Inc."
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

    def test_upsert_new_and_existing(self, app_config: AppConfig, stock_repo: StockRepository):
        stock: Stock = Stock(
            id=None, ticker="GOOG", exchange="NASDAQ", currency="USD", name="Google LLC"
        )
        first_id: int = stock_repo.upsert(stock)
        assert first_id == stock.id

        stock2: Stock = Stock(
            id=None, ticker="GOOG", exchange="NASDAQ", currency="USD", name="Google LLC"
        )
        second_id: int = stock_repo.upsert(stock2)
        assert second_id == first_id
        assert stock2.id == first_id


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
            last_updated=datetime(2025, 1, 1, 9, 30),
            current_price=200.0,
            market_cap=5000.0,
            pe_ratio=35.0,
            dividend_yield=0.35,
        )
        assert stock_info.stock_id == stock_obj.id

        stock_info_repo.insert(stock_info)

        assert stock_info == stock_info_repo.get_by_stock_id(stock_info.stock_id)
