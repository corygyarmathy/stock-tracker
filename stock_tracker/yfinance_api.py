from pyrate_limiter import Duration, Limiter, RequestRate
from requests import Session
from requests_cache import CacheMixin, SQLiteCache
from requests_ratelimiter import LimiterMixin, MemoryQueueBucket


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
