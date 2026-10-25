"""Push the swaps to the tradbot service (best effort, never blocks a write).

Configuration (env vars override settings.json):
    TRADBOT_URL / settings["Tradbot"]["url"]      e.g. https://tradbot.example.com
    TRADBOT_TOKEN / settings["Tradbot"]["token"]  Bearer secret (SWAPS_API_TOKEN on the bot)
Without a url and a token the push is disabled and does nothing.
"""

import json
import logging
import os
import threading
import urllib.request

from modules.utils import db_connect

logger = logging.getLogger(__name__)

SETTINGS_FILE = "./settings.json"
TIMEOUT_S = 10

# Serializes pushes: the payload is read from the DB inside the lock, so the
# last push always carries the latest state even if several are queued.
_lock = threading.Lock()


def _load_config() -> tuple[str, str]:
    url = os.getenv("TRADBOT_URL", "")
    token = os.getenv("TRADBOT_TOKEN", "")
    if not (url and token):
        try:
            with open(SETTINGS_FILE, encoding="utf-8") as handle:
                section = json.load(handle).get("Tradbot", {})
            url = url or section.get("url", "")
            token = token or section.get("token", "")
        except (OSError, ValueError, AttributeError):
            pass
    return url.rstrip("/"), token


def _read_swaps(db_path: str) -> list[dict]:
    with db_connect(db_path) as conn:
        rows = conn.execute(
            "SELECT id, timestamp, token_from, amount_from, wallet_from,"
            " token_to, amount_to, wallet_to FROM Swaps"
            " WHERE token_from IS NOT NULL AND token_to IS NOT NULL"
            " AND amount_from > 0 AND amount_to > 0"
        ).fetchall()
    keys = (
        "id",
        "timestamp",
        "token_from",
        "amount_from",
        "wallet_from",
        "token_to",
        "amount_to",
        "wallet_to",
    )
    return [dict(zip(keys, row)) for row in rows]


def push_swaps_now(db_path: str) -> bool:
    """Send every swap to the bot. Return True on success; never raises."""
    url, token = _load_config()
    if not (url and token):
        return False
    if not url.startswith("https://") and not url.startswith("http://localhost"):
        logger.warning("Tradbot push skipped: the url must be https")
        return False
    try:
        with _lock:
            body = json.dumps({"swaps": _read_swaps(db_path)}).encode()
            request = urllib.request.Request(
                f"{url}/swaps",
                data=body,
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                    # Cloudflare rejects the default Python-urllib User-Agent (403)
                    "User-Agent": "CryptoUpdate/1.0",
                },
            )
            with urllib.request.urlopen(request, timeout=TIMEOUT_S):
                pass
        logger.info("Swaps pushed to tradbot")
        return True
    except Exception as exc:  # noqa: BLE001  # pylint: disable=broad-exception-caught
        logger.warning("Tradbot push failed: %s", exc)
        return False


def push_swaps(db_path: str) -> None:
    """Push in a background thread so the UI is not slowed down."""
    url, token = _load_config()
    if not (url and token):
        return
    threading.Thread(target=push_swaps_now, args=(db_path,), daemon=True).start()
