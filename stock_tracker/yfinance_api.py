import logging

import yfinance as yf
from pyrate_limiter import Duration, Limiter, RequestRate
from requests import Session
from requests_cache import CacheMixin, SQLiteCache
from requests_ratelimiter import LimiterMixin, MemoryQueueBucket

logger: logging.Logger = logging.getLogger(__name__)


class CachedLimiterSession(CacheMixin, LimiterMixin, Session):
    pass


def get_yfinance_session(
    *,
    cache_path: str = "yfinance.cache",
    requests_per_window: int = 2,
    window_seconds: int = 5,
    cache_expiry: int = 3600,  # Default cache expiry of 1 hour
) -> CachedLimiterSession:
    """
    Returns a requests.Session with built-in caching and rate limiting,
    ready to be passed to yfinance API calls.

    :param cache_path: File path for SQLite cache
    :param requests_per_window: Number of requests allowed per window
    :param window_seconds: Length of rate limit window in seconds
    :param cache_expiry: How long to keep cached responses (in seconds)
    :return: Configured CachedLimiterSession
    """
    rate: RequestRate = RequestRate(
        limit=requests_per_window, interval=Duration.SECOND * window_seconds
    )
    limiter: Limiter = Limiter(rate)

    return CachedLimiterSession(
        limiter=limiter,
        bucket_class=MemoryQueueBucket,
        backend=SQLiteCache(db_path=cache_path, expire_after=cache_expiry),
    )


def get_stock_price(
    ticker: str, session: CachedLimiterSession, exchange: str | None = None
) -> float:
    """
    Retrieves the latest stock price for a given symbol using the Alpha Vantage API.
    Returns a tuple: (price: float or None, error: str or None).
    """
    # TODO: Specify the currency, and convert it if necessary
    # TODO: Ensure can hangle stocks with the same ticker, that are listed in different exchanges
    try:
        logger.debug(f"Checking {ticker} price in exchange: {exchange}.")
        full_ticker: str = f"{ticker}.{exchange}" if exchange else ticker
        data: yf.Ticker = yf.Ticker(full_ticker, session=session)

        last_price = data.fast_info.last_price
        if last_price is not None:
            logger.debug(f"{ticker} price is: {last_price}.")
            return float(last_price)
        raise ValueError(f"No price found for {full_ticker}")
    except Exception as e:
        raise ValueError(f"Failed to retrieve price for {ticker} at {exchange}: {e}")
