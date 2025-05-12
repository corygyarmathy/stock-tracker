from datetime import datetime
from sqlite3 import Cursor, Row
from stock_tracker.db import Database
from stock_tracker.models import CorporateAction
from stock_tracker.utils.model_utils import ModelFactory


class CorporateActionRepository:
    def __init__(self, db: Database):
        self.db: Database = db

    def insert(self, action: CorporateAction) -> int:
        cursor: Cursor = self.db.execute(
            """
            INSERT INTO corporate_actions (stock_id, action_type, action_date, ratio, target_stock_id)
            VALUES (:stock_id, :action_type, :action_date, :ratio, :target_stock_id)
            """,
            {
                "stock_id": action.stock_id,
                "action_type": action.action_type,
                "action_date": action.action_date,
                "ratio": action.ratio,
                "target_stock_id": action.target_stock_id,
            },
        )
        action.id = cursor.lastrowid
        if action.id:
            return action.id
        else:
            raise ValueError(f"Failed to obtain id of corporate action after inserting into db.")

    def get_by_stock_id(self, stock_id: int) -> list[CorporateAction]:
        rows: list[Row] = self.db.query_all(
            "SELECT * FROM corporate_actions WHERE stock_id = ?",
            (stock_id,),
        )
        return ModelFactory.create_list_from_rows(CorporateAction, rows)
