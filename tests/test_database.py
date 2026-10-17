"""Database layer tests: transactions, migrations, price cache, CMC parsing."""

import sqlite3
import threading
from unittest import mock

import pytest

from modules.cmc import CMC
from modules.database import migrations
from modules.database.operations import Operations
from modules.database.portfolios import Portfolios
from modules.database.price_cache import PriceCache
from modules.database.swaps import Swaps
from modules.utils import db_connect


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "db.sqlite3")
    migrations.run_migrations(path)
    portfolios = Portfolios(path)
    portfolios.add_portfolio("A")
    portfolios.add_portfolio("B")
    return path


def balance(db, name):
    return Portfolios(db).get_tokens(name)


def buys(db):
    return Operations(db).get_operations_by_type("buy")


# --- migrations ---------------------------------------------------------------


def test_migrations_reach_latest_version_and_are_idempotent(db):
    migrations.run_migrations(db)
    with db_connect(db) as conn:
        row = conn.execute(
            "SELECT value FROM Customdata WHERE name = 'db_version'"
        ).fetchone()
    assert row[0] == str(max(migrations.MIGRATIONS))


def test_failed_migration_rolls_back_schema_and_version(db, monkeypatch):
    def failing(conn):
        conn.execute("CREATE TABLE Tmp (x)")
        raise RuntimeError("boom")

    version = max(migrations.MIGRATIONS) + 1
    monkeypatch.setitem(migrations.MIGRATIONS, version, failing)
    with pytest.raises(RuntimeError):
        migrations.run_migrations(db)
    with db_connect(db) as conn:
        assert conn.execute(
            "SELECT value FROM Customdata WHERE name = 'db_version'"
        ).fetchone()[0] == str(version - 1)
        assert not conn.execute(
            "SELECT 1 FROM sqlite_master WHERE name = 'Tmp'"
        ).fetchone()


# --- operations / holdings ----------------------------------------------------


def test_buy_insert_replace_delete_keep_holdings_in_sync(db):
    ops = Operations(db)
    ops.insert("buy", 100, 2, "EUR", "ETH", 1, "A", portfolio_adjusted=True)
    assert balance(db, "A") == {"ETH": 2}

    ops.replace(buys(db)[0][0], "buy", 150, 3, "EUR", "ETH", 2, "B", True)
    assert balance(db, "A") == {"ETH": 0}
    assert balance(db, "B") == {"ETH": 3}

    ops.delete(buys(db)[0][0], revert_portfolio=True)
    assert balance(db, "B") == {"ETH": 0}
    assert not buys(db)


def test_unsynchronized_buy_does_not_touch_holdings(db):
    Operations(db).insert("buy", 1, 1, "EUR", "ETH", 1, "A", portfolio_adjusted=False)
    assert balance(db, "A") == {}


def test_failed_replace_changes_nothing(db):
    ops = Operations(db)
    ops.insert("buy", 100, 2, "EUR", "ETH", 1, "A", portfolio_adjusted=True)
    op_id = buys(db)[0][0]
    with pytest.raises(ValueError):
        ops.replace(op_id, "buy", 1, 9, "EUR", "ETH", 3, "NOPE", True)
    assert balance(db, "A") == {"ETH": 2}
    assert [row[0] for row in buys(db)] == [op_id]


def test_airdrop_rows_survive_replace(db):
    ops = Operations(db)
    ops.insert("buy", 0.0, 5, "EUR", "ARB", 1, "A", portfolio_adjusted=True)
    ops.replace(buys(db)[0][0], "buy", 0.0, 7, "EUR", "ARB", 1, "A", True)
    assert buys(db)[0][2] == 0.0
    assert balance(db, "A") == {"ARB": 7}


# --- swaps --------------------------------------------------------------------


def test_swap_insert_and_replace_move_both_legs(db):
    Portfolios(db).set_token_add("A", "ETH", 5)
    swaps = Swaps(db)
    swaps.insert(1, "ETH", 2, "A", "BTC", 0.1, "B", portfolio_adjusted=True)
    assert balance(db, "A")["ETH"] == 3
    assert balance(db, "B")["BTC"] == pytest.approx(0.1)

    swaps.replace(
        swaps.get_by_tag("")[0][0],
        2,
        "ETH",
        1,
        "A",
        "BTC",
        0.05,
        "B",
        portfolio_adjusted=True,
    )
    assert balance(db, "A")["ETH"] == 4
    assert balance(db, "B")["BTC"] == pytest.approx(0.05)


def test_swap_within_one_portfolio_is_valid(db):
    Portfolios(db).set_token_add("A", "ETH", 5)
    Swaps(db).insert(1, "ETH", 2, "A", "BTC", 0.1, "A", portfolio_adjusted=True)
    assert balance(db, "A")["ETH"] == 3
    assert balance(db, "A")["BTC"] == pytest.approx(0.1)


