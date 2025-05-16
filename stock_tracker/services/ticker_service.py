import logging
from datetime import datetime

import yfinance as yf

from stock_tracker.models import Stock, StockInfo
from stock_tracker.yfinance_api import get_valid_ticker

logger: logging.Logger = logging.getLogger(__name__)


class TickerService:
    """Service for extracting domain models from yfinance.Ticker objects."""

    # TODO: expand this to extract the remaining models.
    # Will implement this as needed: don't want to over-complicate now.
    @staticmethod
    def extract_models(ticker: yf.Ticker) -> tuple[Stock, StockInfo]:
        """
        Extract both Stock and StockInfo models from a single yfinance.Ticker object.

        Args:
            ticker: A validated yfinance.Ticker object

        Returns:
            Tuple containing (Stock, StockInfo) objects
        """
        # Extract Stock data
        stock: Stock = TickerService.extract_stock(ticker)

        # Extract StockInfo data
        stock_info: StockInfo = TickerService.extract_stock_info(ticker)

        return stock, stock_info

    @staticmethod
    def extract_stock(ticker: yf.Ticker) -> Stock:
        """Extract Stock model from yfinance.Ticker."""
        info = ticker.info
        ticker_str: str = str(ticker.ticker)

        symbol = info.get("symbol")
        exchange = info.get("exchange")
        currency = info.get("currency")
        name = info.get("shortName") or info.get("longName")

        if not symbol or not isinstance(symbol, str):
            logger.error(f"YF info missing symbol for {ticker.ticker}: {info.get('symbol')}")
            raise ValueError("YF info missing symbol for {ticker.ticker}: {info.get('symbol')}")
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

        currency = "USD"  # Or handle this as an error if currency is mandatory
        return Stock(
            id=None,
            ticker=symbol.upper(),
            exchange=exchange,
            currency=currency.upper(),
            name=name,
            yfinance_ticker=ticker_str,
        )

    @staticmethod
    def extract_stock_info(ticker: yf.Ticker) -> StockInfo:
        """Extract StockInfo model from yfinance.Ticker."""
        current_price: float | None = ticker.fast_info.last_price

        # Get additional data from info dict
        info = ticker.info
        market_cap = info.get("marketCap", 0)
        pe_ratio = info.get("trailingPE", 0)
        dividend_yield = info.get("dividendYield", 0)

        if not current_price or not isinstance(current_price, float):
            logger.error(f"YF info missing current price for {ticker.ticker}.")
            raise ValueError(f"YF info missing current price for {ticker.ticker}.")

        # NOTE: stock_id will need to be set after the Stock is inserted
        return StockInfo(
            stock_id=-1,  # Temporary value, must be updated after Stock insert
            last_updated_datetime=datetime.now(),
            current_price=current_price,
            market_cap=market_cap,
            pe_ratio=pe_ratio,
            dividend_yield=dividend_yield,
        )

    @staticmethod
    def get_ticker_for_stock(stock: Stock) -> yf.Ticker | None:
        """
        Get a yfinance Ticker object for a stock using its validated ticker string.

        Args:
            stock: Stock object with a validated yfinance_ticker

        Returns:
            yfinance Ticker object or None if validation fails
        """
        if not stock.yfinance_ticker:
            # If we don't have a validated ticker string, try to validate
            logger.debug(f"No yfinance_ticker str for stock {stock.ticker}")
            ticker: yf.Ticker | None = get_valid_ticker(stock.ticker, stock.exchange)
            if ticker:
                # Update the stock with the validated ticker string for future use
                stock.yfinance_ticker = ticker.ticker
                return ticker
            logger.error(f"Failed to obtain valid yfinance_ticker str for stock {stock.ticker}")
            return None

        # Use the validated ticker string we already have
        return yf.Ticker(stock.yfinance_ticker)
