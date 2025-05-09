from datetime import datetime
from sqlite3 import Row
from stock_tracker.db import Database
from stock_tracker.models import StockInfo


class StockInfoRepository:
    def __init__(self, db: Database):
        self.db: Database = db

    def insert(self, stock_info: StockInfo) -> None:
        _ = self.db.execute(
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
            "SELECT * FROM stock_info WHERE stock_id = ?",
            (stock_id,),
        )
        if row:
            return StockInfo(
                stock_id=row["stock_id"],
                # Assumes storing purchase_datetime as an ISO8601 string ("%Y-%m-%d %H:%M:%S")
                last_updated=datetime.strptime(row["last_updated"], "%Y-%m-%d %H:%M:%S"),
                current_price=row["current_price"],
                market_cap=row["market_cap"],
                pe_ratio=row["pe_ratio"],
                dividend_yield=row["dividend_yield"],
            )
        return None
