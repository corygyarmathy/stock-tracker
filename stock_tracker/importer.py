import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf

from stock_tracker.models import Stock, StockOrder
from stock_tracker.repositories.order_repository import OrderRepository
from stock_tracker.repositories.stock_info_repository import StockInfoRepository
from stock_tracker.repositories.stock_repository import StockRepository
from stock_tracker.services.ticker_service import TickerService
from stock_tracker.yfinance_api import get_valid_ticker, search_ticker_quotes

logger: logging.Logger = logging.getLogger(__name__)


# --- CSV Parsing Functions  ---
def parse_csv_datetime(value: Any) -> datetime:
    """Parses a string from CSV into a datetime object."""
    if not isinstance(value, str):
        raise ValueError(f"Expected string for datetime, got {type(value)}")
    try:
        # IMPORTANT: Ensure this format matches your CSV!
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        raise ValueError(
            f"Invalid datetime format: '{value}'. Expected and parse format is %Y-%m-%d %H:%M:%S"
        )  # Be specific in the error


def parse_csv_float(value: Any, field_name: str) -> float:
    """Parses a value from CSV into a float."""
    # Handle empty strings which might come from pandas fillna('')
    if isinstance(value, str) and value.strip() == "":
        raise ValueError(f"Empty string value for '{field_name}'")
    if value is None:  # Handle None if not using fillna('')
        raise ValueError(f"Missing value for '{field_name}'")

    try:
        return float(value)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid float value for '{field_name}': '{value}' (type: {type(value)})")


def parse_csv_quantity(value: Any) -> float:
    qty = parse_csv_float(value, "quantity")
    if qty <= 0:
        raise ValueError(f"Quantity must be positive, got {qty}")
    return qty


def parse_csv_price_paid(value: Any) -> float:
    price = parse_csv_float(value, "price_paid")
    if price < 0:
        raise ValueError(f"Price paid cannot be negative, got {price}")
    return price


def parse_csv_fee(value: Any) -> float:
    # Fee can be zero, but not negative.
    fee = parse_csv_float(value, "fee")
    if fee < 0:
        raise ValueError(f"Fee cannot be negative, got {fee}")
    return fee


def validate_ticker_with_fallback(
    symbol: str, exchange: str, interactive: bool = True
) -> tuple[str | None, str | None, yf.Ticker | None]:
    """
    Validate a ticker with interactive fallback search when validation fails.

    Args:
        symbol: Stock symbol
        exchange: Exchange code
        interactive: Whether to prompt for user input when validation fails

    Returns:
        tuple of (symbol, exchange, ticker_object) - Any may be None if validation fails
    Uses yfinance's built-in session management.
    """
    # First, try with the provided symbol and exchange
    full_symbol: str = f"{symbol}.{exchange}" if exchange else symbol
    logger.info(f"Attempting to validate ticker {full_symbol}")
    ticker: yf.Ticker | None = get_valid_ticker(symbol, exchange)

    if ticker:
        logger.info(f"Successfully validated ticker: {full_symbol}")
        return symbol, exchange, ticker

    # If validation failed and we're in interactive mode, search for alternatives
    if interactive:
        logger.warning(f"Failed to validate ticker: {full_symbol}. Searching for alternatives...")

        # Search using just the symbol as query
        search_results = search_ticker_quotes(symbol)

        if search_results:
            logger.info(f"Found alternatives for {full_symbol}")

            # Prompt user to select from results
            selected = prompt_user_to_select(search_results)

            if selected:
                # Extract new symbol and exchange
                new_symbol = selected.get("symbol")
                new_exchange = selected.get("exchange")

                if new_symbol and new_exchange:
                    logger.info(f"User selected alternative: {new_symbol}.{new_exchange}")

                    # Validate the selected ticker
                    new_ticker = get_valid_ticker(new_symbol, new_exchange)
                    if new_ticker:
                        return new_symbol, new_exchange, new_ticker
                    else:
                        logger.warning(
                            f"Selected alternative {new_symbol}.{new_exchange} also failed validation"
                        )

    # If we get here, validation failed and no valid alternative was selected
    return None, None, None


