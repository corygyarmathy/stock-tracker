from collections.abc import Sequence
import sqlite3
import logging
import traceback


from typing import Any, Self
from collections.abc import Mapping


class Database:
    # Example usage:
    # with Database("stock_orders.db") as db:
    #   db.execute("INSERT INTO tickers (ticker, exchange) VALUES (?, ?)", ("IVV", "ASX"))
    #   No need to call db.commit() — it will auto-commit if no exception occurs
    #   raise ValueError("Something went wrong!")  # <- Rolls back instead of committing
    def __init__(self, db_path: str) -> None:
        self.conn: sqlite3.Connection = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row  # Allows dict-style access
        self.cursor: sqlite3.Cursor = self.conn.cursor()
        self.logger: logging.Logger = logging.getLogger("db")

    def execute(
        self,
        query: str,
        params: Sequence[Any] | Mapping[str, Any] | None = None,
    ) -> sqlite3.Cursor:
        """
        Executes a single SQL query.
        Supports both positional (?) and named (:param) placeholders.
        Includes error handling, transaction support, and logging.
        """
        if params is None:
            params = ()

        self.logger.debug(f"Preparing SQL execution:\n{query}")
        self.logger.debug(f"Parameters: {params}")

        if "?" in query and isinstance(params, Mapping):
            raise ValueError("Positional placeholders (?) used with named parameters.")
        if ":" in query and isinstance(params, (list, tuple)):
            raise ValueError("Named placeholders (:) used with positional parameters.")

        try:
            _ = self.conn.execute("BEGIN")
            result = self.cursor.execute(query, params)
            self.commit()
            self.logger.info(
                f"Query executed successfully. Rows affected: {self.cursor.rowcount}"
            )
            return result
        except sqlite3.Error as e:
            self.conn.rollback()
            self.logger.error("Database error during execute:")
            self.logger.error(traceback.format_exc())
            raise
        except Exception as e:
            self.conn.rollback()
            self.logger.error("Unexpected error during execute:")
            self.logger.error(traceback.format_exc())
            raise

    def executemany(
        self,
        query: str,
        param_list: Sequence[Sequence[Any] | Sequence[Mapping[str, Any]]],
    ) -> sqlite3.Cursor:
        """
        Executes a SQL query for multiple sets of parameters.
        Supports both positional (?) and named (:param) styles.
        Includes error handling, transaction support, and logging.
        """
        self.logger.debug(f"Preparing bulk execution of SQL:\n{query}")
        self.logger.debug(f"Number of entries: {len(param_list)}")

        if not param_list:
            self.logger.warning("executemany called with an empty parameter list.")
            return (
                self.cursor
            )  # Or perhaps raise an exception depending on desired behavior

        first_params = param_list[0] if param_list else None
        using_named_placeholders: bool = ":" in query
        using_positional_placeholders: bool = "?" in query

        # Confirm positional and named-placeholders are not being inter-mixed
        if using_positional_placeholders:
            if isinstance(first_params, Mapping):
                raise ValueError(
                    "Positional placeholders (?) used with named parameters in executemany."
                )
            for params in param_list:
                if not isinstance(params, (list, tuple)):
                    raise ValueError(
                        "Positional placeholders (?) require a sequence of parameters for each execution."
                    )
        elif using_named_placeholders:
            if not isinstance(first_params, Mapping):
                raise ValueError(
                    "Named placeholders (:) used with positional parameters in executemany."
                )
            for params in param_list:
                if not isinstance(params, Mapping):
                    raise ValueError(
                        "Named placeholders (:) require a mapping of parameters for each execution."
                    )
        elif first_params is not None:
            self.logger.warning(
                "Query does not contain placeholders, parameter list will be ignored."
            )

        # Preview the first few entries for logging
        preview = list(param_list)[:3]
        self.logger.debug(f"Sample params: {preview}")

        try:
            _ = self.conn.execute("BEGIN")
            result = self.cursor.executemany(query, param_list)
            self.conn.commit()
            self.logger.info(f"Successfully inserted {self.cursor.rowcount} records.")
            return result
        except sqlite3.Error as e:
            self.conn.rollback()
            self.logger.error("Database error during executemany:")
            self.logger.error(traceback.format_exc())
            raise
        except Exception as e:
            self.conn.rollback()
            self.logger.error("Unexpected error during executemany:")
            self.logger.error(traceback.format_exc())
            raise

    def commit(self):
        """Commits active transaction to DB, saving changes."""
        try:
            self.conn.commit()
            self.logger.debug("Database changes committed.")
        except sqlite3.DatabaseError as e:
            self.logger.error(f"Error committing changes: {e}")
            raise

    def rollback(self):
        """Rolls back active transaction to DB, not saving changes (used if error)."""
        try:
            self.conn.rollback()
            self.logger.warning("Database changes rolled back.")
        except sqlite3.DatabaseError as e:
            self.logger.error(f"Error rolling back changes: {e}")
            raise

    def fetchall(self) -> list[sqlite3.Row]:
        """Returns all data from the latest DB query."""
        # db.execute("SELECT * FROM tickers")
        # results = db.fetchall()
        return self.cursor.fetchall()

    def fetchone(self) -> sqlite3.Row | None:
        """Returns the first row of data from the latest DB query."""
        return self.cursor.fetchone()

    def query_one(
        self, query: str, params: Sequence[Any] | None = None
    ) -> sqlite3.Row | None:
        """Executes a SELECT query and returns a single result."""
        _ = self.execute(query, params)
        return self.fetchone()

    def query_all(
        self, query: str, params: Sequence[Any] | None = None
    ) -> list[sqlite3.Row]:
        """Executes a SELECT query and returns all results."""
        _ = self.execute(query, params)
        return self.fetchall()

    def close(self) -> None:
        """Closes active DB connection."""
        self.conn.close()

    def __enter__(self) -> Self:
        """Runs when entering the with block. If no error, commit and close connection."""
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Runs when entering the with block. If error, rollback and close connection."""
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()

    def create_tables_if_not_exists(self) -> None:
        _ = self.execute("""
            CREATE TABLE IF NOT EXISTS tickers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                exchange TEXT NOT NULL,
                UNIQUE(ticker, exchange)
            )
        """)
        _ = self.execute("""
            CREATE TABLE IF NOT EXISTS splits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                exchange TEXT NOT NULL,
                split_date TEXT NOT NULL,
                split_ratio REAL NOT NULL,
                UNIQUE(ticker, exchange, split_date)
            )
        """)
        _ = self.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                exchange TEXT NOT NULL,
                order_date TEXT NOT NULL,
                shares REAL NOT NULL,
                adjusted_shares REAL,
                price REAL,
                order_type TEXT,
                UNIQUE(ticker, exchange, order_date, order_type)
            )
        """)


