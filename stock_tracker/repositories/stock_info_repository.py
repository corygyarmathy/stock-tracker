import logging
from sqlite3 import Row
from stock_tracker.db import Database
from stock_tracker.models import StockInfo
from stock_tracker.utils.model_utils import ModelFactory

logger: logging.Logger = logging.getLogger(__name__)


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

    def update(self, stock_info: StockInfo) -> None:
        """Update an existing StockInfo record."""
        logger.debug(f"Performing an update on StockInfo record, ID {stock_info.stock_id}")
        _ = self.db.execute(
            """
            UPDATE stock_info
            SET last_updated = :last_updated,
                current_price = :current_price,
                market_cap = :market_cap,
                pe_ratio = :pe_ratio,
                dividend_yield = :dividend_yield
            WHERE stock_id = :stock_id
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

    def upsert(self, stock_info: StockInfo) -> None:
        """
        Insert a stock_info if it doesn't exist, or update it if it already exists.
        Uses the stock_id as the unique identifier.
        """
        logger.debug(f"Checking if StockInfo w/ id {stock_info.stock_id} already exists in db.")
        existing: StockInfo | None = self.get_by_stock_id(stock_info.stock_id)
        if existing:
            logger.debug(f"StockInfo already exists in db, updating.")
            self.update(stock_info)
        else:
            logger.debug(f"StockInfo doesn't exists in db, inserting.")
            self.insert(stock_info)

    def get_by_stock_id(self, stock_id: int) -> StockInfo | None:
        logger.debug(f"Getting StockInfo by stock id {stock_id}")
        row: Row | None = self.db.query_one(
            "SELECT * FROM stock_info WHERE stock_id = ?",
            (stock_id,),
        )
        if row:
            return ModelFactory.create_from_row(StockInfo, row)
        return None
