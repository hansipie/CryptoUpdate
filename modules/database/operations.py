"""Operations management module.

This module handles cryptocurrency operations including:
- Buy and sell transactions
- Operation history tracking
- Performance calculations
"""

import logging
import sqlite3

logger = logging.getLogger(__name__)


class operations:
    def __init__(self, db_path: str):
        self.db_path = db_path

        # Créer les tables si elles n'existent pas
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS Operations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL, 
                    source FLOAT NOT NULL, 
                    destination FLOAT NOT NULL, 
                    source_unit TEXT NOT NULL, 
                    destination_unit TEXT NOT NULL,
                    timestamp INTEGERT NOT NULL,
                    portfolio TEXT
                )
            """
            )
            conn.commit()

    def insert(
        self,
        type,
        source,
        destination,
        source_unit,
        destination_unit,
        timestamp,
        portfolio,
    ):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO Operations (type, source, destination, source_unit, destination_unit, timestamp, portfolio)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    type,
                    source,
                    destination,
                    source_unit,
                    destination_unit,
                    timestamp,
                    portfolio,
                ),
            )
            conn.commit()

    def delete(self, item_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Operations WHERE id = ?", (item_id,))
            conn.commit()

    def get_operations(self) -> list:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Operations")
            return cursor.fetchall()

    def get_operations_by_type(self, op_type: str) -> list:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM Operations WHERE type = ? ORDER BY timestamp DESC",
                (op_type,),
            )
            return cursor.fetchall()

    def sum_buyoperations(self) -> float:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT SUM(source) FROM Operations WHERE type = 'buy'")
            ret = cursor.fetchone()[0]
            if ret is None:
                return 0
            return ret

    def get_averages(self) -> list:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT destination_unit, SUM(source), source_unit, SUM(destination) FROM Operations WHERE type = 'buy' GROUP BY destination_unit, source_unit"
            )
            return cursor.fetchall()