def batch_validate_with_fallback(
    tickers_to_validate: list[tuple[str, str]],
    batch_size: int = 2,  # Smaller batch size
    batch_delay: float = 15.0,  # Longer delay between batches
    interactive: bool = True,
) -> dict[tuple[str, str], tuple[str | None, str | None, yf.Ticker | None]]:
    """
    Batch validate tickers with interactive fallback for invalid tickers.

    Args:
        tickers_to_validate: List of (symbol, exchange) tuples to validate
        batch_size: Number of tickers to process in each batch
        batch_delay: Delay in seconds between batches
        interactive: Whether to prompt for user input when validation fails

    Returns:
        Dictionary mapping original (symbol, exchange) to (new_symbol, new_exchange, ticker_obj)
    Batch validate tickers with fallback, using yfinance's built-in session management.
    """
    results: dict[tuple[str, str], tuple[str | None, str | None, yf.Ticker | None]] = {}
    total_batches = (len(tickers_to_validate) - 1) // batch_size + 1

    logger.info(f"Batch validating {len(tickers_to_validate)} tickers in {total_batches} batches")

    # Process in batches with generous delays
    for i in range(0, len(tickers_to_validate), batch_size):
        batch = tickers_to_validate[i : i + batch_size]
        batch_num = i // batch_size + 1

        logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} tickers)")

        for j, (symbol, exchange) in enumerate(batch):
            logger.info(
                f"Validating ticker {i + j + 1}/{len(tickers_to_validate)}: {symbol}.{exchange}"
            )

            # Try validation without custom session
            ticker_obj: yf.Ticker | None = get_valid_ticker(symbol, exchange)

            if ticker_obj:
                # Successfully validated
                results[(symbol, exchange)] = (symbol, exchange, ticker_obj)
                logger.info(f"Successfully validated {symbol}.{exchange}")
            elif interactive:
                # Try with fallback
                logger.info(
                    f"Ticker {symbol}.{exchange} failed validation, trying interactive search..."
                )

                # Add delay before interactive search
                time.sleep(5.0)

                new_symbol, new_exchange, new_ticker = validate_ticker_with_fallback(
                    symbol, exchange, interactive=True
                )
                results[(symbol, exchange)] = (new_symbol, new_exchange, new_ticker)
            else:
                # Non-interactive mode and validation failed
                results[(symbol, exchange)] = (None, None, None)
                logger.warning(f"Failed to validate {symbol}.{exchange} in non-interactive mode")

            # Add delay between tickers in batch
            if j < len(batch) - 1:
                time.sleep(5.0)

        # Add longer delay between batches
        if batch_num < total_batches:
            logger.info(
                f"Batch {batch_num} complete. Sleeping for {batch_delay} seconds before next batch"
            )
            time.sleep(batch_delay)

    return results


