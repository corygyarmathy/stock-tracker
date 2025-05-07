import logging
import sqlite3
import traceback
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Self


class Database:
    # INFO: Example usage:
    # with Database("stock_orders.db") as db:
    #   db.execute("INSERT INTO tickers (ticker, exchange) VALUES (?, ?)", ("IVV", "ASX"))
    #   No need to call db.commit() — it will auto-commit if no exception occurs
    #   raise ValueError("Something went wrong!")  # <- Rolls back instead of committing
    def __init__(self, db_path: Path) -> None:
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

        # Confirm positional and named-placeholders are not being inter-mixed
        if "?" in query and isinstance(params, Mapping):
            raise ValueError("Positional placeholders (?) used with named parameters.")
        if ":" in query and isinstance(params, (list, tuple)):
            raise ValueError("Named placeholders (:) used with positional parameters.")

        try:
            _ = self.conn.execute("BEGIN")
            result: sqlite3.Cursor = self.cursor.execute(query, params)
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

        # Execute query
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

    # TODO: review that it actually doesn't execute if the tables exist
    def create_tables_if_not_exists(self) -> None:
        # Tracks each unique stock
        _ = self.execute("""
        CREATE TABLE stocks (
            id INTEGER PRIMARY KEY,
            ticker TEXT NOT NULL,
            exchange TEXT NOT NULL,
            currency TEXT NOT NULL,
            name TEXT,
            UNIQUE(ticker, exchange)
        );
        """)
        # Stores user orders
        _ = self.execute("""
        CREATE TABLE stock_orders (
            id INTEGER PRIMARY KEY,
            stock_id INTEGER NOT NULL,
            purchase_datetime TEXT NOT NULL,
            quantity REAL NOT NULL,
            price_paid REAL NOT NULL,  -- price in native currency per share
            fee REAL DEFAULT 0.0,
            note TEXT,
            FOREIGN KEY(stock_id) REFERENCES stocks(id)
        );
        """)
        # Caches current stock info (refreshable)
        _ = self.execute("""
        CREATE TABLE stock_info (
            stock_id INTEGER PRIMARY KEY,
            last_updated TEXT NOT NULL,
            current_price REAL,
            market_cap REAL,
            pe_ratio REAL,
            dividend_yield REAL,
            FOREIGN KEY(stock_id) REFERENCES stocks(id)
        );
        """)
        # Corporate actions like splits and mergers
        _ = self.execute("""
        CREATE TABLE corporate_actions (
            id INTEGER PRIMARY KEY,
            stock_id INTEGER NOT NULL,
            action_type TEXT NOT NULL, -- 'split', 'merger', 'acquisition', etc.
            action_date TEXT NOT NULL,
            ratio REAL,                -- e.g. 2.0 for 2:1 split
            target_stock_id INTEGER,   -- for mergers/acquisitions
            FOREIGN KEY(stock_id) REFERENCES stocks(id),
            FOREIGN KEY(target_stock_id) REFERENCES stocks(id)
        );
        """)
        # Currencies and conversion rates
        _ = self.execute("""
        CREATE TABLE fx_rates (
            base_currency TEXT NOT NULL,
            target_currency TEXT NOT NULL,
            date TEXT NOT NULL,
            rate REAL NOT NULL,
            PRIMARY KEY(base_currency, target_currency, date)
        );
        """)
        # Useful indexes
        # TODO: investigate these further
        _ = self.execute("""
        CREATE INDEX idx_orders_stock_id ON stock_orders(stock_id);
        CREATE INDEX idx_prices_stock_date ON historical_prices(stock_id, date);
        CREATE INDEX idx_fx_rates_date ON fx_rates(date);
        """)
