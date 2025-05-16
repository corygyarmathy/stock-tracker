# models.py
from dataclasses import dataclass
from datetime import datetime, date


@dataclass
class Stock:
    id: int | None
    ticker: str
    exchange: str
    currency: str
    name: str | None = None


@dataclass
class StockOrder:
    id: int | None
    stock_id: int
    purchase_datetime: datetime
    quantity: float
    price_paid: float
    fee: float = 0.0
    note: str | None = None


@dataclass
class StockInfo:
    stock_id: int
    last_updated_datetime: datetime
    current_price: float
    market_cap: float
    pe_ratio: float
    dividend_yield: float


@dataclass
class CorporateAction:
    id: int | None
    stock_id: int
    action_type: str
    action_date: date
    ratio: float
    target_stock_id: int  # For mergers/acquisitions


@dataclass
class FxRate:
    base_currency: str
    target_currency: str
    date: date
    rate: float


@dataclass
class StockPerformance:
    """
    Represents the performance metrics for a stock in the portfolio.
    """

    stock_id: int
    ticker: str
    exchange: str
    name: str
    total_shares: float
    total_cost: float  # Total cost basis including fees
    current_value: float
    capital_gain: float
    capital_gain_percentage: float
    dividends_received: float
    total_return: float  # Capital gains + dividends
    total_return_percentage: float


@dataclass
class Dividend:
    id: int | None
    stock_id: int
    ex_date: date
    payment_date: date
    amount: float
    currency: str


@dataclass
class PortfolioPerformance:
    """
    Represents the aggregated performance of the entire portfolio.
    """

    stocks: list[StockPerformance]
    total_cost: float
    current_value: float
    capital_gain: float
    capital_gain_percentage: float
    dividends_received: float
    total_return: float
    total_return_percentage: float
