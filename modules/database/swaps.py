"""Swap operations management module.

This module handles cryptocurrency swap operations including:
- Token exchange tracking
- Swap history management
- Cross-rate calculations
"""

import logging
import sqlite3
import traceback

logger = logging.getLogger(__name__)


class swaps:
    def __init__(self, db_path: str = "./data/db.sqlite3"):
        logger.debug("Initializing swaps database")
        self.db_path = db_path

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS Swaps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER,
                    token_from TEXT,
                    amount_from TEXT, 
                    wallet_from TEXT,
                    token_to TEXT,
                    amount_to TEXT,
                    wallet_to TEXT, 
                    tag TEXT
                )
            """
            )
            conn.commit()

    def get(self) -> list:
        logger.debug("Getting swaps")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, timestamp, token_from, amount_from, wallet_from, token_to, amount_to, wallet_to, tag
                FROM Swaps ORDER BY timestamp DESC
            """
            )
            return cursor.fetchall()

    def insert(
        self,
        timestamp,
        token_from,
        amount_from,
        wallet_from,
        token_to,
        amount_to,
        wallet_to,
    ):
        logger.debug("Inserting swap")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO Swaps (timestamp, token_from, amount_from, wallet_from, token_to, amount_to, wallet_to, tag)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    timestamp,
                    token_from,
                    amount_from,
                    wallet_from,
                    token_to,
                    amount_to,
                    wallet_to,
                    None,
                ),
            )
            conn.commit()
            logger.debug("Swap inserted")

    def delete(self, entry_id: int):
        logger.debug("Deleting swap")
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f"DELETE FROM Swaps WHERE id = {entry_id}")
                conn.commit()
                logger.debug(f"Entry with id {entry_id} deleted successfully.")
        except Exception as e:
            logger.error(f"Error deleting swap: {e}")
            traceback.print_exc()
