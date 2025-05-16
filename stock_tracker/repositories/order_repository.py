import logging
from sqlite3 import Cursor, Row
from stock_tracker.db import Database
from stock_tracker.models import StockOrder
from stock_tracker.utils.model_utils import ModelFactory

logger: logging.Logger = logging.getLogger(__name__)


class OrderRepository:
    def __init__(self, db: Database) -> None:
        self.db: Database = db

    def insert(self, order: StockOrder) -> int:
        cursor: Cursor = self.db.execute(
            """
            INSERT INTO stock_orders (stock_id, purchase_datetime, quantity, price_paid, fee, note)
            VALUES (:stock_id, :purchase_datetime, :quantity, :price_paid, :fee, :note)
            """,
            {
                "stock_id": order.stock_id,
                "purchase_datetime": order.purchase_datetime,
                "quantity": order.quantity,
                "price_paid": order.price_paid,
                "fee": order.fee,
                "note": order.note,
            },
        )
        order.id = cursor.lastrowid
        if order.id:
            return order.id
        else:
            raise ValueError(f"Failed to obtain id of stock after inserting into db.")

    def get_orders_for_stock(self, stock_id: int) -> list[StockOrder]:
        rows: list[Row] = self.db.query_all(
            """
            SELECT *
            FROM stock_orders
            WHERE stock_id = ?
            """,
            (stock_id,),
        )
        return ModelFactory.create_list_from_rows(StockOrder, rows)

    def calculate_capital_gains(self, stock_id: int) -> float:
        # Calculate capital gains for all orders related to stock_id
        orders: list[StockOrder] = self.get_orders_for_stock(stock_id)
        total_gains: float = 0.0
        for order in orders:
            # TODO: Example capital gain calculation; customize as per your logic
            total_gains += order.quantity * order.price_paid  # Simplified example
        return total_gains
