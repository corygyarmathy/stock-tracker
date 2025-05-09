import sqlite3
from unittest.mock import patch
import pytest

from stock_tracker.config import AppConfig
from stock_tracker.db import Database


def test_create_tables(app_config: AppConfig, test_db: Database):
    """Test tables are created correctly."""
    # Check tables exist by querying sqlite_master
    tables = test_db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    table_names = [table[0] for table in tables]

    assert "stocks" in table_names
    assert "stock_orders" in table_names
    assert "stock_info" in table_names
    assert "corporate_actions" in table_names
    assert "fx_rates" in table_names


def test_execute_single_query(app_config: AppConfig, test_db: Database):
    """Test executing a single SQL query."""
    # Insert a test stock
    _ = test_db.execute(
        "INSERT INTO stocks (ticker, exchange, currency, name) VALUES (?, ?, ?, ?)",
        ("AAPL", "NASDAQ", "USD", "Apple Inc."),
    )

    # Verify the stock was inserted correctly
    result = test_db.execute("SELECT * FROM stocks WHERE ticker = ?", ("AAPL",)).fetchone()

    assert result is not None
    assert result["ticker"] == "AAPL"
    assert result["exchange"] == "NASDAQ"
    assert result["currency"] == "USD"
    assert result["name"] == "Apple Inc."


def test_execute_with_named_params(app_config: AppConfig, test_db: Database):
    """Test executing a SQL query with named parameters."""
    # Insert a test stock using named parameters
    _ = test_db.execute(
        "INSERT INTO stocks (ticker, exchange, currency, name) VALUES (:ticker, :exchange, :currency, :name)",
        {
            "ticker": "MSFT",
            "exchange": "NASDAQ",
            "currency": "USD",
            "name": "Microsoft Corporation",
        },
    )

    # Verify the stock was inserted correctly
    result = test_db.execute(
        "SELECT * FROM stocks WHERE ticker = :ticker", {"ticker": "MSFT"}
    ).fetchone()

    assert result is not None
    assert result["ticker"] == "MSFT"
    assert result["name"] == "Microsoft Corporation"


def test_execute_error_handling(app_config: AppConfig, test_db: Database):
    """Test error handling during SQL execution."""
    # Try to execute an invalid SQL query
    with pytest.raises(sqlite3.Error):
        _ = test_db.execute("SELECT * FROM non_existent_table")


def test_execute_mixed_params_error(app_config: AppConfig, test_db: Database):
    """Test that mixing parameter styles raises an error."""
    # Positional placeholders with named parameters
    with pytest.raises(ValueError, match="Positional placeholders"):
        _ = test_db.execute(
            "INSERT INTO stocks (ticker, exchange) VALUES (?, ?)",
            {"ticker": "GOOG", "exchange": "NASDAQ"},
        )

    # Named placeholders with positional parameters
    with pytest.raises(ValueError, match="Named placeholders"):
        _ = test_db.execute(
            "INSERT INTO stocks (ticker, exchange) VALUES (:ticker, :exchange)", ["GOOG", "NASDAQ"]
        )


def test_executemany(app_config: AppConfig, test_db: Database):
    """Test bulk insert with executemany."""
    # Prepare test data for bulk insert
    stocks = [
        ("GOOG", "NASDAQ", "USD", "Alphabet Inc."),
        ("AMZN", "NASDAQ", "USD", "Amazon.com Inc."),
        ("TSLA", "NASDAQ", "USD", "Tesla, Inc."),
    ]

    # Execute bulk insert
    _ = test_db.executemany(
        "INSERT INTO stocks (ticker, exchange, currency, name) VALUES (?, ?, ?, ?)", stocks
    )

    # Verify all stocks were inserted
    results = test_db.execute(
        "SELECT * FROM stocks WHERE ticker IN (?, ?, ?)", ("GOOG", "AMZN", "TSLA")
    ).fetchall()

    assert len(results) == 3
    tickers = [row["ticker"] for row in results]
    assert "GOOG" in tickers
    assert "AMZN" in tickers
    assert "TSLA" in tickers


def test_executemany_with_named_params(app_config: AppConfig, test_db: Database):
    """Test bulk insert with executemany using named parameters."""
    # Prepare test data with named parameters
    stocks: list[dict[str, str]] = [
        {"ticker": "FB", "exchange": "NASDAQ", "currency": "USD", "name": "Meta Platforms Inc."},
        {"ticker": "NFLX", "exchange": "NASDAQ", "currency": "USD", "name": "Netflix Inc."},
    ]

    # Execute bulk insert with named parameters
    _ = test_db.executemany(
        "INSERT INTO stocks (ticker, exchange, currency, name) VALUES (:ticker, :exchange, :currency, :name)",
        stocks,
    )

    # Verify the stocks were inserted
    results = test_db.execute(
        "SELECT * FROM stocks WHERE ticker IN (?, ?)", ("FB", "NFLX")
    ).fetchall()

    assert len(results) == 2
    names = [row["name"] for row in results]
    assert "Meta Platforms Inc." in names
    assert "Netflix Inc." in names


