from modules import swap_push
from modules.database.swaps import Swaps


def test_push_disabled_without_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TRADBOT_URL", raising=False)
    monkeypatch.delenv("TRADBOT_TOKEN", raising=False)
    assert swap_push.push_swaps_now(str(tmp_path / "db.sqlite3")) is False


def test_push_refuses_plain_http(tmp_path, monkeypatch):
    monkeypatch.setenv("TRADBOT_URL", "http://example.com")
    monkeypatch.setenv("TRADBOT_TOKEN", "t")
    assert swap_push.push_swaps_now(str(tmp_path / "db.sqlite3")) is False


def test_write_pushes_all_swaps(tmp_path, monkeypatch):
    db = str(tmp_path / "db.sqlite3")
    calls = []
    monkeypatch.setattr(
        "modules.database.swaps.push_swaps", lambda path: calls.append(path)
    )
    swaps = Swaps(db)
    swaps.insert(1, "ETH", 1, "A", "BTC", 1, "A")
    swaps.delete(swaps.get()[0][0])
    assert calls == [db, db]


def test_payload_contains_only_swap_fields(tmp_path):
    db = str(tmp_path / "db.sqlite3")
    Swaps(db).insert(1, "ETH", 2, "A", "BTC", 0.1, "B", note="secret note")
    rows = swap_push._read_swaps(db)  # pylint: disable=protected-access
    assert rows == [
        {
            "id": 1,
            "timestamp": 1,
            "token_from": "ETH",
            "amount_from": 2.0,
            "wallet_from": "A",
            "token_to": "BTC",
            "amount_to": 0.1,
            "wallet_to": "B",
        }
    ]
