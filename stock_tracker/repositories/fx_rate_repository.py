from datetime import date, datetime
from sqlite3 import Cursor, Row
from stock_tracker.db import Database
from stock_tracker.models import FxRate
from stock_tracker.utils.model_utils import ModelFactory


class FxRateRepository:
    def __init__(self, db: Database):
        self.db: Database = db

    def insert(self, fx_rate: FxRate) -> None:
        _ = self.db.execute(
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

    def get_rate(self, base_currency: str, target_currency: str, date: date) -> FxRate | None:
        row: Row | None = self.db.query_one(
            "SELECT * FROM fx_rates WHERE base_currency = ? AND target_currency = ? AND date = ?",
            (base_currency, target_currency, date),
        )
        if not row:
            return None
        return ModelFactory.create_from_row(FxRate, row)
