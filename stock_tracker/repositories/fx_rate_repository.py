from sqlite3 import Cursor
from stock_tracker.db import Database
from stock_tracker.models import FxRate


class FxRateRepository:
    def __init__(self, db: Database):
        self.db = db

    def insert(self, fx_rate: FxRate) -> None:
        cursor: Cursor = self.db.execute(
            """
            INSERT INTO fx_rates (base_currency, target_currency, date, rate)
            VALUES (:base_currency, :target_currency, :date, :rate)
            """,
            {
                "base_currency": fx_rate.base_currency,
                "target_currency": fx_rate.target_currency,
                "date": fx_rate.date,
                "rate": fx_rate.rate,
            },
        )

    def get_rate(self, base_currency: str, target_currency: str, date: str) -> FxRate | None:
        row = self.db.query_one(
            "SELECT id, base_currency, target_currency, date, rate FROM fx_rates WHERE base_currency = ? AND target_currency = ? AND date = ?",
            (base_currency, target_currency, date),
        )
        return FxRate(**row) if row else None
