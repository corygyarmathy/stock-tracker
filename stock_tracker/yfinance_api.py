from collections import deque
import logging
import os
import time
from threading import Lock
from typing import Any

import yfinance as yf
from requests import PreparedRequest, Response
from requests_cache import CachedSession, MutableMapping
from requests_cache.models import AnyResponse  # Import this for the return type

logger: logging.Logger = logging.getLogger(__name__)
# Define types for send method parameters for clarity (optional, but good practice)
# These align with what 'requests' library uses.
Timeout = float, tuple[float, float] | None
Verify = bool | str | None
Cert = Any | tuple[Any, Any] | None  # Using Any for AnyStr placeholder if AnyStr not defined
Proxies = MutableMapping[str, str] | None


class RateLimiter:
    def __init__(self, max_requests: int, interval_seconds: float):
        if max_requests <= 0:
            raise ValueError("max_requests must be positive")
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")

        self.max_requests = max_requests
        self.interval = interval_seconds
        self.lock = Lock()
        self.timestamps: deque[float] = deque()
        logger.info(
            f"RateLimiter initialized: max_requests={max_requests}, interval_seconds={interval_seconds}s"
        )

    def wait(self) -> None:
        while True:  # Loop to re-check after waiting
            with self.lock:
                now = time.time()
                # Remove timestamps older than the interval window from the left (oldest)
                while self.timestamps and (now - self.timestamps[0] >= self.interval):
                    self.timestamps.popleft()

                if len(self.timestamps) < self.max_requests:
                    self.timestamps.append(now)
                    logger.debug(
                        f"RateLimiter: Request allowed. Current load: {len(self.timestamps)}/{self.max_requests} in last {self.interval:.2f}s."
                    )
                    return  # Allowed to proceed

                # If queue is full, calculate time to wait until the oldest request slot is free
                # self.timestamps[0] is the time of the k-th previous request (where k=max_requests)
                time_to_wait = (self.timestamps[0] + self.interval) - now

            if time_to_wait > 0:  # Ensure positive wait time
                logger.info(
                    f"RateLimiter: Hit limit ({len(self.timestamps)}/{self.max_requests}). Sleeping for {time_to_wait:.2f} seconds."
                )
                time.sleep(time_to_wait)
            # else: slot might be free now or wait_time was <=0, loop again to re-check under lock immediately


