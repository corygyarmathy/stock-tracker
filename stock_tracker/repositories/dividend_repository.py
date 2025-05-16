from datetime import date
import logging
from sqlite3 import Cursor, Row
from stock_tracker.db import Database
from stock_tracker.models import Dividend
from stock_tracker.utils.model_utils import ModelFactory

logger: logging.Logger = logging.getLogger(__name__)


class DividendRepository:
    def __init__(self, db: Database):
        self.db: Database = db

    def insert(self, dividend: Dividend) -> int:
        """Insert a new dividend record into the database."""
        cursor: Cursor = self.db.execute(
            """
            INSERT INTO dividend_history (stock_id, ex_date, payment_date, amount, currency)
            VALUES (:stock_id, :ex_date, :payment_date, :amount, :currency)
            """,
            {
                "stock_id": dividend.stock_id,
                "ex_date": dividend.ex_date,
                "payment_date": dividend.payment_date,
                "amount": dividend.amount,
                "currency": dividend.currency,
            },
        )

        dividend.id = cursor.lastrowid
        if dividend.id:
            logger.debug(
                f"Inserted dividend for stock ID {dividend.stock_id} on {dividend.ex_date}"
            )
            return dividend.id
        else:
            logger.error(f"Failed to obtain id of dividend after inserting into db.")
            raise ValueError(f"Failed to obtain id of dividend after inserting into db.")

    def get_dividends_for_stock(self, stock_id: int) -> list[Dividend]:
        """Get all dividends for a specific stock."""
        rows: list[Row] = self.db.query_all(
            """
            SELECT * FROM dividend_history
            WHERE stock_id = ?
            ORDER BY ex_date ASC
            """,
            (stock_id,),
        )
        logger.debug(f"Found {len(rows)} dividends for stock ID {stock_id}")
        return ModelFactory.create_list_from_rows(Dividend, rows)

    def get_dividends_in_date_range(
        self, stock_id: int, start_date: date, end_date: date
    ) -> list[Dividend]:
        """Get dividends for a stock within a specific date range."""
        rows: list[Row] = self.db.query_all(
            """
            SELECT * FROM dividend_history
            WHERE stock_id = ? AND ex_date BETWEEN ? AND ?
            ORDER BY ex_date ASC
            """,
            (stock_id, start_date, end_date),
        )
        logger.debug(
            f"Found {len(rows)} dividends for stock ID {stock_id} between {start_date} and {end_date}"
        )
        return ModelFactory.create_list_from_rows(Dividend, rows)

    def get_dividend_by_ex_date(self, stock_id: int, ex_date: date) -> Dividend | None:
        """Get a specific dividend by its ex-date."""
        row: Row | None = self.db.query_one(
            """
            SELECT * FROM dividend_history
            WHERE stock_id = ? AND ex_date = ?
            """,
            (stock_id, ex_date),
        )
        if row:
            return ModelFactory.create_from_row(Dividend, row)
        return None

    def delete_dividend(self, dividend_id: int) -> bool:
        """Delete a dividend by ID."""
        try:
            _ = self.db.execute(
                "DELETE FROM dividend_history WHERE id = ?",
                (dividend_id,),
            )
            logger.info(f"Deleted dividend with ID {dividend_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting dividend with ID {dividend_id}: {e}")
            return False

    def calculate_dividends_received(
        self, stock_id: int, start_date: date | None = None, end_date: date | None = None
    ) -> float:
        """
        Calculate total dividends received for a stock in a given date range.

        Args:
            stock_id: ID of the stock
            start_date: Start of date range (optional)
            end_date: End of date range (optional)

        Returns:
            Total amount of dividends received
        """
        # Implement proper SQL query with date restrictions if provided
        query_parts: list[str] = [
            "SELECT SUM(amount) as total FROM dividend_history WHERE stock_id = ?"
        ]
        params: list[int | date] = [stock_id]

        if start_date:
            query_parts.append("AND ex_date >= ?")
            params.append(start_date)

        if end_date:
            query_parts.append("AND ex_date <= ?")
            params.append(end_date)

        query: str = " ".join(query_parts)
        result: Row | None = self.db.query_one(query, params)

        # If no dividends are found, return 0
        if not result or result["total"] is None:
            return 0.0

        return float(result["total"])
