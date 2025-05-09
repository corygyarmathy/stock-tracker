from sqlite3 import Cursor, Row
from stock_tracker.db import Database
from stock_tracker.models import StockInfo


class StockInfoRepository:
    def __init__(self, db: Database):
        self.db: Database = db

    def insert(self, stock_info: StockInfo) -> int:
        cursor: Cursor = self.db.execute(
            """
            INSERT INTO stock_info (stock_id, last_updated, current_price, market_cap, pe_ratio, dividend_yield)
            VALUES (:stock_id, :last_updated, :current_price, :market_cap, :pe_ratio, :dividend_yield)
            """,
            {
                "stock_id": stock_info.stock_id,
                "last_updated": stock_info.last_updated,
                "current_price": stock_info.current_price,
                "market_cap": stock_info.market_cap,
                "pe_ratio": stock_info.pe_ratio,
                "dividend_yield": stock_info.dividend_yield,
            },
        )

    def get_by_stock_id(self, stock_id: int) -> StockInfo | None:
        row: Row | None = self.db.query_one(
            "SELECT id, stock_id, last_updated, current_price, market_cap, pe_ratio, dividend_yield FROM stock_info WHERE stock_id = ?",
            (stock_id,),
        )
        return StockInfo(**row) if row else None
