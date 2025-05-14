from datetime import datetime
import logging
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf

from stock_tracker.models import Stock, StockOrder
from stock_tracker.repositories.order_repository import OrderRepository
from stock_tracker.repositories.stock_repository import StockRepository
from stock_tracker.yfinance_api import RateLimitedCachedSession

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


def is_valid_ticker(
    symbol: str, exchange: str, session: "RateLimitedCachedSession", max_retries: int = 3
) -> yf.Ticker | None:
    """
    Validates if a ticker symbol is valid by checking if it has valid price information.
    Implements exponential backoff for retries on potential API request issues.

    :param symbol: Stock symbol (e.g., "AAPL")
    :param exchange: Exchange code (e.g., "NASDAQ", "AX"). Can be None or empty for US stocks.
    :param session: Cached session with rate limiting
    :param max_retries: Maximum number of retry attempts for API calls
    :return: Ticker object if valid and price info is found, None otherwise
    """

    # Try common US exchanges with symbol only first
    us_exchanges = ["NASDAQ", "NYSE", "ARCA", "PCX"]  # NYSE Arca may just be ARCA or blank
    potential_tickers: list[str] = []

    if exchange and exchange.upper() in us_exchanges:
        potential_tickers.append(symbol)  # For US exchanges, try symbol alone first
        potential_tickers.append(f"{symbol}.{exchange}")  # And then with suffix, just in case
    elif exchange:  # For non-US exchanges, suffix is usually required
        potential_tickers.append(f"{symbol}.{exchange.upper()}")
        potential_tickers.append(symbol)  # As a fallback, try symbol alone
    else:  # No exchange info provided
        potential_tickers.append(symbol)

    # Remove duplicates if any by converting to dict and back to list
    potential_tickers = list(dict.fromkeys(potential_tickers))

    for attempt_ticker_str in potential_tickers:
        logger.debug(f"Attempting to validate: {attempt_ticker_str}")
        retry_count = 0
        current_ticker_obj: yf.Ticker | None = None

        while retry_count <= max_retries:
            try:
                current_ticker_obj = yf.Ticker(attempt_ticker_str, session=session)

                # Try fast_info first
                price = current_ticker_obj.fast_info.get("last_price")
                currency = current_ticker_obj.fast_info.get("currency")

                if price is not None and price > 0 and currency:
                    logger.info(
                        f"Validated {attempt_ticker_str} with fast_info: Price={price} {currency}"
                    )
                    return current_ticker_obj

                # If fast_info fails or lacks price, try .info
                if not (price and price > 0 and currency):
                    logger.debug(
                        f"fast_info for {attempt_ticker_str} insufficient (Price: {price}, Currency: {currency}). Trying .info."
                    )
                    # ticker.info can be slow and might raise an exception if the ticker is truly invalid
                    # or if there are network issues not caught by the session.
                    # Ensure your session handles underlying yfinance HTTP errors if possible,
                    # or catch them here.
                    info = current_ticker_obj.info
                    price = info.get("currentPrice") or info.get(
                        "previousClose"
                    )  # Fallback to previousClose
                    currency = info.get("currency")

                    if price is not None and price > 0 and currency:
                        logger.info(
                            f"Validated {attempt_ticker_str} with .info: Price={price} {currency}"
                        )
                        return current_ticker_obj
                    else:
                        logger.warning(
                            f"{attempt_ticker_str}: Could not get valid price from .info (Price: {price}, Currency: {currency})"
                        )
                        # Break from retry loop for this ticker_str, move to next potential_ticker_str
                        break
                else:  # fast_info was sufficient
                    return current_ticker_obj

            except Exception as e:  # Catching a broader range of yfinance/network issues
                error_message = str(e).lower()
                # yfinance can sometimes return simple Exceptions for "No data found"
                # or specific HTTP errors if not wrapped by your session.
                if (
                    "no data found" in error_message
                    or "failed to decrypt" in error_message
                    or "404" in error_message
                ):  # Common yfinance errors for invalid tickers
                    logger.warning(
                        f"Could not fetch data for {attempt_ticker_str}: {e}. This might indicate an invalid ticker or temporary issue."
                    )
                    break  # Break from retry loop for this ticker_str, it's likely invalid

                # Check for rate limit error text from Yahoo Finance responses
                # (This might be HTML in the exception message)
                is_rate_limit_error = (
                    "rate limit" in error_message
                    or "too many requests" in error_message
                    or "crumb trail" in error_message
                )  # often related to session/cookie issues yfinance handles

                if is_rate_limit_error:
                    retry_count += 1
                    if retry_count > max_retries:
                        logger.error(
                            f"Max retries exceeded for {attempt_ticker_str} due to API errors. Giving up on this ticker string."
                        )
                        break  # Break from retry loop

                    wait_time = min(
                        60, (2**retry_count) + (random.randint(0, 1000) / 1000)
                    )  # Exponential backoff
                    logger.warning(
                        f"API error for {attempt_ticker_str} (possibly rate limit). Retrying in {wait_time:.2f} seconds (attempt {retry_count}/{max_retries}). Error: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    # Not a known rate limit error, and not a "no data" error
                    logger.error(
                        f"Failed to validate ticker {attempt_ticker_str} with unhandled error: {e}"
                    )
                    break  # Break from retry loop, move to next potential_ticker_str

        # If this attempt_ticker_str loop finished without returning, it failed.
        # The outer loop will then try the next potential_ticker_str.

    logger.warning(
        f"Failed to validate {symbol} (exchange: {exchange}) after trying: {potential_tickers}"
    )
    return None


        )
        return result.quotes
    except Exception as e:
        logger.error(f"Search failed for {ticker}: {e}")
        return []