def test_failed_swap_replace_changes_nothing(db):
    Portfolios(db).set_token_add("A", "ETH", 5)
    swaps = Swaps(db)
    swaps.insert(1, "ETH", 2, "A", "BTC", 0.1, "B", portfolio_adjusted=True)
    swap_id = swaps.get_by_tag("")[0][0]
    with pytest.raises(ValueError):
        swaps.replace(
            swap_id, 3, "ETH", 1, "A", "BTC", 1, "NOPE", portfolio_adjusted=True
        )
    assert balance(db, "A")["ETH"] == 3
    assert swaps.is_portfolio_adjusted(swap_id)
    assert len(swaps.get_by_tag("")) == 1


def test_swap_archive_and_errors_are_not_swallowed(db, tmp_path):
    swaps = Swaps(db)
    swaps.insert(1, "ETH", 2, "A", "BTC", 0.1, "B")
    swap_id = swaps.get_by_tag("")[0][0]
    swaps.update_tag(swap_id, "archived")
    assert len(swaps.get_by_tag("archived")) == 1
    swaps.update_tag(swap_id, None)
    assert len(swaps.get_by_tag("")) == 1

    broken = Swaps.__new__(Swaps)
    broken.db_path = str(tmp_path / "missing" / "db.sqlite3")
    with pytest.raises(sqlite3.OperationalError):
        broken.delete(1)


# --- portfolios ---------------------------------------------------------------


def test_rename_portfolio_updates_operations_and_swaps(db):
    Operations(db).insert("buy", 1, 1, "EUR", "ETH", 1, "A", portfolio_adjusted=True)
    Swaps(db).insert(1, "ETH", 1, "A", "BTC", 1, "A")
    Portfolios(db).rename_portfolio("A", "A2")
    assert buys(db)[0][7] == "A2"
    swap = Swaps(db).get_by_tag("")[0]
    assert (swap[4], swap[7]) == ("A2", "A2")
    Operations(db).delete(buys(db)[0][0], revert_portfolio=True)
    assert balance(db, "A2") == {"ETH": 0}


def test_set_token_add_unknown_portfolio_raises(db):
    with pytest.raises(ValueError):
        Portfolios(db).set_token_add("NOPE", "ETH", 1)


def test_concurrent_increments_are_not_lost(db):
    portfolios = Portfolios(db)

    def work():
        for _ in range(20):
            portfolios.set_token_add("B", "XRP", 1)

    threads = [threading.Thread(target=work) for _ in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert balance(db, "B")["XRP"] == 100


# --- connections --------------------------------------------------------------


def test_db_connect_commits_closes_and_rolls_back(tmp_path):
    path = str(tmp_path / "c.sqlite3")
    with db_connect(path) as conn:
        conn.execute("CREATE TABLE t (x)")
    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute("SELECT 1")

    with pytest.raises(KeyError):
        with db_connect(path) as conn:
            conn.execute("INSERT INTO t VALUES (1)")
            raise KeyError
    with db_connect(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 0


# --- price cache --------------------------------------------------------------


def test_price_cache_only_widens_coverage_when_ranges_touch(tmp_path):
    cache = PriceCache(str(tmp_path / "pc.sqlite3"))
    cache.store(1, [(10, 1.0, 0)], 0, 100, 5)
    cache.store(1, [(900, 2.0, 0)], 800, 1000, 6)  # disjoint: gap not covered
    assert cache.get_coverage(1) == (0, 100, 5)
    cache.store(1, [(150, 3.0, 0)], 90, 200, 7)  # overlapping: widened
    assert cache.get_coverage(1) == (0, 200, 7)
    assert len(cache.read(1, 0, 1000)) == 3


# --- CoinMarketCap parsing ----------------------------------------------------


def _response(payload):
    response = mock.Mock(status_code=200)
    response.json.return_value = {"data": payload}
    return response


def _quote(price):
    return [{"quote": {"EUR": {"price": price}}}]


def test_cmc_drops_missing_and_invalid_crypto_prices():
    data = {
        "OK": _quote(12.5),
        "NONE": _quote(None),
        "TEXT": _quote("x"),
        "NAN": _quote(float("nan")),
        "EMPTY": [],
        "NOQUOTE": [{"quote": {}}],
    }
    with mock.patch("modules.cmc.requests.get", return_value=_response(data)):
        prices = CMC("key").get_crypto_prices(list(data))
    assert prices == {"OK": {"price": 12.5, "unit": "EUR"}}


def test_cmc_drops_invalid_fiat_rates():
    date = "2026-01-01T00:00:00.000Z"
    payload = [
        {
            "quote": {
                "USD": {"price": 1.2, "last_updated": date},
                "GBP": {"price": None, "last_updated": date},
            }
        }
    ]
    with mock.patch("modules.cmc.requests.get", return_value=_response(payload)):
        rates = CMC("key").get_current_fiat_prices(converts=["USD", "GBP"])
    assert list(rates) == ["USD"]
    assert rates["USD"]["price"] == 1.2
