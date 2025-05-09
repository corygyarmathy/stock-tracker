# models.py
from dataclasses import dataclass
from datetime import datetime


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
    id: int | None
    last_updated: datetime
    current_price: float
    market_cap: float
    pe_ratio: float
    dividend_yield: float
    stock_id: int


@dataclass
class CorporateActions:
    id: int | None
    stock_id: int
    action_type: str
    action_date: datetime
    ratio: float
    target_stock_id: int  # For mergers/acquisitions


@dataclass
class FxRates:
    base_currency: str
    target_currency: str
    date: datetime
    rate: float
