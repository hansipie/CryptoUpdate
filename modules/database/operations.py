"""Operations management module.

This module handles cryptocurrency operations including:
- Buy and sell transactions
- Airdrop operations (buy with source = 0)
- Operation history tracking
- Performance calculations

IMPORTANT: Operations with source = 0 are VALID and represent token airdrops.
These are legitimate operations where tokens are received without monetary cost.
Do NOT delete or flag these as invalid.
"""

import logging
import sqlite3

from modules.utils import db_connect

from modules.database.portfolios import add_token_amount, transaction

logger = logging.getLogger(__name__)


class Operations:
    def __init__(self, db_path: str):
        self.db_path = db_path

        # Créer les tables si elles n'existent pas
        with db_connect(self.db_path) as conn:
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
                    timestamp INTEGER NOT NULL,
                    portfolio TEXT,
                    portfolio_adjusted INTEGER NOT NULL DEFAULT 0
                )
            """
            )
            conn.commit()

    @staticmethod
    def _insert(
        conn: sqlite3.Connection,
        op_type,
        source,
        destination,
        source_unit,
        destination_unit,
        timestamp,
        portfolio,
        portfolio_adjusted: bool,
    ) -> None:
        """Insert an operation (and credit the portfolio if adjusted) on `conn`."""
        conn.execute(
            """
            INSERT INTO Operations (type, source, destination, source_unit, destination_unit, timestamp, portfolio, portfolio_adjusted)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                op_type,
                source,
                destination,
                source_unit,
                destination_unit,
                timestamp,
                portfolio,
                int(portfolio_adjusted),
            ),
        )
        if portfolio_adjusted:
            add_token_amount(conn, portfolio, destination_unit, destination)

    @staticmethod
    def _delete(conn: sqlite3.Connection, item_id, revert_portfolio: bool) -> bool:
        """Delete an operation (and debit the portfolio if asked) on `conn`.

        Returns:
            True if the operation was flagged as applied to the portfolios.
        """
        row = conn.execute(
            "SELECT portfolio, destination_unit, destination, portfolio_adjusted"
            " FROM Operations WHERE id = ?",
            (item_id,),
        ).fetchone()
        if row is None:
            return False
        portfolio, token, amount, adjusted = row
        if revert_portfolio:
            add_token_amount(conn, portfolio, token, -float(amount))
        conn.execute("DELETE FROM Operations WHERE id = ?", (item_id,))
        return bool(adjusted)

    def insert(
        self,
        op_type,
        source,
        destination,
        source_unit,
        destination_unit,
        timestamp,
        portfolio,
        portfolio_adjusted: bool = False,
    ):
        """Insert an operation; if portfolio_adjusted, credit the portfolio too.

        The row, its flag and the holdings change are one transaction.
        """
        with transaction(self.db_path) as conn:
            self._insert(
                conn,
                op_type,
                source,
                destination,
                source_unit,
                destination_unit,
                timestamp,
                portfolio,
                portfolio_adjusted,
            )

    def replace(
        self,
        item_id,
        op_type,
        source,
        destination,
        source_unit,
        destination_unit,
        timestamp,
        portfolio,
        portfolio_adjusted: bool = False,
    ):
        """Edit an operation: undo the old effect (if it was applied), insert the new.

        Everything happens in one transaction: a failure leaves the old
        operation and the holdings untouched.
        """
        with transaction(self.db_path) as conn:
            self._delete(
                conn, item_id, revert_portfolio=self._was_adjusted(conn, item_id)
            )
            self._insert(
                conn,
                op_type,
                source,
                destination,
                source_unit,
                destination_unit,
                timestamp,
                portfolio,
                portfolio_adjusted,
            )

    @staticmethod
    def _was_adjusted(conn: sqlite3.Connection, item_id) -> bool:
        row = conn.execute(
            "SELECT portfolio_adjusted FROM Operations WHERE id = ?", (item_id,)
        ).fetchone()
        return bool(row and row[0])

    def is_portfolio_adjusted(self, item_id: int) -> bool:
        """Return True if the operation was applied to the portfolios holdings."""
        with db_connect(self.db_path) as conn:
            return self._was_adjusted(conn, item_id)

    def delete(self, item_id, revert_portfolio: bool = False):
        """Delete an operation; if revert_portfolio, debit the bought amount too."""
        with transaction(self.db_path) as conn:
            self._delete(conn, item_id, revert_portfolio)

    def get_operations(self) -> list:
        with db_connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Operations")
            return cursor.fetchall()

    def get_operations_by_type(self, op_type: str) -> list:
        with db_connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, type, source, destination, source_unit, destination_unit,"
                " timestamp, portfolio FROM Operations"
                " WHERE type = ? ORDER BY timestamp DESC",
                (op_type,),
            )
            return cursor.fetchall()

    def sum_buyoperations(self) -> float:
        with db_connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT SUM(source) FROM Operations WHERE type = 'buy'")
            ret = cursor.fetchone()[0]
            if ret is None:
                return 0
            return ret

    def sum_buyoperations_by_unit(self) -> dict:
        """Total invested per source currency (ex: {"EUR": 1200.0, "USD": 300.0})."""
        with db_connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT source_unit, SUM(source) FROM Operations "
                "WHERE type = 'buy' GROUP BY source_unit"
            )
            return {unit: total or 0 for unit, total in cursor.fetchall()}

    def get_averages(self) -> list:
        with db_connect(self.db_path) as conn:
            cursor = conn.cursor()
            query = (
                "SELECT destination_unit, SUM(source), source_unit, SUM(destination) "
                "FROM Operations WHERE type = 'buy' "
                "GROUP BY destination_unit, source_unit"
            )
            cursor.execute(query)
            return cursor.fetchall()
