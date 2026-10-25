import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from modules import swap_push
from modules.configuration import Configuration
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


def test_is_enabled_needs_url_and_token(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TRADBOT_URL", raising=False)
    monkeypatch.delenv("TRADBOT_TOKEN", raising=False)
    assert swap_push.is_enabled() is False
    monkeypatch.setenv("TRADBOT_URL", "https://bot.example.com")
    assert swap_push.is_enabled() is False
    monkeypatch.setenv("TRADBOT_TOKEN", "t")
    assert swap_push.is_enabled() is True


# --- check_status: probe against a fake bot -------------------------------------


@pytest.fixture(name="fake_bot")
def _fake_bot():
    """A bot stand-in: GET /status, and POST /swaps checking a Bearer token."""
    state = {"status": 200, "token": "secret", "posts": 0}

    class Handler(BaseHTTPRequestHandler):
        def _reply(self, code):
            self.send_response(code)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_GET(self):  # pylint: disable=invalid-name
            self._reply(state["status"])

        def do_POST(self):  # pylint: disable=invalid-name
            state["posts"] += 1
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            if not state["token"]:
                self._reply(404)
            elif self.headers.get("Authorization") != f"Bearer {state['token']}":
                self._reply(401)
            else:
                self._reply(422)

        def log_message(self, *args):  # pylint: disable=arguments-differ
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://localhost:{server.server_port}", state
    server.shutdown()


def test_check_status_ok_and_stores_nothing(fake_bot):
    url, state = fake_bot
    assert swap_push.check_status(url, "secret") == "ok"
    assert state["posts"] == 1  # one probe, with an empty body (rejected as 422)


def test_check_status_wrong_token(fake_bot):
    url, _ = fake_bot
    assert swap_push.check_status(url, "nope") == "unauthorized"


def test_check_status_push_disabled_on_the_bot(fake_bot):
    url, state = fake_bot
    state["token"] = ""
    assert swap_push.check_status(url, "secret") == "push_disabled"


def test_check_status_without_token_does_not_post(fake_bot):
    url, state = fake_bot
    assert swap_push.check_status(url, "") == "no_token"
    assert state["posts"] == 0


def test_check_status_bot_down(fake_bot):
    url, state = fake_bot
    state["status"] = 502
    assert swap_push.check_status(url, "secret") == "down"


def test_check_status_unreachable():
    assert swap_push.check_status("http://localhost:1", "t") == "connection_error"


def test_check_status_url_validation():
    assert swap_push.check_status("", "t") == "not_configured"
    assert swap_push.check_status("http://example.com", "t") == "invalid_url"


# --- the Tradbot section survives a settings save -------------------------------


def test_save_config_persists_the_tradbot_section(tmp_path):
    settings = {
        "marketraccoon_url": "https://api.example.org",
        "notion_token": "",
        "notion_database": "",
        "notion_parentpage": "",
        "coinmarketcap_token": "",
        "ai_apitoken": "",
        "debug_flag": False,
        "data_path": str(tmp_path),
        "archive_path": str(tmp_path / "archive"),
        "dbfile": str(tmp_path / "db.sqlite3"),
        "tradbot_url": "https://bot.example.com",
        "tradbot_token": "t0k3n",
    }
    target = tmp_path / "settings.json"
    Configuration(str(target)).save_config(settings)
    saved = json.loads(target.read_text(encoding="utf-8"))
    assert saved["Tradbot"] == {"url": "https://bot.example.com", "token": "t0k3n"}
