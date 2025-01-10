import logging
import sqlite3

logger = logging.getLogger(__name__)

class swaps:
    def __init__(self, db_path: str = "./data/db.sqlite3"):
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
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT timestamp, token_from, amount_from, wallet_from, token_to, amount_to, wallet_to, tag
                FROM Swaps
            """
            )
            return cursor.fetchall()
        
    def insert(self, timestamp, token_from, amount_from, wallet_from, token_to, amount_to, wallet_to):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO Swaps (timestamp, token_from, amount_from, wallet_from, token_to, amount_to, wallet_to, tag)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (timestamp, token_from, amount_from, wallet_from, token_to, amount_to, wallet_to, None),
            )
            conn.commit()
            logger.debug("Swap inserted")