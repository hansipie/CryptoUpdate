"""Système de migration versionnée de la base de données SQLite.

La version courante du schéma est stockée dans la table Customdata
sous la clé 'db_version'. Au démarrage, les migrations en attente
sont appliquées séquentiellement.
"""

import logging
import sqlite3

logger = logging.getLogger(__name__)


def _ensure_customdata(db_path: str) -> None:
    """Bootstrap : crée la table Customdata si elle n'existe pas encore.

    Doit être appelé avant toute lecture de db_version.
    """
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS Customdata (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                name  TEXT NOT NULL UNIQUE,
                value TEXT NOT NULL,
                type  TEXT NOT NULL
            )"""
        )


def _get_db_version(db_path: str) -> int:
    """Retourne la version courante de la base (0 si absente)."""
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT value FROM Customdata WHERE name = 'db_version'"
        ).fetchone()
    return int(row[0]) if row else 0


def _set_db_version(db_path: str, version: int) -> None:
    """Enregistre la version courante dans Customdata."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO Customdata (name, value, type) VALUES ('db_version', ?, 'int')",
            (str(version),),
        )


def _migrate_v1(conn: sqlite3.Connection) -> None:
    """Schéma original — crée toutes les tables de base."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS TokensDatabase (
            timestamp INTEGER,
            token     TEXT,
            price     REAL,
            count     REAL
        );

        CREATE TABLE IF NOT EXISTS Portfolios (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            name   TEXT    NOT NULL UNIQUE,
            bundle INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS Portfolios_Tokens (
            portfolio_id INTEGER NOT NULL,
            token        TEXT    NOT NULL,
            amount       REAL,
            PRIMARY KEY (portfolio_id, token),
            FOREIGN KEY (portfolio_id) REFERENCES Portfolios(id)
        );

        CREATE TABLE IF NOT EXISTS Operations (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            type             TEXT,
            source           REAL,
            destination      REAL,
            source_unit      TEXT,
            destination_unit TEXT,
            timestamp        INTEGER,
            portfolio        TEXT
        );

        CREATE TABLE IF NOT EXISTS Market (
            timestamp INTEGER,
            token     TEXT,
            price     REAL
        );

        CREATE TABLE IF NOT EXISTS Currency (
            timestamp INTEGER,
            currency  TEXT,
            price     REAL
        );

        CREATE INDEX IF NOT EXISTS idx_currency ON Currency (timestamp, currency);

        CREATE TABLE IF NOT EXISTS Swaps (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   INTEGER,
            token_from  TEXT,
            amount_from REAL,
            wallet_from TEXT,
            token_to    TEXT,
            amount_to   REAL,
            wallet_to   TEXT,
            tag         TEXT
        );

        CREATE TABLE IF NOT EXISTS TokenMetadata (
            token                TEXT PRIMARY KEY,
            status               TEXT,
            delisting_date       INTEGER,
            last_valid_price_date INTEGER,
            notes                TEXT,
            created_at           INTEGER DEFAULT (strftime('%s', 'now')),
            updated_at           INTEGER DEFAULT (strftime('%s', 'now'))
        );
        """
    )


def _migrate_v2(conn: sqlite3.Connection) -> None:
    """Ajout des colonnes MarketRaccoon : mr_id et name dans TokenMetadata."""
    cursor = conn.cursor()
    for col, typedef in [("mr_id", "INTEGER"), ("name", "TEXT")]:
        try:
            cursor.execute(f"ALTER TABLE TokenMetadata ADD COLUMN {col} {typedef}")
        except sqlite3.OperationalError:
            pass  # colonne déjà présente


MIGRATIONS: dict = {
    1: _migrate_v1,
    2: _migrate_v2,
}


def run_migrations(db_path: str) -> None:
    """Point d'entrée public : applique toutes les migrations en attente.

    Args:
        db_path: Chemin vers le fichier SQLite.
    """
    _ensure_customdata(db_path)
    current_version = _get_db_version(db_path)
    logger.info("db_version courante : %d", current_version)

    for version in sorted(MIGRATIONS):
        if version <= current_version:
            continue
        logger.info("Application de la migration v%d…", version)
        with sqlite3.connect(db_path) as conn:
            MIGRATIONS[version](conn)
        _set_db_version(db_path, version)
        logger.info("Migration v%d appliquée — db_version = %d", version, version)