def test_executemany_mixed_params_error(app_config: AppConfig, test_db: Database):
    """Test that mixing parameter styles in executemany raises an error."""
    # Positional placeholders with named parameters
    with pytest.raises(ValueError, match="Positional placeholders"):
        _ = test_db.executemany(
            "INSERT INTO stocks (ticker, exchange) VALUES (?, ?)",
            [{"ticker": "GOOG", "exchange": "NASDAQ"}],
        )

    # Named placeholders with positional parameters
    with pytest.raises(ValueError, match="Named placeholders"):
        _ = test_db.executemany(
            "INSERT INTO stocks (ticker, exchange) VALUES (:ticker, :exchange)",
            [["GOOG", "NASDAQ"]],
        )


def test_fetch_methods(app_config: AppConfig, test_db: Database):
    """Test the fetch methods (fetchone, fetchall)."""
    # Insert test data
    _ = test_db.execute(
        "INSERT INTO stocks (ticker, exchange, currency, name) VALUES (?, ?, ?, ?)",
        ("JPM", "NYSE", "USD", "JPMorgan Chase & Co."),
    )
    _ = test_db.execute(
        "INSERT INTO stocks (ticker, exchange, currency, name) VALUES (?, ?, ?, ?)",
        ("GS", "NYSE", "USD", "Goldman Sachs Group Inc."),
    )

    # Test fetchone
    _ = test_db.execute("SELECT * FROM stocks WHERE ticker = ?", ("JPM",))
    result = test_db.fetchone()
    assert result is not None
    assert result["ticker"] == "JPM"

    # Test fetchall
    _ = test_db.execute("SELECT * FROM stocks WHERE exchange = ? ORDER BY ticker", ("NYSE",))
    results = test_db.fetchall()
    assert len(results) == 2
    assert results[0]["ticker"] == "GS"
    assert results[1]["ticker"] == "JPM"


def test_query_convenience_methods(app_config: AppConfig, test_db: Database):
    """Test the query_one and query_all convenience methods."""
    # Insert test data
    _ = test_db.execute(
        "INSERT INTO stocks (ticker, exchange, currency, name) VALUES (?, ?, ?, ?)",
        ("INTC", "NASDAQ", "USD", "Intel Corporation"),
    )
    _ = test_db.execute(
        "INSERT INTO stocks (ticker, exchange, currency, name) VALUES (?, ?, ?, ?)",
        ("AMD", "NASDAQ", "USD", "Advanced Micro Devices, Inc."),
    )

    # Test query_one
    result = test_db.query_one("SELECT * FROM stocks WHERE ticker = ?", ("INTC",))
    assert result is not None
    assert result["name"] == "Intel Corporation"

    # Test query_all
    results = test_db.query_all(
        "SELECT * FROM stocks WHERE exchange = ? ORDER BY ticker", ("NASDAQ",)
    )
    # Count might vary depending on other tests, so we'll just check for our specific entries
    tickers = [row["ticker"] for row in results]
    assert "AMD" in tickers
    assert "INTC" in tickers


# def test_context_manager(app_config: AppConfig):
#     """Test the context manager functionality (commit on success)."""
#     db_path = app_config.db_path
#
#     # Use the context manager
#     with Database(db_path) as db:
#         # Make sure tables exist
#         db.create_tables_if_not_exists()
#         _ = db.execute(
#             "INSERT INTO stocks (ticker, exchange, currency, name) VALUES (?, ?, ?, ?)",
#             ("NVDA", "NASDAQ", "USD", "NVIDIA Corporation"),
#         )
#
#     # Open a new connection to verify the data was committed
#     with Database(db_path) as db:
#         result = db.query_one("SELECT * FROM stocks WHERE ticker = ?", ("NVDA",))
#         assert result is not None
#         assert result["name"] == "NVIDIA Corporation"
#
#
# def test_context_manager_rollback(app_config: AppConfig):
#     """Test that the context manager rolls back on exception."""
#     db_path = app_config.db_path
#
#     # Use the context manager with an exception
#     try:
#         with Database(db_path) as db:
#             _ = db.execute(
#                 "INSERT INTO stocks (ticker, exchange, currency, name) VALUES (?, ?, ?, ?)",
#                 ("CSCO", "NASDAQ", "USD", "Cisco Systems, Inc."),
#             )
#             # Force an exception
#             raise ValueError("Test exception")
#     except ValueError:
#         pass
#
#     # Open a new connection to verify the data was rolled back
#     with Database(db_path) as db:
#         result = db.query_one("SELECT * FROM stocks WHERE ticker = ?", ("CSCO",))
#         assert result is None
#
#
# def test_transaction_management(app_config: AppConfig):
#     """Test manual transaction management (commit and rollback)."""
#     db_path = app_config.db_path
#
#     # Test commit
#     db = Database(db_path)
#     _ = db.execute(
#         "INSERT INTO stocks (ticker, exchange, currency, name) VALUES (?, ?, ?, ?)",
#         ("ORCL", "NYSE", "USD", "Oracle Corporation"),
#     )
#     db.commit()
#     db.close()
#
#     # Verify data was committed
#     with Database(db_path) as db:
#         result = db.query_one("SELECT * FROM stocks WHERE ticker = ?", ("ORCL",))
#         assert result is not None
#
#     # Test rollback
#     db = Database(db_path)
#     _ = db.execute(
#         "INSERT INTO stocks (ticker, exchange, currency, name) VALUES (?, ?, ?, ?)",
#         ("CRM", "NYSE", "USD", "Salesforce, Inc."),
#     )
#     db.rollback()
#     db.close()
#
#     # Verify data was rolled back
#     with Database(db_path) as db:
#         result = db.query_one("SELECT * FROM stocks WHERE ticker = ?", ("CRM",))
#         assert result is None


