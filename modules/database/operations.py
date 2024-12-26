import logging
import sqlite3

logger = logging.getLogger(__name__)

class operations:
    def __init__(self, db_path: str = "./data/db.sqlite3"):
        self.db_path = db_path

        # Créer les tables si elles n'existent pas
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS Operations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL
                )
            """
            )
            conn.commit()
    