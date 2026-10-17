"""Portfolio management module.

This module handles cryptocurrency portfolios including:
- Portfolio creation and deletion
- Token balances tracking
- Portfolio aggregation and analysis
"""

import logging
import sqlite3
from contextlib import contextmanager

from modules.utils import db_connect

logging.getLogger("matplotlib").setLevel(logging.WARNING)
logging.getLogger("PIL").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


@contextmanager
def transaction(db_path: str):
    """Open a connection in a single write transaction (BEGIN IMMEDIATE).

    Commits on success, rolls back on any exception and always closes the
    connection, so several writes on the same connection are all-or-nothing.
    """
    conn = sqlite3.connect(db_path, isolation_level=None, timeout=30)
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield conn
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()


def add_token_amount(conn: sqlite3.Connection, name: str, token: str, amount: float):
    """Add `amount` (may be negative) to a portfolio token, in an open transaction.

    The increment is done in SQL, so concurrent sessions cannot overwrite
    each other's update.

    Raises:
        ValueError: if the portfolio does not exist.
    """
    cursor = conn.execute(
        """
        INSERT INTO Portfolios_Tokens (portfolio_id, token, amount)
        SELECT id, ?, ? FROM Portfolios WHERE name = ?
        ON CONFLICT (portfolio_id, token)
        DO UPDATE SET amount = amount + excluded.amount
        """,
        (token, amount, name),
    )
    if cursor.rowcount == 0:
        raise ValueError(f"Portfolio '{name}' not found")


class Portfolios:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_portfolio_names(self) -> list:
        logger.debug("Getting portfolios from database")
        with db_connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM Portfolios")
            # return sorted list of portfolios
            portfolio_names = [row[0] for row in cursor.fetchall()]
            logger.debug("Getting portfolios from database %s", portfolio_names)
            portfolio_names.sort()
            return portfolio_names

    def get_portfolio(self, name: str) -> dict:
        logger.debug("Getting portfolio %s from database", name)
        with db_connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT token, amount FROM Portfolios_Tokens
                JOIN Portfolios ON Portfolios_Tokens.portfolio_id = Portfolios.id
                WHERE Portfolios.name = ?
            """,
                (name,),
            )
            return {row[0]: {"amount": row[1]} for row in cursor.fetchall()}

    def add_portfolio(self, name: str, bundle: int = 0):
        with db_connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO Portfolios (name, bundle) VALUES (?, ?)", (name, bundle)
            )
            conn.commit()

    def delete_portfolio(self, name: str):
        with db_connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Portfolios WHERE name = ?", (name,))
            conn.commit()

    def rename_portfolio(self, old_name: str, new_name: str):
        """Rename a portfolio and the references kept by name in Operations/Swaps."""
        with transaction(self.db_path) as conn:
            conn.execute(
                "UPDATE Portfolios SET name = ? WHERE name = ?", (new_name, old_name)
            )
            conn.execute(
                "UPDATE Operations SET portfolio = ? WHERE portfolio = ?",
                (new_name, old_name),
            )
            conn.execute(
                "UPDATE Swaps SET wallet_from = ? WHERE wallet_from = ?",
                (new_name, old_name),
            )
            conn.execute(
                "UPDATE Swaps SET wallet_to = ? WHERE wallet_to = ?",
                (new_name, old_name),
            )

    def get_tokens(self, name: str) -> dict:
        with db_connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT token, amount FROM Portfolios_Tokens
                JOIN Portfolios ON Portfolios_Tokens.portfolio_id = Portfolios.id
                WHERE Portfolios.name = ?
            """,
                (name,),
            )
            return {row[0]: row[1] for row in cursor.fetchall()}

    def get_token_by_portfolio(self, token: str) -> dict:
        with db_connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT name, amount FROM Portfolios_Tokens
                JOIN Portfolios ON Portfolios_Tokens.portfolio_id = Portfolios.id
                WHERE Portfolios_Tokens.token = ?
            """,
                (token,),
            )
            return {row[0]: row[1] for row in cursor.fetchall()}

    def set_token(self, portfolio_name: str, token: str, amount: float):
        with db_connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO Portfolios_Tokens (portfolio_id, token, amount)
                VALUES (
                    (SELECT id FROM Portfolios WHERE name = ?),
                    ?,
                    ?
                )
            """,
                (portfolio_name, token, amount),
            )

    def set_token_add(self, name: str, token: str, amount: float):
        """Add amount to the amount of a token in a portfolio (created if absent)."""
        with transaction(self.db_path) as conn:
            add_token_amount(conn, name, token, amount)

    def delete_token_by_name(self, name: str, token: str):
        with db_connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM Portfolios_Tokens
                WHERE portfolio_id = (SELECT id FROM Portfolios WHERE name = ?) AND token = ?
            """,
                (name, token),
            )
            conn.commit()

    def delete_token_by_id(self, portfolio_id: int, token: str):
        with db_connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM Portfolios_Tokens WHERE portfolio_id = ? AND token = ?",
                (portfolio_id, token),
            )
            conn.commit()

    def aggregate_portfolios(self) -> dict:
        with db_connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT token, SUM(amount) FROM Portfolios_Tokens
                JOIN Portfolios ON Portfolios_Tokens.portfolio_id = Portfolios.id
                GROUP BY token
            """
            )
            return {row[0]: row[1] for row in cursor.fetchall()}

    def update_portfolio(self, input_data: dict):
        """Update portfolio balances."""
        logger.debug("Update portfolio - Data: %s", input_data.items())
        for portfolio_name, tokens in input_data.items():
            logger.debug(
                "Update portfolio - Name: %s - Tokens: %s",
                portfolio_name,
                tokens.items(),
            )
            for token_name, token_details in tokens.items():
                self.set_token(portfolio_name, token_name, token_details["amount"])
        return True
