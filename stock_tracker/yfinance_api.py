import logging

import yfinance as yf

logger: logging.Logger = logging.getLogger(__name__)


def get_stock_price(ticker: str, exchange: str | None = None) -> float:
    """
    Retrieves the latest stock price for a given symbol using the Alpha Vantage API.
    Returns a tuple: (price: float or None, error: str or None).
    """
    # TODO: Specify the currency, and convert it if necessary
    # TODO: Ensure can hangle stocks with the same ticker, that are listed in different exchanges
    try:
        logger.debug(f"Checking {ticker} price in exchange: {exchange}.")
        full_ticker: str = f"{ticker}.{exchange}" if exchange else ticker
        data: yf.Ticker = yf.Ticker(full_ticker)

        last_price = data.fast_info.last_price
        if last_price is not None:
            logger.debug(f"{ticker} price is: {last_price}.")
            return float(last_price)
        raise ValueError(f"No price found for {full_ticker}")
    except Exception as e:
        raise ValueError(f"Failed to retrieve price for {ticker} at {exchange}: {e}")
