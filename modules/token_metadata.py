"""
Module pour gérer les métadonnées des tokens (tokens délistés, actifs, etc.)
"""

import sqlite3
from typing import Optional, List, Dict
from enum import Enum
from datetime import datetime

import pandas as pd


class TokenStatus(Enum):
    """Status des tokens"""

    ACTIVE = "active"
    DELISTED = "delisted"
    DEPRECATED = "deprecated"
    MIGRATED = "migrated"


class TokenMetadataManager:
    """Gestionnaire des métadonnées des tokens"""

    def __init__(self, db_path: str = "data/db.sqlite3"):
        self.db_path = db_path

    def get_token_status(self, token: str) -> Optional[TokenStatus]:
        """
        Récupère le statut d'un token.

        Args:
            token: Symbole du token

        Returns:
            TokenStatus si le token existe dans les métadonnées, None sinon
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT status
                   FROM TokenMetadata
                   WHERE token = ?
                   ORDER BY updated_at DESC
                   LIMIT 1""",
                (token,),
            )
            result = cursor.fetchone()
            if result:
                return TokenStatus(result[0])
            return None

    def is_token_active(self, token: str) -> bool:
        """
        Vérifie si un token est actif.

        Args:
            token: Symbole du token

        Returns:
            True si le token est actif, False sinon (ou si inconnu)
        """
        status = self.get_token_status(token)
        # Si le token n'est pas dans les métadonnées, on le considère comme actif par défaut
        return status is None or status == TokenStatus.ACTIVE

    def is_token_delisted(self, token: str) -> bool:
        """
        Vérifie si un token est délisté.

        Args:
            token: Symbole du token

        Returns:
            True si le token est délisté, False sinon
        """
        status = self.get_token_status(token)
        return status == TokenStatus.DELISTED

    def get_delisted_tokens(self) -> List[str]:
        """
        Récupère la liste de tous les tokens délistés.

        Returns:
            Liste des symboles de tokens délistés
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT DISTINCT token FROM TokenMetadata WHERE status = ?",
                (TokenStatus.DELISTED.value,),
            )
            return [row[0] for row in cursor.fetchall()]

    def get_active_tokens(self) -> List[str]:
        """
        Récupère la liste de tous les tokens actifs.

        Returns:
            Liste des symboles de tokens actifs
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT DISTINCT token FROM TokenMetadata WHERE status = ?",
                (TokenStatus.ACTIVE.value,),
            )
            return [row[0] for row in cursor.fetchall()]

    def get_token_info(self, token: str) -> Optional[Dict]:
        """
        Récupère toutes les informations d'un token.

        Args:
            token: Symbole du token

        Returns:
            Dictionnaire avec les informations du token, ou None si non trouvé
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """SELECT token, status,
                          datetime(delisting_date, 'unixepoch') as delisting_date,
                          datetime(last_valid_price_date, 'unixepoch') as last_valid_price_date,
                          notes,
                          datetime(created_at, 'unixepoch') as created_at,
                          datetime(updated_at, 'unixepoch') as updated_at,
                          mraccoon_id, name
                   FROM TokenMetadata
                   WHERE token = ?
                   ORDER BY updated_at DESC
                   LIMIT 1""",
                (token,),
            )
            result = cursor.fetchone()
            if result:
                return dict(result)
            return None

    def add_or_update_token(
        self,
        token: str,
        status: TokenStatus,
        delisting_date: Optional[datetime] = None,
        last_valid_price_date: Optional[datetime] = None,
        notes: Optional[str] = None,
    ) -> None:
        """
        Ajoute ou met à jour les métadonnées d'un token.

        Args:
            token: Symbole du token
            status: Status du token
            delisting_date: Date de délisting (si applicable)
            last_valid_price_date: Date du dernier prix valide (si applicable)
            notes: Notes supplémentaires
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            delisting_ts = int(delisting_date.timestamp()) if delisting_date else None
            last_price_ts = (
                int(last_valid_price_date.timestamp())
                if last_valid_price_date
                else None
            )

            cursor.execute(
                """UPDATE TokenMetadata
                   SET status = ?,
                       delisting_date = COALESCE(?, delisting_date),
                       last_valid_price_date = COALESCE(?, last_valid_price_date),
                       notes = COALESCE(?, notes),
                       updated_at = strftime('%s', 'now')
                   WHERE token = ?""",
                (status.value, delisting_ts, last_price_ts, notes, token),
            )

            if cursor.rowcount == 0:
                cursor.execute(
                    """INSERT INTO TokenMetadata
                       (token, status, delisting_date, last_valid_price_date, notes, updated_at)
                       VALUES (?, ?, ?, ?, ?, strftime('%s', 'now'))""",
                    (token, status.value, delisting_ts, last_price_ts, notes),
                )
            conn.commit()

    def add_or_update_token_by_mr_id(
        self,
        mr_id: int,
        token: str,
        status: TokenStatus,
        delisting_date: Optional[datetime] = None,
        last_valid_price_date: Optional[datetime] = None,
        notes: Optional[str] = None,
    ) -> None:
        """
        Ajoute ou met a jour les metadonnees d'un token via mraccoon_id.

        Args:
            mr_id: ID MarketRaccoon du token
            token: Symbole du token (utilise si insertion)
            status: Status du token
            delisting_date: Date de delisting (si applicable)
            last_valid_price_date: Date du dernier prix valide (si applicable)
            notes: Notes supplementaires
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            delisting_ts = int(delisting_date.timestamp()) if delisting_date else None
            last_price_ts = (
                int(last_valid_price_date.timestamp())
                if last_valid_price_date
                else None
            )

            cursor.execute(
                """UPDATE TokenMetadata
                   SET status = ?,
                       delisting_date = COALESCE(?, delisting_date),
                       last_valid_price_date = COALESCE(?, last_valid_price_date),
                       notes = COALESCE(?, notes),
                       updated_at = strftime('%s', 'now')
                   WHERE mraccoon_id = ?""",
                (status.value, delisting_ts, last_price_ts, notes, mr_id),
            )

            if cursor.rowcount == 0:
                cursor.execute(
                    """INSERT INTO TokenMetadata
                       (token, mraccoon_id, status, delisting_date, last_valid_price_date, notes, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, strftime('%s', 'now'))""",
                    (token, mr_id, status.value, delisting_ts, last_price_ts, notes),
                )

            conn.commit()

    def filter_active_tokens(self, tokens: List[str]) -> List[str]:
        """
        Filtre une liste de tokens pour ne garder que les actifs.

        Args:
            tokens: Liste de symboles de tokens

        Returns:
            Liste filtrée contenant uniquement les tokens actifs
        """
        return [token for token in tokens if self.is_token_active(token)]

    def get_mr_id(self, token: str) -> Optional[int]:
        """Get MarketRaccoon ID for a token symbol.

        Args:
            token: Token symbol

        Returns:
            MarketRaccoon ID or None if not found / not set
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT mraccoon_id
                   FROM TokenMetadata
                   WHERE token = ?
                   ORDER BY updated_at DESC
                   LIMIT 1""",
                (token,),
            )
            result = cursor.fetchone()
            return result[0] if result and result[0] is not None else None

    def get_all_tokens_df(self) -> Optional[pd.DataFrame]:
        """Get all tokens that have a MarketRaccoon ID, as a DataFrame.

        Returns:
            DataFrame with columns token, mraccoon_id, name or None if empty
        """
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(
                "SELECT token, mraccoon_id, name FROM TokenMetadata"
                " WHERE mraccoon_id IS NOT NULL ORDER BY token",
                conn,
            )
            return df if not df.empty else None

    def upsert_token_info(self, token: str, mraccoon_id: int, name: str) -> None:
        """Insert or update MarketRaccoon ID and name for a token.

        Preserves existing status and other fields on conflict.

        Args:
            token: Token symbol
            mraccoon_id: MarketRaccoon integer ID
            name: Full token name
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE TokenMetadata
                   SET mraccoon_id = ?,
                       name = ?,
                       updated_at = strftime('%s', 'now')
                   WHERE token = ?""",
                (mraccoon_id, name, token),
            )

            if cursor.rowcount == 0:
                cursor.execute(
                    """INSERT INTO TokenMetadata (token, mraccoon_id, name, status, updated_at)
                       VALUES (?, ?, ?, 'active', strftime('%s', 'now'))""",
                    (token, mraccoon_id, name),
                )
            conn.commit()

    def upsert_token_info_by_mr_id(
        self, mraccoon_id: int, token: str, name: str
    ) -> None:
        """Insert or update MarketRaccoon ID and name using mraccoon_id.

        Preserves existing token symbol when mraccoon_id is already present.

        Args:
            mraccoon_id: MarketRaccoon integer ID
            token: Token symbol (used on insert)
            name: Full token name
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT token FROM TokenMetadata WHERE mraccoon_id = ?",
                (mraccoon_id,),
            )
            existing = cursor.fetchone()

            if existing:
                cursor.execute(
                    """UPDATE TokenMetadata
                       SET name = ?,
                           updated_at = strftime('%s', 'now')
                       WHERE mraccoon_id = ?""",
                    (name, mraccoon_id),
                )
            else:
                # Chercher si un token existe avec le même symbole mais sans mraccoon_id
                cursor.execute(
                    """SELECT id FROM TokenMetadata
                       WHERE token = ? AND (mraccoon_id IS NULL OR mraccoon_id = '')
                       ORDER BY updated_at DESC
                       LIMIT 1""",
                    (token,),
                )
                existing_without_id = cursor.fetchone()

                if existing_without_id:
                    # Mettre à jour le token existant avec le mraccoon_id
                    cursor.execute(
                        """UPDATE TokenMetadata
                           SET mraccoon_id = ?,
                               name = ?,
                               updated_at = strftime('%s', 'now')
                           WHERE id = ?""",
                        (mraccoon_id, name, existing_without_id[0]),
                    )
                else:
                    # Insérer un nouveau token
                    cursor.execute(
                        """INSERT INTO TokenMetadata (token, mraccoon_id, name, status, updated_at)
                           VALUES (?, ?, ?, 'active', strftime('%s', 'now'))""",
                        (token, mraccoon_id, name),
                    )

            conn.commit()

    def delete_token(self, token: str) -> bool:
        """Delete a token entry from TokenMetadata.

        Args:
            token: Token symbol to delete

        Returns:
            True if the row was deleted, False if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM TokenMetadata WHERE token = ?", (token,))
            conn.commit()
            return cursor.rowcount > 0

    def get_token_info_by_mr_id(self, mr_id: int) -> Optional[Dict]:
        """
        Récupère toutes les informations d'un token par son mraccoon_id.

        Args:
            mr_id: ID MarketRaccoon du token

        Returns:
            Dictionnaire avec les informations du token, ou None si non trouvé
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """SELECT token, status,
                          datetime(delisting_date, 'unixepoch') as delisting_date,
                          datetime(last_valid_price_date, 'unixepoch') as last_valid_price_date,
                          notes,
                          datetime(created_at, 'unixepoch') as created_at,
                          datetime(updated_at, 'unixepoch') as updated_at,
                          mraccoon_id, name
                   FROM TokenMetadata
                   WHERE mraccoon_id = ?""",
                (mr_id,),
            )
            result = cursor.fetchone()
            if result:
                return dict(result)
            return None

    def delete_token_by_mr_id(self, mr_id: int) -> bool:
        """Delete a token entry from TokenMetadata by mraccoon_id.

        Args:
            mr_id: MarketRaccoon ID of the token to delete

        Returns:
            True if the row was deleted, False if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM TokenMetadata WHERE mraccoon_id = ?", (mr_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_all_metadata(self) -> List[Dict]:
        """
        Récupère toutes les métadonnées de tous les tokens.

        Returns:
            Liste de dictionnaires contenant les métadonnées de tous les tokens
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """SELECT token, name, status,
                          mraccoon_id,
                          datetime(delisting_date, 'unixepoch') as delisting_date,
                          datetime(last_valid_price_date, 'unixepoch') as last_valid_price_date,
                          notes,
                          datetime(created_at, 'unixepoch') as created_at,
                          datetime(updated_at, 'unixepoch') as updated_at
                   FROM TokenMetadata
                   ORDER BY status, token"""
            )
            return [dict(row) for row in cursor.fetchall()]


# Exemple d'utilisation
if __name__ == "__main__":
    manager = TokenMetadataManager()

    # Vérifier si un token est actif
    print(
        f"BTC actif: {manager.is_token_active('BTC')}"
    )  # True (pas dans métadonnées = actif par défaut)
    print(f"KYROS actif: {manager.is_token_active('KYROS')}")  # False
    print(f"MATIC délisté: {manager.is_token_delisted('MATIC')}")  # True

    # Récupérer tous les tokens délistés
    delisted = manager.get_delisted_tokens()
    print(f"\nTokens délistés: {delisted}")

    # Récupérer les infos d'un token
    info = manager.get_token_info("MATIC")
    if info:
        print("\nInfo MATIC:")
        for key, value in info.items():
            print(f"  {key}: {value}")

    # Filtrer une liste de tokens
    all_tokens = ["BTC", "ETH", "MATIC", "KYROS", "SOL"]
    active_only = manager.filter_active_tokens(all_tokens)
    print(f"\nTokens actifs parmi {all_tokens}: {active_only}")