def search_ticker_quotes(
    ticker: str, session: RateLimitedCachedSession, max_retries: int = 3
) -> list[dict[str, Any]]:
    """
    Search for ticker symbols in Yahoo Finance with retry mechanism.

    Args:
        ticker: The search query (ticker or company name)
        session: Cached session with rate limiting
        max_retries: Maximum number of retry attempts

    Returns:
        List of matching ticker quotes
    """
    retry_count = 0

    while retry_count <= max_retries:
        try:
            logger.debug(f"Searching for tickers which match: {ticker}")
            result: yf.Search = yf.Search(
                query=ticker, max_results=20, news_count=0, lists_count=0, session=session
            )
            return result.quotes
        except Exception as e:
            error_message: str = str(e).lower()

            # Check if this is a rate limit error
            if "rate limit" in error_message or "too many requests" in error_message:
                retry_count += 1

                if retry_count > max_retries:
                    logger.error(f"Max retries exceeded for search '{ticker}'. Giving up.")
                    return []

                # Exponential backoff with jitter
                wait_time: int = min(60, (2**retry_count) + (random.randint(0, 1000) / 1000))
                logger.warning(
                    f"Rate limited for search '{ticker}'. Retrying in {wait_time:.2f} seconds (attempt {retry_count}/{max_retries})"
                )
                time.sleep(wait_time)
            else:
                # If it's not a rate limit error, don't retry
                logger.error(f"Search failed for '{ticker}': {e}")
                return []

    return []


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


def yf_ticker_to_stock(ticker: yf.Ticker) -> Stock | None:
    """Converts yfinance Ticker info to a Stock model, with basic validation."""
    info: dict[str, Any] = ticker.info

    # Basic validation on essential fields from yfinance
    symbol = info.get("symbol")
    exchange = info.get("exchange")
    currency = info.get("currency")
    name = info.get("shortName") or info.get("longName")  # Allow name to be None

    if not symbol or not isinstance(symbol, str):
        logger.error(f"YF info missing valid symbol for {ticker.ticker}: {info.get('symbol')}")
        return None
    if not exchange or not isinstance(exchange, str):
        logger.error(f"YF info missing valid exchange for {symbol}: {info.get('exchange')}")
        # TODO: Can we make a guess based on the ticker format? e.g. AAPL -> NASDAQ, AAPL.L -> LSE?
        # This is complex; for now, error out or default
        exchange = "UNKNOWN"  # Or return None if unknown exchange is unacceptable
    if not currency or not isinstance(currency, str):
        logger.warning(
            f"YF info missing valid currency for {symbol}.{exchange}: {info.get('currency')}. Defaulting to USD."
        )
        currency = "USD"  # Or handle this as an error if currency is mandatory

    return Stock(
        id=None,
        ticker=symbol.upper(),
        exchange=exchange,
        currency=currency.upper(),  # Standardise currency codes
        name=name,
    )


