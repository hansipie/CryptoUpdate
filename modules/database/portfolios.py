"""Portfolio management module.

This module handles cryptocurrency portfolios including:
- Portfolio creation and deletion
- Token balances tracking
- Portfolio aggregation and analysis
"""

import logging
import sqlite3

logging.getLogger("matplotlib").setLevel(logging.WARNING)
logging.getLogger("PIL").setLevel(logging.WARNING)
logging.getLogger("modules.process").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


class Portfolios:
    def __init__(self, db_path: str):
        self.db_path = db_path

        # Créer les tables si elles n'existent pas
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS Portfolios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    bundle INTEGER NOT NULL DEFAULT 0
                )
            """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS Portfolios_Tokens (
                    portfolio_id INTEGER,
                    token TEXT,
                    amount TEXT,
                    PRIMARY KEY (portfolio_id, token),
                    FOREIGN KEY (portfolio_id) REFERENCES Portfolios(id)
                )
            """
            )
            conn.commit()

    def get_portfolio_names(self) -> list:
        logger.debug("Getting portfolios from database")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM Portfolios")
            # return sorted list of portfolios
            portfolio_names = [row[0] for row in cursor.fetchall()]
            logger.debug(f"Getting portfolios from database {portfolio_names}")
            portfolio_names.sort()
            return portfolio_names

    def get_portfolio(self, name: str) -> dict:
        logger.debug(f"Getting portfolio {name} from database")
        with sqlite3.connect(self.db_path) as conn:
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
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO Portfolios (name, bundle) VALUES (?, ?)", (name, bundle)
            )
            conn.commit()

    def delete_portfolio(self, name: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Portfolios WHERE name = ?", (name,))
            conn.commit()

    def rename_portfolio(self, old_name: str, new_name: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE Portfolios SET name = ? WHERE name = ?", (new_name, old_name)
            )
            conn.commit()

    def get_tokens(self, name: str) -> dict:
        with sqlite3.connect(self.db_path) as conn:
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
        with sqlite3.connect(self.db_path) as conn:
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
        with sqlite3.connect(self.db_path) as conn:
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
                (portfolio_name, token, str(amount)),
            )

    def set_token_add(self, name: str, token: str, amount: float):
        # add amout to the amount of an existing token in portfolio
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT token, amount FROM Portfolios_Tokens
                JOIN Portfolios ON Portfolios_Tokens.portfolio_id = Portfolios.id
                WHERE Portfolios.name = ? AND Portfolios_Tokens.token = ?
            """,
                (name, token),
            )
            row = cursor.fetchone()
            if row:
                new_amount = float(row[1]) + amount
                cursor.execute(
                    """
                    UPDATE Portfolios_Tokens
                    SET amount = ?
                    WHERE portfolio_id = (SELECT id FROM Portfolios WHERE name = ?) AND token = ?
                """,
                    (str(new_amount), name, token),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO Portfolios_Tokens (portfolio_id, token, amount)
                    VALUES (
                        (SELECT id FROM Portfolios WHERE name = ?),
                        ?,
                        ?
                    )
                """,
                    (name, token, str(amount)),
                )
            conn.commit()

    def delete_token_a(self, name: str, token: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM Portfolios_Tokens
                WHERE portfolio_id = (SELECT id FROM Portfolios WHERE name = ?) AND token = ?
            """,
                (name, token),
            )
            conn.commit()

    def delete_token_b(self, portfolio_id: int, token: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM Portfolios_Tokens WHERE portfolio_id = ? AND token = ?",
                (portfolio_id, token),
            )
            conn.commit()

    def aggregate_portfolios(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
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
