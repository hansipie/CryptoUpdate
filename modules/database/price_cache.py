"""Incremental SQLite cache for MarketRaccoon historical prices.

Historical prices are immutable once published, so each coin's series is stored
once and only the missing head/tail is fetched later. The cache lives in its own
SQLite file (disposable: deleting it only costs a re-download) and is safe to use
from several threads: every call opens its own connection.
"""

import logging
import os
import sqlite3

from modules.utils import db_connect


logger = logging.getLogger(__name__)

_SQLITE_TIMEOUT = 30


class PriceCache:
    """Per-coin price series with the time range known to be complete.

    Tables:
        prices(coin_id, ts, price, interpolated): one row per data point,
            ts being a UTC Unix timestamp.
        coverage(coin_id, from_ts, to_ts, fetched_at): contiguous range already
            fetched for the coin and when its newest part was last refreshed.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        cache_dir = os.path.dirname(db_path)
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS prices (
                    coin_id      INTEGER NOT NULL,
                    ts           INTEGER NOT NULL,
                    price        REAL,
                    interpolated INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (coin_id, ts)
                ) WITHOUT ROWID
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS coverage (
                    coin_id    INTEGER PRIMARY KEY,
                    from_ts    INTEGER NOT NULL,
                    to_ts      INTEGER NOT NULL,
                    fetched_at INTEGER NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return db_connect(self.db_path, timeout=_SQLITE_TIMEOUT)

    def get_coverage(self, coin_id: int) -> tuple | None:
        """Return (from_ts, to_ts, fetched_at) for a coin, or None if unknown."""
        with self._connect() as conn:
            return conn.execute(
                "SELECT from_ts, to_ts, fetched_at FROM coverage WHERE coin_id = ?",
                (int(coin_id),),
            ).fetchone()

    def store(
        self,
        coin_id: int,
        rows: list,
        from_ts: int,
        to_ts: int,
        fetched_at: int,
    ) -> None:
        """Insert/replace data points and widen the coin's covered range.

        The covered range is only widened when the fetched range overlaps or
        touches it: a disjoint fetch (e.g. two sessions starting from an empty
        cache on different periods) must not declare the gap between them as
        covered. Its rows are kept, the gap is fetched on a later request.

        Args:
            coin_id: MarketRaccoon coin id
            rows: List of (ts, price, interpolated) tuples
            from_ts: Start of the range that was fetched
            to_ts: End of the range that was fetched
            fetched_at: Unix time of the fetch
        """
        coin_id = int(coin_id)
        with self._connect() as conn:
            conn.executemany(
                "INSERT OR REPLACE INTO prices (coin_id, ts, price, interpolated)"
                " VALUES (?, ?, ?, ?)",
                [(coin_id, int(ts), price, int(bool(i))) for ts, price, i in rows],
            )
            conn.execute(
                """
                INSERT INTO coverage (coin_id, from_ts, to_ts, fetched_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(coin_id) DO UPDATE SET
                    from_ts = MIN(from_ts, excluded.from_ts),
                    to_ts = MAX(to_ts, excluded.to_ts),
                    fetched_at = excluded.fetched_at
                WHERE excluded.from_ts <= to_ts AND excluded.to_ts >= from_ts
                """,
                (coin_id, int(from_ts), int(to_ts), int(fetched_at)),
            )

    def read(self, coin_id: int, from_ts: int, to_ts: int) -> list:
        """Return (ts, price, interpolated) rows within [from_ts, to_ts], by time."""
        with self._connect() as conn:
            return conn.execute(
                "SELECT ts, price, interpolated FROM prices"
                " WHERE coin_id = ? AND ts BETWEEN ? AND ? ORDER BY ts",
                (int(coin_id), int(from_ts), int(to_ts)),
            ).fetchall()
