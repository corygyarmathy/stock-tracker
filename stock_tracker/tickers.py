# pyright: ignore[reportUnsafeMultipleInheritance, reportIncompatibleMethodOverride]
import logging
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf

from stock_tracker.config import AppConfig
from stock_tracker.db import Database
from stock_tracker.yfinance_api import CachedLimiterSession

logger: logging.Logger = logging.getLogger(__name__)


def is_valid_ticker(symbol: str, exchange: str, session: CachedLimiterSession) -> yf.Ticker | None:
    full_symbol: str = f"{symbol}.{exchange}"
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
        result = yf.Search(
            ticker, max_results=20, news_count=0, lists_count=0, session=session
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
            if not choice:
                return None
            choice = int(choice)
            if 1 <= choice <= len(results):
                return results[choice - 1]
            else:
                print(f"Please enter a number between 1 and {len(results)}.")
        except ValueError:
            print("Invalid input. Enter a number.")


def import_valid_tickers(csv_path: str, db_path: str, session: CachedLimiterSession):
    init_db(db_path)
    df = pd.read_csv(csv_path)
    inserted = 0

    for _, row in df.iterrows():
        ticker = str(row["ticker"]).strip()
        exchange = str(row["exchange"]).strip()
        full_symbol = f"{ticker}.{exchange}"

        if is_valid_ticker(ticker, exchange, session):
            if save_ticker(db_path, ticker, exchange, full_symbol):
                inserted += 1
                logger.info(f"Inserted {full_symbol}")
            continue

        logger.warning(f"Invalid ticker: {full_symbol}. Searching for alternatives...")
        results = search_ticker_quotes(ticker, session)
        match = prompt_user_to_select(results)

        if match:
            symbol = match["symbol"]
            exch = match.get("exchange", "N/A")
            logger.info(f"User selected: {symbol} on {exch}")

            if save_ticker(db_path, symbol, exch, f"{symbol}.{exch}"):
                inserted += 1
                logger.info(f"Inserted corrected: {symbol}.{exch}")
        else:
            logger.warning(f"Skipped: {ticker}.{exchange}")

    logger.info(f"Imported {inserted} tickers from {csv_path}")
