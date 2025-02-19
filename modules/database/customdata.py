import logging
import sqlite3

logger = logging.getLogger(__name__)


class Customdata:
    def __init__(self, db_path: str):
        self.db = db_path
        self.__init_db()

    def __init_db(self):
        with sqlite3.connect(self.db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS Customdata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    value TEXT NOT NULL,
                    type TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def set(self, name: str, value: str, val_type: str):
        logger.debug("Setting %s to %s (%s)", name, value, val_type)
        with sqlite3.connect(self.db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO Customdata (name, value, type)
                VALUES (?, ?, ?)
                """,
                (name, value, val_type),
            )
            conn.commit()

    def get(self, name: str) -> str:
        with sqlite3.connect(self.db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value, type FROM Customdata WHERE name = ?", (name,))
            row = cursor.fetchone()
            logger.debug("row: %s", row)
            if row is None:
                return None
            return row

    def delete(self, name: str):
        logger.debug("Deleting %s", name)
        with sqlite3.connect(self.db) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Customdata WHERE name = ?", (name,))
            conn.commit()
