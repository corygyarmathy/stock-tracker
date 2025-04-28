import sqlite3
from typing import Any
import yfinance as yf
import pandas as pd
from datetime import datetime
import logging


logger: logging.Logger = logging.getLogger("refresh_splits")


def get_all_unique_tickers(cursor: sqlite3.Cursor) -> list[str]:
    _ = cursor.execute("""
        SELECT DISTINCT ticker, exchange FROM orders
    """)
    return cursor.fetchall()


def fetch_stored_split_dates(cursor: sqlite3.Cursor, ticker: str, exchange: str):
    _ = cursor.execute(
        """
        SELECT split_date FROM splits
        WHERE ticker = ? AND exchange = ?
    """,
        (ticker, exchange),
    )
    return set(row[0] for row in cursor.fetchall())


def insert_new_splits(
    cursor: sqlite3.Cursor, ticker: str, exchange: str, splits: pd.Series[float]
) -> int:
    formatted_splits: dict[str, float] = format_split_dates(splits)
    inserted = 0
    for date_str, ratio in formatted_splits.items():
        logging.debug(
            f"Inserting split for {ticker}.{exchange} on {date_str} ratio: {ratio}"
        )
        try:
            _ = cursor.execute(
                """
                INSERT INTO splits (ticker, exchange, split_date, split_ratio)
                VALUES (?, ?, ?, ?)
            """,
                (ticker, exchange, date_str, ratio),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            # Split already exists (due to UNIQUE constraint), ignore
            continue
    return inserted


def recalculate_adjusted_shares(
    cursor: sqlite3.Cursor, ticker: str, exchange: str
) -> int:
    _ = cursor.execute(
        """
        SELECT id, original_shares, order_date FROM orders
        WHERE ticker = ? AND exchange = ?
    """,
        (ticker, exchange),
    )

    orders: list[Any] = cursor.fetchall()
    updated = 0

    for order_id, original_shares, order_date in orders:
        _ = cursor.execute(
            """
            SELECT split_ratio FROM splits
            WHERE ticker = ? AND exchange = ? AND split_date > ?
            ORDER BY split_date ASC
        """,
            (ticker, exchange, order_date),
        )

        adjusted = original_shares
        for (ratio,) in cursor.fetchall():
            adjusted *= ratio

        _ = cursor.execute(
            """
            UPDATE orders
            SET adjusted_shares = ?
            WHERE id = ?
        """,
            (adjusted, order_id),
        )
        updated += 1

    return updated


def format_split_dates(splits: pd.Series[float]) -> dict[str, float]:
    return {
        date.strftime("%Y-%m-%d"): ratio
        for date, ratio in splits.items()
        if isinstance(date, pd.Timestamp)  # guards runtime + satisfies Pyright
    }


def refresh_splits() -> None:
    conn: sqlite3.Connection = sqlite3.connect(DB_PATH)
    cursor: sqlite3.Cursor = conn.cursor()

    tickers = get_all_unique_tickers(cursor)
    logging.info(f"Found {len(tickers)} unique tickers to check for splits.")

    total_inserted = 0

    for ticker, exchange in tickers:
        full_symbol = f"{ticker}.{exchange}"
        try:
            stock = yf.Ticker(full_symbol)
            splits = stock.splits
        except Exception as e:
            logging.warning(f"Failed to fetch splits for {full_symbol}: {e}")
            continue

        formatted_splits = format_split_dates(splits)
        new_splits = {
            date: ratio
            for date, ratio in formatted_splits.items()
            if date not in fetch_stored_split_dates(cursor, ticker, exchange)
        }

        inserted_count = insert_new_splits(
            cursor, ticker, exchange, pd.Series(new_splits)
        )
        total_inserted += inserted_count

        updated_count = recalculate_adjusted_shares(cursor, ticker, exchange)

        if inserted_count > 0:
            logging.info(f"Inserted {inserted_count} new split(s) for {full_symbol}.")
        logging.info(
            f"Updated adjusted shares for {updated_count} order(s) of {full_symbol}."
        )

        conn.commit()
        conn.close()

        logging.info(f"Done. Total new splits inserted: {total_inserted}")


if __name__ == "__main__":
    refresh_splits()
