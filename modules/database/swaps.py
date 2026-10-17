"""Swap operations management module.

This module handles cryptocurrency swap operations including:
- Token exchange tracking
- Swap history management
- Cross-rate calculations
"""

import logging
import sqlite3

from modules.database.portfolios import add_token_amount, transaction

logger = logging.getLogger(__name__)


class Swaps:
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
                    amount_from REAL,
                    wallet_from TEXT,
                    token_to TEXT,
                    amount_to REAL,
                    wallet_to TEXT,
                    tag TEXT,
                    note TEXT,
                    portfolio_adjusted INTEGER NOT NULL DEFAULT 0
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
                SELECT id, timestamp, token_from, amount_from, wallet_from, token_to, amount_to, wallet_to, tag, note
                FROM Swaps ORDER BY timestamp DESC
            """
            )
            return cursor.fetchall()

    def get_by_tag(self, tag: str) -> list:
        logger.debug("Getting swaps by tag")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            _sql = (
                "SELECT id, timestamp, token_from, amount_from, wallet_from,"
                " token_to, amount_to, wallet_to, tag, note FROM Swaps"
            )
            if not tag:
                cursor.execute(f"{_sql} WHERE tag IS NULL ORDER BY timestamp DESC")
            else:
                cursor.execute(
                    f"{_sql} WHERE tag = ? ORDER BY timestamp DESC",
                    (tag,),
                )
            return cursor.fetchall()

    @staticmethod
    def _insert(
        conn: sqlite3.Connection,
        timestamp,
        token_from,
        amount_from,
        wallet_from,
        token_to,
        amount_to,
        wallet_to,
        note,
        portfolio_adjusted: bool,
    ) -> None:
        """Insert a swap (and move the amounts between wallets if adjusted)."""
        conn.execute(
            "INSERT INTO Swaps"
            " (timestamp, token_from, amount_from, wallet_from,"
            " token_to, amount_to, wallet_to, tag, note, portfolio_adjusted)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                timestamp,
                token_from,
                amount_from,
                wallet_from,
                token_to,
                amount_to,
                wallet_to,
                None,
                note or None,
                int(portfolio_adjusted),
            ),
        )
        if portfolio_adjusted:
            add_token_amount(conn, wallet_from, token_from, -amount_from)
            add_token_amount(conn, wallet_to, token_to, amount_to)

    def insert(
        self,
        timestamp,
        token_from,
        amount_from,
        wallet_from,
        token_to,
        amount_to,
        wallet_to,
        note: str = None,
        portfolio_adjusted: bool = False,
    ):
        """Insert a swap; if portfolio_adjusted, move the amounts between wallets.

        The row, its flag and both holdings changes are one transaction.
        """
        logger.debug("Inserting swap")
        with transaction(self.db_path) as conn:
            self._insert(
                conn,
                timestamp,
                token_from,
                amount_from,
                wallet_from,
                token_to,
                amount_to,
                wallet_to,
                note,
                portfolio_adjusted,
            )
        logger.debug("Swap inserted")

    def replace(
        self,
        entry_id,
        timestamp,
        token_from,
        amount_from,
        wallet_from,
        token_to,
        amount_to,
        wallet_to,
        note: str = None,
        portfolio_adjusted: bool = False,
    ):
        """Edit a swap: undo the old effect (if it was applied), insert the new.

        Everything happens in one transaction: a failure leaves the old swap
        and the holdings untouched.
        """
        with transaction(self.db_path) as conn:
            row = conn.execute(
                "SELECT token_from, amount_from, wallet_from, token_to, amount_to,"
                " wallet_to, portfolio_adjusted FROM Swaps WHERE id = ?",
                (entry_id,),
            ).fetchone()
            if row is not None:
                old_tf, old_af, old_wf, old_tt, old_at, old_wt, adjusted = row
                if adjusted:
                    add_token_amount(conn, old_wf, old_tf, float(old_af))
                    add_token_amount(conn, old_wt, old_tt, -float(old_at))
                conn.execute("DELETE FROM Swaps WHERE id = ?", (entry_id,))
            self._insert(
                conn,
                timestamp,
                token_from,
                amount_from,
                wallet_from,
                token_to,
                amount_to,
                wallet_to,
                note,
                portfolio_adjusted,
            )

    def is_portfolio_adjusted(self, entry_id: int) -> bool:
        """Return True if the swap was applied to the portfolios holdings."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT portfolio_adjusted FROM Swaps WHERE id = ?", (entry_id,)
            ).fetchone()
        return bool(row and row[0])

    def delete(self, entry_id: int):
        logger.debug("Deleting swap")
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM Swaps WHERE id = ?", (entry_id,))
                conn.commit()
                logger.debug("Entry with id %s deleted successfully.", entry_id)
        except Exception as e:
            logger.exception("Error deleting swap: %s", e)

    def update_note(self, entry_id: int, note: str):
        logger.debug("Updating swap note")
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE Swaps SET note = ? WHERE id = ?", (note or None, entry_id)
                )
                conn.commit()
                logger.debug("Note updated for entry with id %s", entry_id)
        except Exception as e:
            logger.exception("Error updating note: %s", e)

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
                logger.debug("Tag updated for entry with id %s", entry_id)
        except Exception as e:
            logger.exception("Error updating tag: %s", e)