# def init_db(db: Database) -> None:
#     _ = db.execute("""
#         CREATE TABLE IF NOT EXISTS orders (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             ticker TEXT NOT NULL,
#             exchange TEXT,
#             order_date TEXT NOT NULL,
#             original_shares REAL NOT NULL,
#             adjusted_shares REAL
#         );
#
#         CREATE TABLE IF NOT EXISTS splits (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             ticker TEXT NOT NULL,
#             exchange TEXT NOT NULL,
#             split_date TEXT NOT NULL,
#             split_ratio REAL NOT NULL,
#             UNIQUE(ticker, exchange, split_date) -- Avoid inserting duplicates
#         );
#     """)
#     db.commit()
#     db.close()


# def save_ticker(db_path: str, symbol: str, exchange: str, full_symbol: str) -> bool:
#     try:
#         conn: sqlite3.Connection = sqlite3.connect(db_path)
#         cur: sqlite3.Cursor = conn.cursor()
#         _ = cur.execute(
#             "INSERT OR IGNORE INTO tickers (symbol, exchange, full_symbol) VALUES (?, ?, ?)",
#             (symbol, exchange, full_symbol),
#         )
#         conn.commit()
#         inserted: int = cur.rowcount
#         conn.close()
#         return inserted > 0
#     except Exception as e:
#         logger.error(f"DB insert failed for {full_symbol}: {e}")
#         return False


# def insert_order_into_db(
#     cursor, ticker, exchange, original_shares, adjusted_shares, order_date
# ):
#     cursor.execute(
#         """
#         INSERT INTO orders (ticker, exchange, original_shares, adjusted_shares, order_date)
#         VALUES (?, ?, ?, ?, ?)
#     """,
#         (ticker, exchange, original_shares, adjusted_shares, order_date),
#     )


# def get_adjusted_shares(
#     cursor: sqlite3.Cursor,
#     ticker: str,
#     exchange: str,
#     original_shares: float,
#     order_date: str,
# ) -> float:
#     _ = cursor.execute(
#         """
#         SELECT split_ratio FROM splits
#         WHERE ticker = ? AND exchange = ? AND split_date > ?
#         ORDER BY split_date ASC
#     """,
#         (ticker, exchange, order_date),
#     )
#
#     adjusted: float = original_shares
#     for (ratio,) in cursor.fetchall():
#         adjusted *= ratio
#     return adjusted