@patch("logging.Logger.error")
def test_error_logging(mock_error_log, app_config: AppConfig, test_db: Database):
    """Test that database errors are properly logged."""
    # Execute invalid SQL to trigger an error
    try:
        test_db.execute("SELECT * FROM nonexistent_table")
    except sqlite3.Error:
        pass

    # Verify that the error was logged
    mock_error_log.assert_called()
    # Check that the first call to error() contains "Database error"
    assert "Database error" in mock_error_log.call_args_list[0][0][0]


def test_complex_query_with_joins(app_config: AppConfig, test_db: Database):
    """Test more complex queries with joins between tables."""
    # Insert a stock
    _ = test_db.execute(
        "INSERT INTO stocks (ticker, exchange, currency, name) VALUES (?, ?, ?, ?)",
        ("VTI", "NYSE", "USD", "Vanguard Total Stock Market ETF"),
    )

    # Get the stock_id
    stock = test_db.query_one("SELECT id FROM stocks WHERE ticker = ?", ("VTI",))
    if stock:
        stock_id = stock["id"]
    else:
        raise ValueError(f"Can't find stock at id: VTI")

    # Insert stock orders
    _ = test_db.execute(
        """INSERT INTO stock_orders 
           (stock_id, purchase_datetime, quantity, price_paid, fee, note) 
           VALUES (?, ?, ?, ?, ?, ?)""",
        (stock_id, "2023-01-15 10:30:00", 10, 200.50, 4.95, "Initial purchase"),
    )
    _ = test_db.execute(
        """INSERT INTO stock_orders 
           (stock_id, purchase_datetime, quantity, price_paid, fee, note) 
           VALUES (?, ?, ?, ?, ?, ?)""",
        (stock_id, "2023-02-20 14:15:00", 5, 205.75, 4.95, "Adding to position"),
    )

    # Test a JOIN query
    results = test_db.query_all(
        """
        SELECT s.ticker, s.exchange, so.quantity, so.price_paid, so.purchase_datetime
        FROM stocks s
        JOIN stock_orders so ON s.id = so.stock_id
        WHERE s.ticker = ?
        ORDER BY so.purchase_datetime
        """,
        ("VTI",),
    )

    assert len(results) == 2
    assert results[0]["ticker"] == "VTI"
    assert results[0]["quantity"] == 10
    assert results[0]["price_paid"] == 200.50
    assert results[1]["quantity"] == 5
    assert results[1]["price_paid"] == 205.75


@pytest.mark.parametrize(
    "table_name,expected_columns",
    [
        ("stocks", ["id", "ticker", "exchange", "currency", "name"]),
        (
            "stock_orders",
            ["id", "stock_id", "purchase_datetime", "quantity", "price_paid", "fee", "note"],
        ),
        (
            "stock_info",
            [
                "stock_id",
                "last_updated",
                "current_price",
                "market_cap",
                "pe_ratio",
                "dividend_yield",
            ],
        ),
        (
            "corporate_actions",
            ["id", "stock_id", "action_type", "action_date", "ratio", "target_stock_id"],
        ),
        ("fx_rates", ["base_currency", "target_currency", "date", "rate"]),
    ],
)
def test_table_schema(app_config: AppConfig, test_db: Database, table_name, expected_columns):
    """Test that table schemas match expected structure."""
    # Query table info
    columns = test_db.query_all(f"PRAGMA table_info({table_name})")

    # Extract column names
    column_names = [col["name"] for col in columns]

    # Check that all expected columns exist
    for expected_col in expected_columns:
        assert expected_col in column_names, f"Column {expected_col} not found in {table_name}"
