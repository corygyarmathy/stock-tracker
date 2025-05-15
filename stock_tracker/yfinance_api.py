import logging
import random
import time
from typing import Any

import yfinance as yf

from stock_tracker.models import Stock

logger: logging.Logger = logging.getLogger(__name__)


def get_valid_ticker(
    symbol: str, exchange: str | None = None, max_retries: int = 3
) -> yf.Ticker | None:
    """
    Attempts to fetch a valid yfinance Ticker object with price data.

    Args:
        symbol: Stock symbol (e.g., "AAPL")
        exchange: Exchange code (e.g., "NASDAQ", "AX"). Can be None or empty for US stocks.
        max_retries: Maximum number of retry attempts for API calls

    Returns:
        A validated yf.Ticker object if successful, None otherwise
    """
    # TODO: Specify the currency, and convert it if necessary
    # TODO: Ensure can hangle stocks with the same ticker, that are listed in different exchanges

    # Try common US exchanges with symbol only first
    us_exchanges: list[str] = [
        "NASDAQ",
        "NYSE",
        "ARCA",
        "PCX",
    ]  # NYSE Arca may just be ARCA or blank
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
    potential_tickers: list[str] = list(dict.fromkeys(potential_tickers))

    for attempt_ticker_str in potential_tickers:
        logger.debug(f"Attempting to validate: {attempt_ticker_str}")
        retry_count = 0

        while retry_count <= max_retries:
            try:
                ticker_obj: yf.Ticker = yf.Ticker(ticker=attempt_ticker_str)

                try:
                    price: float | None = ticker_obj.fast_info.last_price

                    if price is not None and price > 0:
                        logger.info(
                            f"Successfully retrieved ticker {attempt_ticker_str}: Price={price}"
                        )
                        return ticker_obj
                except Exception as e:
                    logger.debug(f"Failed to get fast_info for {attempt_ticker_str}: {e}")

                # Increment retry counter
                retry_count += 1
                if retry_count > max_retries:
                    break

                # Exponential backoff with jitter
                wait_time: int = min(60, (2**retry_count) + (random.randint(0, 1000) / 1000))
                logger.warning(f"Retrying {attempt_ticker_str} in {wait_time:.2f} seconds")
                time.sleep(wait_time)

            except Exception as e:
                error_message: str = str(e).lower()

                if "no data found" in error_message or "404" in error_message:
                    logger.warning(f"Invalid ticker {attempt_ticker_str}: {e}")
                    break  # Try next format

                if "rate limit" in error_message or "too many requests" in error_message:
                    retry_count += 1
                    if retry_count > max_retries:
                        logger.error(f"Rate limit exceeded for {attempt_ticker_str}")
                        break

                    # Longer wait for rate limits
                    wait_time = min(120, (2**retry_count) + (random.randint(0, 1000) / 1000))
                    logger.warning(f"Rate limited. Waiting {wait_time:.2f}s before retry")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Error for {attempt_ticker_str}: {e}")
                    break


def search_ticker_quotes(ticker: str, max_retries: int = 3) -> list[dict[str, Any]]:
    """
    Search for ticker symbols in Yahoo Finance with retry mechanism.
    Uses yfinance's built-in session management.
    """
    retry_count = 0

    while retry_count <= max_retries:
        try:
            logger.debug(f"Searching for tickers which match: {ticker}")
            # Don't pass a custom session
            result: yf.Search = yf.Search(query=ticker, max_results=20, news_count=0, lists_count=0)
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
