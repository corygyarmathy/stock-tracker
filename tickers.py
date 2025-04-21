# pyright: ignore[reportUnsafeMultipleInheritance, reportIncompatibleMethodOverride]
import logging
import yfinance as yf
import pandas as pd
from requests import Session
from requests_cache import CacheMixin, SQLiteCache
from requests_ratelimiter import LimiterMixin, MemoryQueueBucket
from pyrate_limiter import Duration, RequestRate, Limiter
from yfinance.base import FastInfo

from db import save_ticker, init_db

logger = logging.getLogger("ticker_importer.tickers")


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


def is_valid_ticker(ticker: str, exchange: str, session: CachedLimiterSession) -> bool:
    full_symbol: str = f"{ticker}.{exchange}"
    try:
        info: FastInfo = yf.Ticker(full_symbol, session).fast_info
        price = info["last_price"]
        logger.debug(f"{full_symbol}: last_price = {price}")
        return isinstance(price, (float)) and price > 0
    except Exception as e:
        logger.error(f"Failed to validate {full_symbol}: {e}")
        return False


def search_ticker(ticker: str, session: CachedLimiterSession) -> yf.Search:
    # TODO: only return list / dict of stock tickers and corresponding exchanges

    # Example return of search['quotes']
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

    return yf.Search(
        ticker, max_results=8, news_count=0, lists_count=0, session=session
    )


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
        else:
            logger.warning(f"Invalid ticker: {full_symbol}")

    logger.info(f"Imported {inserted} tickers from {csv_path}")