def prompt_user_to_select(results: list[dict[str, Any]]) -> dict[str, Any] | None:
    """
    Display search results and prompt user to select the correct ticker.

    Args:
        results: List of ticker search results

    Returns:
        Selected ticker info or None if user skips
    """
    if not results:
        print("No alternatives found.")
        return None

    logger.info(f"Found {len(results)} results. Prompting user to select.")
    col_widths: dict[str, int] = {
        "index": 4,
        "symbol": 12,
        "exchange": 10,
        "type": 8,
        "name": 40,
    }

    header: str = (
        f"{'No.':<{col_widths['index']}} "
        f"{'Symbol':<{col_widths['symbol']}} "
        f"{'Exchange':<{col_widths['exchange']}} "
        f"{'Type':<{col_widths['type']}} "
        f"{'Name':<{col_widths['name']}}"
    )
    print("\nPotential matches:")
    print(header)
    print("-" * len(header))

    for idx, item in enumerate(results, 1):
        symbol: str = str(item.get("symbol", ""))[: col_widths["symbol"]]
        exchange: str = str(item.get("exchange", ""))[: col_widths["exchange"]]
        quote_type: str = str(item.get("quoteType", ""))[: col_widths["type"]]
        name: str = str(item.get("shortname") or item.get("longname", ""))[: col_widths["name"]]

        info: str = (
            f"{str(idx):<{col_widths['index']}} "
            f"{symbol:<{col_widths['symbol']}} "
            f"{exchange:<{col_widths['exchange']}} "
            f"{quote_type:<{col_widths['type']}} "
            f"{name:<{col_widths['name']}}"
        )
        print(info)

    while True:
        try:
            choice_str: str | None = input(
                "Enter the number of the correct symbol (or press Enter to skip): "
            ).strip()

            if not choice_str:
                return None
            choice_int: int = int(choice_str)
            if 1 <= choice_int <= len(results):
                return results[choice_int - 1]
            else:
                print(f"Please enter a number between 1 and {len(results)}.")
        except ValueError:
            print("Invalid input. Enter a number.")


def read_csv_file(csv_path: Path) -> pd.DataFrame | None:
    """
    Read and validate a CSV file.

    Args:
        csv_path: Path to the CSV file

    Returns:
        DataFrame containing the CSV data or None if there was an error
    """
    try:
        df: pd.DataFrame = pd.read_csv(csv_path, dtype=str).fillna("")
        if df.empty:
            logger.warning(f"CSV file is empty: {csv_path}")
            return None
        return df
    except FileNotFoundError:
        logger.error(f"CSV file not found: {csv_path}")
        return None
    except Exception as e:
        logger.error(f"Error reading CSV file {csv_path}: {e}")
        return None


def extract_unique_tickers(df: pd.DataFrame) -> set[tuple[str, str]]:
    """
    Extract unique ticker/exchange combinations from DataFrame.

    Args:
        df: DataFrame containing stock order data

    Returns:
        Set of unique (ticker, exchange) tuples
    """
    # Common tickers and their exchanges - can help reduce API calls
    common_tickers = {
        "AAPL": "NASDAQ",
        "MSFT": "NASDAQ",
        "GOOGL": "NASDAQ",
        "GOOG": "NASDAQ",
        "AMZN": "NASDAQ",
        "META": "NASDAQ",
        "TSLA": "NASDAQ",
        "NVDA": "NASDAQ",
        "JPM": "NYSE",
        "XOM": "NYSE",
        "V": "NYSE",
        "WMT": "NYSE",
    }

    unique_tickers: set[tuple[str, str]] = set()

    for i in range(len(df)):
        row_data: dict[str, str] = df.iloc[i].to_dict()
        symbol: str = row_data.get("ticker", "").strip().upper()
        exchange: str = row_data.get("exchange", "").strip().upper()

        # Use common ticker mapping if known
        if symbol in common_tickers and not exchange:
            exchange = common_tickers[symbol]
            logger.info(f"Using known exchange {exchange} for {symbol}")

        if symbol and exchange:
            unique_tickers.add((symbol.upper(), exchange.upper()))

    return unique_tickers


def get_existing_stocks(
    stock_repo: StockRepository, tickers: set[tuple[str, str]]
) -> dict[tuple[str, str], Stock]:
    """
    Check which stocks already exist in the database.

    Args:
        stock_repo: Repository for stock data
        tickers: Set of (ticker, exchange) tuples to check

    Returns:
        Dictionary mapping (ticker, exchange) to existing Stock objects
    """
    existing_stocks: dict[tuple[str, str], Stock] = {}

    for symbol, exchange in tickers:
        stock: Stock | None = stock_repo.get_by_ticker_exchange(symbol, exchange)
        if stock:
            existing_stocks[(symbol, exchange)] = stock
            logger.debug(f"Stock {symbol}.{exchange} already exists in database")

    return existing_stocks


