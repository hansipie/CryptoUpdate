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
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS Customdata (
                    id    INTEGER PRIMARY KEY AUTOINCREMENT,
                    name  TEXT NOT NULL UNIQUE,
                    value TEXT NOT NULL,
                    type  TEXT NOT NULL
                )"""
            )
    except sqlite3.Error as e:
        logger.error("Erreur lors de la création de Customdata : %s", e)
        raise


def _get_db_version(db_path: str) -> int:
    """Retourne la version courante de la base (0 si absente)."""
    try:
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT value FROM Customdata WHERE name = 'db_version'"
            ).fetchone()
    except sqlite3.Error as e:
        logger.error("Erreur lors de la lecture de db_version : %s", e)
        raise
    if not row:
        return 0
    try:
        return int(row[0])
    except ValueError:
        logger.warning("db_version invalide : %s, reset à 0", row[0])
        return 0


def _migrate_v1(conn: sqlite3.Connection) -> None:
    """Schéma original — crée toutes les tables de base."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS TokensDatabase (
            timestamp INTEGER,
            token     TEXT,
            price     REAL,
            count     REAL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS Portfolios (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            name   TEXT    NOT NULL UNIQUE,
            bundle INTEGER DEFAULT 0
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS Portfolios_Tokens (
            portfolio_id INTEGER NOT NULL,
            token        TEXT    NOT NULL,
            amount       REAL,
            PRIMARY KEY (portfolio_id, token),
            FOREIGN KEY (portfolio_id) REFERENCES Portfolios(id)
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS Operations (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            type             TEXT,
            source           REAL,
            destination      REAL,
            source_unit      TEXT,
            destination_unit TEXT,
            timestamp        INTEGER,
            portfolio        TEXT
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS Market (
            timestamp INTEGER,
            token     TEXT,
            price     REAL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS Currency (
            timestamp INTEGER,
            currency  TEXT,
            price     REAL
        )"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_currency ON Currency (timestamp, currency)"
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS Swaps (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   INTEGER,
            token_from  TEXT,
            amount_from REAL,
            wallet_from TEXT,
            token_to    TEXT,
            amount_to   REAL,
            wallet_to   TEXT,
            tag         TEXT
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS TokenMetadata (
            token                TEXT PRIMARY KEY,
            status               TEXT,
            delisting_date       INTEGER,
            last_valid_price_date INTEGER,
            notes                TEXT,
            created_at           INTEGER DEFAULT (strftime('%s', 'now')),
            updated_at           INTEGER DEFAULT (strftime('%s', 'now'))
        )"""
    )


_V2_COLUMNS: dict = {
    "mr_id": "INTEGER",
    "name": "TEXT",
}


def _migrate_v2(conn: sqlite3.Connection) -> None:
    """Ajout des colonnes MarketRaccoon : mr_id et name dans TokenMetadata."""
    cursor = conn.cursor()
    for col, typedef in _V2_COLUMNS.items():
        try:
            cursor.execute(f"ALTER TABLE TokenMetadata ADD COLUMN {col} {typedef}")
        except sqlite3.OperationalError:
            logger.debug("Colonne %s déjà présente, skip", col)


def _migrate_v3(conn: sqlite3.Connection) -> None:
    """Renommage mr_id → mraccoon_id dans TokenMetadata."""
    conn.execute("ALTER TABLE TokenMetadata RENAME COLUMN mr_id TO mraccoon_id")


def _migrate_v4(conn: sqlite3.Connection) -> None:
    """Ajout d'une cle primaire id et suppression de l'unicite de token."""
    # Utiliser des execute() individuels (pas executescript) pour rester dans
    # la transaction SQLite ouverte par le context manager — évite un COMMIT
    # implicite partiel en cas d'erreur intermédiaire.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS TokenMetadata_new (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            token                TEXT,
            status               TEXT,
            delisting_date       INTEGER,
            last_valid_price_date INTEGER,
            notes                TEXT,
            created_at           INTEGER DEFAULT (strftime('%s', 'now')),
            updated_at           INTEGER DEFAULT (strftime('%s', 'now')),
            mraccoon_id          INTEGER,
            name                 TEXT
        )
        """
    )
    conn.execute(
        """
        INSERT INTO TokenMetadata_new (
            token, status, delisting_date, last_valid_price_date,
            notes, created_at, updated_at, mraccoon_id, name
        )
        SELECT
            token, status, delisting_date, last_valid_price_date,
            notes, created_at, updated_at, mraccoon_id, name
        FROM TokenMetadata
        """
    )
    conn.execute("DROP TABLE TokenMetadata")
    conn.execute("ALTER TABLE TokenMetadata_new RENAME TO TokenMetadata")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_tokenmetadata_token ON TokenMetadata (token)"
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_tokenmetadata_mraccoon_id
            ON TokenMetadata (mraccoon_id)
        """
    )


def _migrate_v5(conn: sqlite3.Connection) -> None:
    """Ajout de la colonne note dans Swaps."""
    try:
        conn.execute("ALTER TABLE Swaps ADD COLUMN note TEXT")
    except sqlite3.OperationalError:
        logger.debug("Colonne note déjà présente dans Swaps, skip")


def _migrate_v6(conn: sqlite3.Connection) -> None:
    """Ajout d'un index composite sur TokensDatabase pour accélérer les requêtes par token/timestamp."""
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_tokensdb ON TokensDatabase (timestamp, token)"
    )


def _migrate_v7(conn: sqlite3.Connection) -> None:
    """Conversion des colonnes amount_from/amount_to de TEXT en REAL dans Swaps."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS Swaps_new (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   INTEGER,
            token_from  TEXT,
            amount_from REAL,
            wallet_from TEXT,
            token_to    TEXT,
            amount_to   REAL,
            wallet_to   TEXT,
            tag         TEXT,
            note        TEXT
        )"""
    )
    conn.execute(
        """INSERT INTO Swaps_new
               (id, timestamp, token_from, amount_from, wallet_from,
                token_to, amount_to, wallet_to, tag, note)
           SELECT id, timestamp, token_from,
                  CAST(amount_from AS REAL),
                  wallet_from, token_to,
                  CAST(amount_to AS REAL),
                  wallet_to, tag, note
           FROM Swaps"""
    )
    conn.execute("DROP TABLE Swaps")
    conn.execute("ALTER TABLE Swaps_new RENAME TO Swaps")


MIGRATIONS: dict = {
    1: _migrate_v1,
    2: _migrate_v2,
    3: _migrate_v3,
    4: _migrate_v4,
    5: _migrate_v5,
    6: _migrate_v6,
    7: _migrate_v7,
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
            conn.execute(
                "INSERT OR REPLACE INTO Customdata (name, value, type) VALUES ('db_version', ?, 'int')",
                (str(version),),
            )
        logger.info("Migration v%d appliquée — db_version = %d", version, version)
