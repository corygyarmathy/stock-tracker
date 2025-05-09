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