def validate_and_save_stocks(
    stocks_to_validate: list[tuple[str, str]],
    stock_repo: StockRepository,
    stock_info_repo: StockInfoRepository,
    existing_stocks: dict[tuple[str, str], Stock],
    batch_size: int = 2,
    batch_delay: float = 15.0,
    interactive: bool = True,
) -> tuple[dict[tuple[str, str], Stock], dict[tuple[str, str], tuple[str, str]]]:
    """
    Validate stocks not in the database and save them.

    Args:
        stocks_to_validate: List of (ticker, exchange) tuples to validate
        stock_repo: Repository for stock data
        existing_stocks: Dictionary of stocks that already exist in the database
        batch_size: Number of tickers to validate in each batch
        batch_delay: Delay in seconds between batches
        interactive: Whether to prompt for user input when validation fails

    Returns:
        Tuple of (validated_stocks, stock_mapping) where:
        - validated_stocks: Dictionary mapping (ticker, exchange) to Stock objects
        - stock_mapping: Dictionary mapping original (ticker, exchange) to corrected (ticker, exchange)
    """
    validated_stocks: dict[tuple[str, str], Stock] = {}
    stock_mapping: dict[tuple[str, str], tuple[str, str]] = {}

    # Start with existing stocks
    validated_stocks.update(existing_stocks)

    if not stocks_to_validate:
        logger.info("No new stocks to validate")
        return validated_stocks, stock_mapping

    logger.info(f"Validating {len(stocks_to_validate)} new stocks")

    # Use batch validation without custom session
    validation_results = batch_validate_with_fallback(
        stocks_to_validate,
        batch_size=batch_size,
        batch_delay=batch_delay,
        interactive=interactive,
    )

    # Process validation results
    for original_key, (new_symbol, new_exchange, ticker_obj) in validation_results.items():
        if new_symbol and new_exchange and ticker_obj:
            # Create stock object from ticker data
            stock = yf_ticker_to_stock(ticker_obj)

            if not stock:
                logger.error(f"Failed to convert ticker to Stock object")
                continue
            # Extract both models from a single ticker object
            stock, stock_info = TickerService.extract_models(ticker_obj)

            # Save stock to database
            _ = stock_repo.upsert(stock)

            # Update stock_id and save stock_info
            stock_info.stock_id = stock.id
            stock_info_repo.insert(stock_info)

            # If symbol was corrected, store mapping
            if original_key != (new_symbol.upper(), new_exchange.upper()):
                stock_mapping[original_key] = (new_symbol.upper(), new_exchange.upper())
                logger.info(
                    f"Symbol corrected: {original_key[0]}.{original_key[1]} -> {new_symbol}.{new_exchange}"
                )

            # Add to validated stocks cache
            validated_stocks[(new_symbol.upper(), new_exchange.upper())] = stock
            logger.info(f"Added new stock to database: {new_symbol}.{new_exchange}")

    return validated_stocks, stock_mapping


