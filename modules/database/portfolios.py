import streamlit as st
import pandas as pd
import logging
import sqlite3
from modules.tools import get_current_price
from modules.utils import clean_price

logging.getLogger("matplotlib").setLevel(logging.WARNING)
logging.getLogger("PIL").setLevel(logging.WARNING)
logging.getLogger("modules.process").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


class Portfolios:
    def __init__(self, db_path: str = "./data/db.sqlite3"):
        self.db_path = db_path

        # Créer les tables si elles n'existent pas
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS Portfolios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL
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
            list = [row[0] for row in cursor.fetchall()]
            logger.debug(f"Getting portfolios from database {list}")
            list.sort()
            return list
        
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

    def add_portfolio(self, name: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Portfolios (name) VALUES (?)", (name,))
            conn.commit()

    def delete_portfolio(self, name: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Portfolios WHERE name = ?", (name,))
            conn.commit()


    def rename_portfolio(self, old_name: str, new_name: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE Portfolios SET name = ? WHERE name = ?", (new_name, old_name))
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

    def set_token(self, name: str, token: str, amount: float):
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
                (name, token, str(amount)),
            )


    def set_token_add(self, name: str, token: str, amount: float):
        #add amout to the amount of an existing token in portfolio
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


    def delete_token(self, name: str, token: str):
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


    def create_portfolio_dataframe(self, data: dict) -> pd.DataFrame:
        logger.debug(f"Create portfolio dataframe - Data: {data}")
        if not data:
            logger.debug("No data")
            return pd.DataFrame()
        df = pd.DataFrame(data).T
        df.index.name = "token"
        df["amount"] = df.apply(lambda row: clean_price(row["amount"]), axis=1)
        # Ajouter une colonne "Value" basée sur le cours actuel
        df["value(€)"] = df.apply(
            lambda row: round(
                clean_price(row["amount"]) * get_current_price(row.name), 2
            ),
            axis=1,
        )
        #sort df by token
        df = df.sort_index()
        return df

    def aggregate_portfolios(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT token, amount FROM Portfolios_Tokens
                JOIN Portfolios ON Portfolios_Tokens.portfolio_id = Portfolios.id
            """
            )
            data = cursor.fetchall()
            df = pd.DataFrame(data, columns=["token", "amount"])
            logger.debug(f"Aggregate portfolios - Data: \n{df}")
            df["amount"] = df.apply(lambda row: clean_price(row["amount"]), axis=1)
            return df.groupby("token").agg({"amount": "sum"}).to_dict(orient="index")
        
    def update_portfolio(self, input_data: dict):
        logger.debug(f"Update portfolio - Data: {input_data.items()}")
        for portfolio_name, tokens in input_data.items():
            logger.debug(f"Update portfolio - Name: {portfolio_name} - Tokens: {tokens.items()}")
            for token_name, token_details in tokens.items():
                self.set_token(portfolio_name, token_name, token_details["amount"])  
        return True