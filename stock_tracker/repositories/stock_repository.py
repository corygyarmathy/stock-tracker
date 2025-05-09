from stock_tracker.db import Database
from stock_tracker.models import Stock


class StockRepository:
    def __init__(self, db: Database):
        self.db = db

    def insert(self, stock: Stock) -> int:
        cursor = self.db.execute(
            """
            INSERT INTO stocks (ticker, exchange, currency, name)
            VALUES (:ticker, :exchange, :currency, :name)
            """,
            {
                "ticker": stock.ticker,
                "exchange": stock.exchange,
                "currency": stock.currency,
                "name": stock.name,
            },
        )
        stock.id = cursor.lastrowid
        if stock.id:
            return stock.id
        else:
            raise ValueError(f"Failed to obtain id of stock after inserting into db.")

    def get_by_ticker_exchange(self, ticker: str, exchange: str) -> Stock | None:
        row = self.db.query_one(
            """
            SELECT id, ticker, exchange, currency, name
            FROM stocks
            WHERE ticker = ? AND exchange = ?
            """,
            (ticker, exchange),
        )
        return Stock(**row) if row else None

    def get_by_id(self, stock_id: int) -> Stock | None:
        row = self.db.query_one(
            "SELECT id, ticker, exchange, currency, name FROM stocks WHERE id = ?",
            (stock_id,),
        )
        return Stock(**row) if row else None

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
