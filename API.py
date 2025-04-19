# pyright: ignore[reportUnsafeMultipleInheritance, reportIncompatibleMethodOverride]
import logging

import requests

import yfinance as yf
from typing import Any
from requests import Response, Session
from requests_cache import CacheMixin, SQLiteCache
from requests_ratelimiter import LimiterMixin, MemoryQueueBucket
from pyrate_limiter import Duration, RequestRate, Limiter


# # Set up logging
# logger: logging.Logger = logging.getLogger(name="yfinance_session")
# logger.setLevel(level=logging.DEBUG)  # You can change this to INFO in production
#
# # Add a default console handler if none exist
# if not logger.hasHandlers():
#     handler: logging.StreamHandler[TextIO] = logging.StreamHandler()
#     formatter: logging.Formatter = logging.Formatter(
#         fmt="[%(asctime)s] %(levelname)s - %(message)s"
#     )
#     handler.setFormatter(fmt=formatter)
#     logger.addHandler(hdlr=handler)
#
#
# class LoggingBucket(MemoryQueueBucket):
#     """
#     Custom bucket class that logs when a request is being throttled.
#     """
#
#     def get_wait_time(self, context: RequestContext) -> float:
#         wait_time = super(LoggingBucket, self).get_wait_time(context)
#         if wait_time > 0:
#             logger.debug(
#                 msg=f"Throttling: Delaying request for {wait_time:.2f} seconds due to rate limits."
#             )
#         return wait_time
#


class CachedLimiterSession(CacheMixin, LimiterMixin, Session):
    pass


def get_yfinance_session(
    *,
    cache_path: str = "yfinance.cache",
    requests_per_window: int = 2,
    window_seconds: int = 5,
) -> CachedLimiterSession:
    """
    Returns a requests.Session with built-in caching and rate limiting,
    ready to be passed to yfinance API calls.

    :param cache_path: File path for SQLite cache
    :param requests_per_window: Number of requests allowed per window
    :param window_seconds: Length of rate limit window in seconds
    :return: Configured CachedLimiterSession
    """
    rate: RequestRate = RequestRate(
        limit=requests_per_window, interval=Duration.SECOND * window_seconds
    )
    limiter: Limiter = Limiter(rate)

    return CachedLimiterSession(
        limiter=limiter,
        bucket_class=MemoryQueueBucket,
        backend=SQLiteCache(db_path=cache_path),
    )


def get_symbol_for_exchange(
    query: str,
    preferred_exchange: str,
    session: CachedLimiterSession,
    region: str = "US",
    lang: str = "en",
    return_ticker: bool = False,
) -> tuple[str | yf.Ticker | None, str | None]:
    """
    Search Yahoo Finance and return the symbol for a specific exchange (e.g. ASX, NYQ, NAS).

    :param query: Ticker or name (e.g., "IVV", "Apple")
    :param preferred_exchange: Target exchange (e.g., "ASX", "NAS", "NYQ")
    :param session: configured CachedLimiterSession
    :param region: Region for Yahoo query
    :param lang: Language
    :param return_ticker: If True, return yfinance.Ticker instead of symbol string
    :return: Matching symbol or yfinance.Ticker (or None if not found)
    """
    url = "https://query2.finance.yahoo.com/v1/finance/search"
    params: dict[str, str | int] = {
        "q": query,
        "lang": lang,
        "region": region,
        "quotesCount": 10,
        "newsCount": 0,
    }

    try:
        response: Response = requests.get(url, params=params)
        response.raise_for_status()
        results: Any = response.json().get("quotes", [])

        preferred: dict[str, str] | None = next(
            (r for r in results if r.get("exchange") == preferred_exchange), None
        )
        fallback: dict[str, str] | None = results[0] if results else None

        symbol: str | None = (
            preferred.get("symbol")
            if preferred
            else fallback.get("symbol")
            if fallback
            else None
        )

        if not symbol:
            return None, f"No match found for '{query}'."

        return (
            (yf.Ticker(ticker=symbol, session=session), None)
            if return_ticker
            else (symbol, None)
        )

    except requests.RequestException as e:
        return None, f"Error during Yahoo Finance search: {e}"
