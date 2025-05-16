import logging
from sqlite3 import Row
from stock_tracker.db import Database
from stock_tracker.models import Stock
from stock_tracker.utils.model_utils import ModelFactory


logger: logging.Logger = logging.getLogger(__name__)


class StockRepository:
    def __init__(self, db: Database):
        self.db: Database = db

    def insert(self, stock: Stock) -> int:
        cursor = self.db.execute(
            """
            INSERT INTO stocks (ticker, exchange, currency, name, yfinance_ticker)
            VALUES (:ticker, :exchange, :currency, :name, :yfinance_ticker)
            """,
            {
                "ticker": stock.ticker,
                "exchange": stock.exchange,
                "currency": stock.currency,
                "name": stock.name,
                "yfinance_ticker": stock.yfinance_ticker,
            },
        )
        stock.id = cursor.lastrowid
        if stock.id:
            return stock.id
        else:
            raise ValueError(f"Failed to obtain id of stock after inserting into db.")

    def get_by_ticker_exchange(self, ticker: str, exchange: str) -> Stock | None:
        row: Row | None = self.db.query_one(
            """
            SELECT *
            FROM stocks
            WHERE ticker = ? AND exchange = ?
            """,
            (ticker, exchange),
        )
        if not row:
            return None
        return ModelFactory.create_from_row(Stock, row)

    def get_by_id(self, stock_id: int) -> Stock | None:
        row: Row | None = self.db.query_one(
            "SELECT * FROM stocks WHERE id = ?",
            (stock_id,),
        )
        if not row:
            return None
        return ModelFactory.create_from_row(Stock, row)

    def get_by_ids(self, stock_ids: list[int]) -> dict[int, Stock]:
        """
        Retrieve multiple stocks by their IDs in a single query.

        Args:
            stock_ids: List of stock IDs to retrieve

        Returns:
            Dictionary mapping stock IDs to Stock objects
        """
        # Convert list to comma-separated string for SQL IN clause
        id_str = ",".join("?" for _ in stock_ids)

        rows = self.db.query_all(f"SELECT * FROM stocks WHERE id IN ({id_str})", stock_ids)

        # Create a dictionary mapping ID to Stock object
        return {row["id"]: ModelFactory.create_from_row(Stock, row) for row in rows}

    def get_all(self) -> list[Stock]:
        """
        Retrieve all stocks from the database.

        Returns:
            List of all Stock objects
        """
        rows: list[Row] = self.db.query_all("SELECT * FROM stocks")
        return ModelFactory.create_list_from_rows(Stock, rows)

    def upsert(self, stock: Stock) -> int:
        """
        Inserts a stock if it doesn't exist, or fetches its ID if it already exists.
        Useful when importing from external sources like yfinance.
        """
        existing: Stock | None = self.get_by_ticker_exchange(stock.ticker, stock.exchange)
        if existing:
            stock.id = existing.id
            if stock.id:
                return stock.id
        return self.insert(stock)
