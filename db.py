import sqlite3
import logging

logger: logging.Logger = logging.getLogger("ticker_importer.db")


def init_db(db_path: str) -> None:
    conn: sqlite3.Connection = sqlite3.connect(db_path)
    _ = conn.execute("""
        CREATE TABLE IF NOT EXISTS tickers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            exchange TEXT NOT NULL,
            full_symbol TEXT UNIQUE NOT NULL
        );
    """)
    conn.commit()
    conn.close()


def save_ticker(db_path: str, symbol: str, exchange: str, full_symbol: str) -> bool:
    try:
        conn: sqlite3.Connection = sqlite3.connect(db_path)
        cur: sqlite3.Cursor = conn.cursor()
        _ = cur.execute(
            "INSERT OR IGNORE INTO tickers (symbol, exchange, full_symbol) VALUES (?, ?, ?)",
            (symbol, exchange, full_symbol),
        )
        conn.commit()
        inserted: int = cur.rowcount
        conn.close()
        return inserted > 0
    except Exception as e:
        logger.error(f"DB insert failed for {full_symbol}: {e}")
        return False
