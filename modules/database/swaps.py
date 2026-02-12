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
    def __init__(self, db_path: str):
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

    def get_by_tag(self, tag: str) -> list:
        logger.debug("Getting swaps by tag")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if not tag:
                cursor.execute(
                    """
                    SELECT id, timestamp, token_from, amount_from, wallet_from, token_to, amount_to, wallet_to, tag
                    FROM Swaps WHERE tag IS NULL ORDER BY timestamp DESC
                    """
                )
            else:
                cursor.execute(
                    """
                    SELECT id, timestamp, token_from, amount_from, wallet_from, token_to, amount_to, wallet_to, tag
                    FROM Swaps WHERE tag = ? ORDER BY timestamp DESC
                    """,
                    (tag,),
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
                cursor.execute("DELETE FROM Swaps WHERE id = ?", (entry_id,))
                conn.commit()
                logger.debug(f"Entry with id {entry_id} deleted successfully.")
        except Exception as e:
            logger.error(f"Error deleting swap: {e}")
            traceback.print_exc()

    def update_tag(self, entry_id: int, tag: str):
        logger.debug("Updating swap tag")
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if not tag:
                    cursor.execute(
                        "UPDATE Swaps SET tag = NULL WHERE id = ?", (entry_id,)
                    )
                else:
                    cursor.execute(
                        "UPDATE Swaps SET tag = ? WHERE id = ?", (tag, entry_id)
                    )
                conn.commit()
                logger.debug(f"Tag updated for entry with id {entry_id}")
        except Exception as e:
            logger.error(f"Error updating tag: {e}")
            traceback.print_exc()