def import_valid_stocks(
    symbol: str, exchange: str, stock_repo: StockRepository, session: CachedLimiterSession
) -> Stock | None:
    ticker: yf.Ticker | None = is_valid_ticker(symbol, exchange, session)
    inserted = 0
    if not ticker:
        logger.warning(f"Invalid ticker: {symbol}.{exchange}. Searching for alternatives...")
        results = search_ticker_quotes(symbol, session)
        match = prompt_user_to_select(results)
        if match:
            ticker = is_valid_ticker(symbol, exchange, session)
        else:
            logger.warning(f"Skipped: {symbol}.{exchange}")
    if ticker:
        stock: Stock | None = yf_ticker_to_stock(ticker)
        if stock:
            if stock_repo.upsert(stock):
                inserted += 1
                logger.info(f"Upserted {stock.ticker}.{stock.exchange}")
            return stock
    return None


def import_valid_orders(
    csv_path: Path,
    stock_repo: StockRepository,
    order_repo: OrderRepository,
    session: RateLimitedCachedSession,
) -> None:
    try:
        # Read CSV, converting everything to string and filling empty with ''
        # This makes parsing functions receive strings or '' consistently
        df: pd.DataFrame = pd.read_csv(csv_path, dtype=str).fillna("")
        if df.empty:
            logger.warning(f"CSV file is empty or contains no data rows: {csv_path}")
            return
    except FileNotFoundError:
        logger.error(f"CSV file not found: {csv_path}")
        return
    except Exception as e:
        logger.error(f"Error reading or processing CSV file {csv_path}: {e}", exc_info=True)
        return

    inserted_orders = 0
    # Cache for stocks validated/upserted during this import run
    validated_stocks: dict[tuple[str, str], Stock] = {}

    # Iterate through dataframe rows using positional index
    # This gives a direct integer index 'i'
    for i in range(len(df)):
        # Calculate human-readable row number (1-based, plus 1 for header)
        row_number: int = i + 2

        # Get the row data using the integer position
        row_data: dict[str, str] = df.iloc[i].to_dict()

        # --- Basic check for essential identifier columns ---
        symbol_raw = row_data.get("ticker", "").strip()
        exchange_raw = row_data.get("exchange", "").strip()
        note = row_data.get("note", None)

        if not symbol_raw or not exchange_raw:
            # Use the calculated row_number in logs
            logger.warning(
                f"Row {row_number}: Missing 'ticker' or 'exchange'. Skipping row: {row_data}"
            )
            continue

        # Use the cleaned symbol/exchange for processing
        symbol: str = symbol_raw
        exchange: str = exchange_raw

        # --- Validate and Import Stock First ---

        # Check if stock has already been validated
        stock_key = (symbol.upper(), exchange.upper())
        stock: Stock | None = validated_stocks.get(stock_key)

        # If not validated, validate
        if not stock:
            logger.info(f"Row {row_number}: Validating stock {symbol}.{exchange}...")
            stock = import_valid_stocks(symbol, exchange, stock_repo, session)
            # If successful, ensure 'stock' variable holds the Stock object with its ID
            if stock:
                validated_stocks[(stock.ticker, stock.exchange)] = stock  # Cache it
            else:
                logger.warning(
                    f"Row {row_number}: Could not validate stock for {symbol}.{exchange}. Skipping order."
                )
                continue  # Skip order if stock validation failed

        # --- Parse and Validate Order Data from CSV ---
        try:
            # Use dedicated parsing functions, accessing data from row_data
            purchase_dt: datetime = parse_csv_datetime(row_data.get("datetime", ""))
            quantity: float = parse_csv_quantity(row_data.get("quantity", ""))
            price_paid: float = parse_csv_price_paid(row_data.get("price_paid", ""))
            fee: float = parse_csv_fee(row_data.get("fee", "0.0"))
            # note already handled

            if not stock.id:
                raise ValueError("Stock {stock.name} is missing its ID value.")

            # --- Create and Insert StockOrder ---
            order: StockOrder = StockOrder(
                id=None,
                stock_id=stock.id,  # Use the ID from the validated Stock object
                purchase_datetime=purchase_dt,
                quantity=quantity,
                price_paid=price_paid,
                fee=fee,
                note=note,
            )

            _ = order_repo.insert(order)
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

    logger.info(
        f"Finished importing orders. Successfully imported {inserted_orders} orders from {csv_path}"
    )