class RateLimitedCachedSession(CachedSession):
    def __init__(
        self,
        # requests-cache specific parameters (passed to super)
        cache_name: str = "yfinance_cache/http_cache",
        expire_after: int = 3600,
        backend: str | None = None,  # Default 'sqlite' if cache_name is path-like
        allowable_codes: tuple[int, ...] = (200,),
        allowable_methods: tuple[str, ...] = ("GET", "HEAD"),
        stale_if_error: bool | int | None = None,  # For requests-cache v1.x (bool or timedelta)
        old_data_on_error: bool = False,  # Simpler flag, often preferred over stale_if_error
        # RateLimiter specific parameters
        max_requests: int = 1,
        interval_seconds: float = 10.0,
        user_agent: str | None = None,
        **kwargs,  # Other CachedSession or underlying requests.Session kwargs
    ):
        # Initialize RateLimiter first
        self.rate_limiter = RateLimiter(max_requests, float(interval_seconds))

        _user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36"
        )

        # Ensure cache directory exists
        cache_dir = os.path.dirname(cache_name)
        if cache_dir and not os.path.exists(cache_dir):
            try:
                os.makedirs(cache_dir, exist_ok=True)
                logger.info(f"Created cache directory: {cache_dir}")
            except OSError as e:
                logger.error(f"Failed to create cache directory {cache_dir}: {e}")

        super().__init__(
            cache_name=cache_name,
            backend=backend or "sqlite",  # requests-cache often defaults based on cache_name
            expire_after=expire_after,
            allowable_codes=allowable_codes,
            allowable_methods=allowable_methods,
            stale_if_error=stale_if_error,
            old_data_on_error=old_data_on_error,
            **kwargs,
        )

        self.headers.update({"User-Agent": _user_agent})
        logger.info(
            f"RateLimitedCachedSession (Inheritance Model) initialized. "
            f"Rate: {max_requests} req / {interval_seconds:.2f}s. "
            f"Cache: '{self.cache.cache_name if hasattr(self, 'cache') and self.cache else cache_name}', Expires: {expire_after}s. "
        )

    # Override the send method with a signature compatible with CacheMixin/Session
    def send(
        self,
        request: PreparedRequest,
        stream: bool = False,
        timeout: Timeout = None,
        verify: Verify = True,  # Default in requests.Session
        cert: Cert = None,
        proxies: Proxies = None,
        **kwargs,  # Catches any other specific kwargs yfinance might pass
    ) -> AnyResponse:  # Return type must be AnyResponse
        is_cached_and_valid = False
        cache_key: str | None = None

        # Check cache only if not streaming and cache is available
        if not stream and hasattr(self, "cache") and self.cache is not None:
            try:
                cache_key = self.cache.create_key(request)  # create_key is on BaseCache

                # Check if the key exists and the response is not expired
                if self.cache.contains(key=cache_key):  # Use contains() instead of has_key()
                    cached_resp = self.cache.get_response(
                        key=cache_key
                    )  # Get potential CachedResponse

                    # A response exists and it's not considered expired by the cache logic
                    if (
                        cached_resp and not cached_resp.is_expired
                    ):  # Check .is_expired on the CachedResponse
                        is_cached_and_valid = True
                        logger.debug(
                            f"RateLimitedCachedSession.send: Valid cache entry found for {request.url}. Skipping rate limiter."
                        )
            except Exception as e:
                # Log error during cache check but proceed as if not cached
                logger.warning(
                    f"RateLimitedCachedSession.send: Error during cache check for {request.url}: {e}. Assuming not cached."
                )

        if not is_cached_and_valid:
            logger.debug(
                f"RateLimitedCachedSession.send: No valid cache for {request.url} or stream=True. Engaging rate limiter."
            )
            self.rate_limiter.wait()  # Apply rate limiting
            logger.info(
                f"RateLimitedCachedSession.send: Proceeding with request for: {request.url} (might be live or revalidated by super().send)."
            )

        # Call the parent's send method (CachedSession.send)
        # This will handle the actual HTTP request (if needed) AND caching.
        response: AnyResponse = super().send(
            request,
            stream=stream,
            timeout=timeout,
            verify=verify,
            cert=cert,
            proxies=proxies,
            **kwargs,
        )

        # Log if response came from cache (useful for verifying behavior)
        # The 'from_cache' attribute is specific to CachedResponse objects
        if getattr(response, "from_cache", False):
            logger.debug(
                f"RateLimitedCachedSession.send: Response for {request.url} (status: {response.status_code}) was served from cache by CachedSession."
            )
        else:
            logger.debug(
                f"RateLimitedCachedSession.send: Response for {request.url} (status: {response.status_code}) was a live fetch by CachedSession."
            )

        return response


def get_yfinance_session(
    *,
    cache_path: str = "yfinance_cache/http_cache",  # Default path for the cache file/db
    requests_per_window: int = 1,  # Drastically reduced
    window_seconds: int = 10,  # Significantly increased interval
    cache_expiry: int = 3600,  # 1 hour
    # You can pass other requests-cache specific args here too
    allowable_codes=(200,),  # Cache only successful responses by default
    old_data_on_error=False,  # Don't serve stale data on error by default
) -> RateLimitedCachedSession:
    """
    Returns a requests.Session with caching and rate limiting, suitable for yfinance.
    Inherits from requests_cache.CachedSession.
    """
    logger.info(
        f"Creating yfinance session (Inheritance): "
        f"Cache Path='{cache_path}', Rate={requests_per_window} req / {window_seconds}s, "
        f"Cache Expiry={cache_expiry}s"
    )

    return RateLimitedCachedSession(
        cache_name=cache_path,  # Passed as cache_name to CachedSession
        expire_after=cache_expiry,  # Passed as expire_after to CachedSession
        max_requests=requests_per_window,
        interval_seconds=float(window_seconds),  # Ensure float for RateLimiter
        # Pass other CachedSession arguments if needed
        allowable_codes=allowable_codes,
        old_data_on_error=old_data_on_error,
        # filter_fn=lambda r: True, # Example: cache all responses (not recommended for errors)
    )


def get_stock_price(
    ticker: str, session: RateLimitedCachedSession, exchange: str | None = None
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
