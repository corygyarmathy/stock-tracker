from datetime import datetime
import logging
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf

from stock_tracker.config import AppConfig
from stock_tracker.db import Database
from stock_tracker.models import Stock
from stock_tracker.yfinance_api import CachedLimiterSession

logger: logging.Logger = logging.getLogger(__name__)


def is_valid_ticker(symbol: str, exchange: str, session: CachedLimiterSession) -> yf.Ticker | None:
    full_symbol: str = f"{symbol}.{exchange}"
# --- CSV Parsing Functions  ---
def parse_csv_datetime(value: Any) -> datetime:
    """Parses a string from CSV into a datetime object."""
    if not isinstance(value, str):
        raise ValueError(f"Expected string for datetime, got {type(value)}")
    try:
        ticker: yf.Ticker = yf.Ticker(full_symbol, session)
        price: float | None = ticker.fast_info["last_price"]
        logger.debug(f"{full_symbol}: last_price = {price}")
        if isinstance(price, (float)) and price > 0:
            return ticker
        raise ValueError(f"Price value is invalid. Price: {price}")
    except Exception as e:
        logger.error(f"Failed to validate ticker: {full_symbol}. Error: {e}")
        return None
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


def search_ticker_quotes(ticker: str, session: CachedLimiterSession) -> list[dict[str, Any]]:
    # INFO: Example return of search['quotes']
    # 'exchange' str = 'BTS'
    # 'shortname' str = 'iShares Trust iShares S&P 500 B'
    # 'quoteType' str = 'ETF'
    # 'symbol' str = 'IVVW'
    # 'index' str = 'quotes'
    # 'score' float = 20006.0
    # 'typeDisp' str = 'ETF'
    # 'longname' str = 'iShares S&P 500 BuyWrite ETF'
    # 'exchDisp' str = 'BATS Trading'
    # 'isYahooFinance' bool = True

    try:
        logger.debug(f"Searching for  tickert which match: {ticker}")
        result: yf.Search = yf.Search(
            query=ticker, max_results=20, news_count=0, lists_count=0, session=session
        )
        return result.quotes
    except Exception as e:
        logger.error(f"Search failed for {ticker}: {e}")
        return []


def prompt_user_to_select(results: list[dict[str, Any]]) -> dict[str, Any] | None:
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


def save_ticker(ticker: yf.Ticker) -> None:
    db_path: Path = AppConfig.get().db_path
    logger.debug(f"Saving ticker {ticker.ticker}.{ticker.fast_info.exchange} into {db_path}")
    with Database(db_path) as db:
        _ = db.execute(
            query="INSERT INTO tickers (ticker, exchange) VALUES (?, ?)",
            params=(ticker.ticker, ticker.fast_info.exchange),
        )


def import_valid_tickers(csv_path: Path, session: CachedLimiterSession) -> None:
    df: pd.DataFrame = pd.read_csv(csv_path)
    inserted = 0

    for _, row in df.iterrows():
        symbol: str = str(row["ticker"]).strip()
        exchange: str = str(row["exchange"]).strip()
        full_symbol: str = f"{symbol}.{exchange}"
        ticker: yf.Ticker | None = is_valid_ticker(symbol, exchange, session)
        if not ticker:
            logger.warning(f"Invalid ticker: {full_symbol}. Searching for alternatives...")
            results = search_ticker_quotes(symbol, session)
            match = prompt_user_to_select(results)
            if match:
                ticker: yf.Ticker | None = is_valid_ticker(symbol, exchange, session)
            else:
                logger.warning(f"Skipped: {symbol}.{exchange}")
        if ticker:
            if save_ticker(ticker):
                inserted += 1
                logger.info(f"Inserted {full_symbol}")
            continue

    logger.info(f"Imported {inserted} tickers from {csv_path}")
