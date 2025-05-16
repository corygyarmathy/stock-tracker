import logging
from datetime import datetime, date

import yfinance as yf
import pandas as pd

from stock_tracker.models import Dividend, Stock
from stock_tracker.repositories.dividend_repository import DividendRepository
from stock_tracker.services.ticker_service import TickerService

logger = logging.getLogger(__name__)


class DividendService:
    """Service for fetching, updating, and managing dividend data."""

    def __init__(self, dividend_repository: DividendRepository):
        self.dividend_repo = dividend_repository

    def fetch_and_store_dividends(self, stock: Stock) -> list[Dividend]:
        """
        Fetch dividend history for a stock from yfinance and store in database.

        Args:
            stock: Stock model to fetch dividends for

        Returns:
            List of Dividend objects stored in the database
        """
        if not stock.id:
            raise ValueError(
                f"Cannot fetch dividends for stock without ID: {stock.ticker}.{stock.exchange}"
            )

        logger.info(f"Fetching dividend history for {stock.ticker}.{stock.exchange}")

        ticker: yf.Ticker | None = TickerService.get_ticker_for_stock(stock)

        if not ticker:
            logger.error(f"Failed to get valid ticker for {stock.ticker}.{stock.exchange}")
            return []

        try:
            dividends = ticker.dividends

            if dividends.empty:
                logger.info(f"No dividend history found for {ticker.ticker}")
                return []

            # Process and store each dividend
            stored_dividends = []
            for date_idx, amount in dividends.items():
                # yfinance doesn't provide payment dates, only ex-dates
                # Approximately set payment date to 15 days after ex-date
                ex_date = date_idx.date()
                payment_date = self._estimate_payment_date(ex_date)

                # Create Dividend object
                dividend = Dividend(
                    id=None,
                    stock_id=stock.id,
                    ex_date=ex_date,
                    payment_date=payment_date,
                    amount=float(amount),
                    currency=stock.currency,
                )

                # Check if this dividend already exists
                existing = self.dividend_repo.get_dividend_by_ex_date(stock.id, ex_date)
                if existing:
                    logger.debug(f"Dividend already exists for {ticker_str} on {ex_date}")
                    stored_dividends.append(existing)
                    continue

                # Store the new dividend
                dividend_id = self.dividend_repo.insert(dividend)
                dividend.id = dividend_id
                stored_dividends.append(dividend)

            logger.info(f"Stored {len(stored_dividends)} dividends for {ticker.ticker}")
            return stored_dividends

        except Exception as e:
            logger.error(f"Error fetching dividends for {ticker.ticker}: {e}")
            return []

    def calculate_dividends_for_order(
        self,
        stock_id: int,
        quantity: float,
        purchase_date: datetime,
        current_date: datetime | None = None,
    ) -> float:
        """
        Calculate dividends received for a specific order.

        Args:
            stock_id: ID of the stock
            quantity: Number of shares owned
            purchase_date: Date when shares were purchased
            current_date: End date for dividend calculation (defaults to today)

        Returns:
            Total dividends received for this order
        """
        if current_date is None:
            current_date = datetime.now()

        # Convert to date objects
        purchase_date_only = purchase_date.date()
        current_date_only = current_date.date()

        # Get all dividends for this stock in the date range
        dividends: list[Dividend] = self.dividend_repo.get_dividends_in_date_range(
            stock_id, purchase_date_only, current_date_only
        )

        # Calculate total dividends received
        total_dividends: float = 0.0
        for div in dividends:
            total_dividends += div.amount * quantity

        return total_dividends

    def _estimate_payment_date(self, ex_date: date) -> date:
        """
        Estimate payment date based on ex-date.

        In reality, this varies by company policy. A more accurate approach would
        be to fetch the actual payment dates from a financial data source.

        Args:
            ex_date: Dividend ex-date

        Returns:
            Estimated payment date
        """
        # Simple estimation: payment date is typically 2-4 weeks after ex-date
        # For simplicity, we'll use ex_date + 15 days
        from datetime import timedelta

        return ex_date + timedelta(days=15)