def create_orders_from_csv(
    df: pd.DataFrame,
    validated_stocks: dict[tuple[str, str], Stock],
    stock_mapping: dict[tuple[str, str], tuple[str, str]],
    order_repo: OrderRepository,
) -> int:
    """
    Create stock orders from CSV data.

    Args:
        df: DataFrame containing stock order data
        validated_stocks: Dictionary mapping (ticker, exchange) to Stock objects
        stock_mapping: Dictionary mapping original (ticker, exchange) to corrected (ticker, exchange)
        order_repo: Repository for order data

    Returns:
        Number of orders successfully inserted
    """
    inserted_orders = 0

    for i in range(len(df)):
        # Calculate human-readable row number (1-based, plus 1 for header)
        row_number: int = i + 2
        row_data: dict[str, str] = df.iloc[i].to_dict()

        # Get basic ticker info
        symbol: str = row_data.get("ticker", "").strip().upper()
        exchange: str = row_data.get("exchange", "").strip().upper()
        note = row_data.get("note", None)

        if not symbol or not exchange:
            logger.warning(
                f"Row {row_number}: Missing 'ticker' or 'exchange'. Skipping row: {row_data}"
            )
            continue

        # Check if this symbol was corrected during validation
        original_key = (symbol, exchange)
        corrected_key = stock_mapping.get(original_key, original_key)

        # Get the validated stock
        stock = validated_stocks.get(corrected_key)

        if not stock:
            logger.warning(
                f"Row {row_number}: Stock {symbol}.{exchange} was not validated. Skipping order."
            )
            continue

        # Parse and validate order data
        try:
            purchase_dt: datetime = parse_csv_datetime(row_data.get("datetime", ""))
            quantity: float = parse_csv_quantity(row_data.get("quantity", ""))
            price_paid: float = parse_csv_price_paid(row_data.get("price_paid", ""))
            fee: float = parse_csv_fee(row_data.get("fee", "0.0"))

            if not stock.id:
                raise ValueError(f"Stock {stock.ticker}.{stock.exchange} is missing its ID value.")

            # Augment note if symbol was corrected
            if original_key != corrected_key:
                corrected_note = f"Original symbol: {original_key[0]}.{original_key[1]}"
                if note:
                    note = f"{note}; {corrected_note}"
                else:
                    note = corrected_note

            # Create and insert StockOrder
            order: StockOrder = StockOrder(
                id=None,
                stock_id=stock.id,
                purchase_datetime=purchase_dt,
                quantity=quantity,
                price_paid=price_paid,
                fee=fee,
                note=note,
            )

            order_id = order_repo.insert(order)
            order.id = order_id
            inserted_orders += 1
            logger.info(
                f"Row {row_number}: Imported order ID {order.id} for {stock.ticker}.{stock.exchange}"
            )

        except ValueError as e:
            logger.error(
                f"Row {row_number}: Order data validation error: {e}. Skipping row: {row_data}"
            )
            continue
        except Exception as e:
            logger.error(
                f"Row {row_number}: Unexpected error processing order row: {e}. Skipping row: {row_data}",
                exc_info=True,
            )
            continue

    logger.info(f"Finished importing orders. Successfully imported {inserted_orders} orders")
    return inserted_orders


def import_valid_orders(
    csv_path: Path,
    stock_repo: StockRepository,
    stock_info_repo: StockInfoRepository,
    order_repo: OrderRepository,
    batch_size: int = 2,
    batch_delay: float = 15.0,
    interactive: bool = True,
) -> None:
    """
    Import and validate orders from a CSV file.

    Args:
        csv_path: Path to the CSV file containing orders
        stock_repo: Repository for stock data
        order_repo: Repository for order data
        batch_size: Number of tickers to validate in each batch
        batch_delay: Delay in seconds between batches
        interactive: Whether to prompt for user input when validation fails
    """
    # Read and validate CSV
    df = read_csv_file(csv_path)
    if df is None or df.empty:
        return

    # Extract unique tickers from CSV
    unique_tickers = extract_unique_tickers(df)
    if not unique_tickers:
        logger.warning(f"No valid ticker/exchange combinations found in CSV: {csv_path}")
        return

    logger.info(f"Found {len(unique_tickers)} unique stock symbols to validate")

    # Check which stocks already exist and validate new ones
    existing_stocks = get_existing_stocks(stock_repo, unique_tickers)
    stocks_to_validate = [ticker for ticker in unique_tickers if ticker not in existing_stocks]

    # Validate new stocks and update database
    validated_stocks, stock_mapping = validate_and_save_stocks(
        stocks_to_validate,
        stock_repo,
        stock_info_repo,
        existing_stocks,
        batch_size,
        batch_delay,
        interactive,
    )

    # Create orders from CSV data
    create_orders_from_csv(df, validated_stocks, stock_mapping, order_repo)
