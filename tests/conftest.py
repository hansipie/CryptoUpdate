"""Shared test fixtures."""

import pytest

from modules import swap_push


@pytest.fixture(autouse=True)
def _isolate_tradbot(tmp_path, monkeypatch):
    """Never let a test reach the real tradbot.

    Writing a swap triggers a push that reads the url and token from the real
    settings.json: a test database would then replace the swaps of the
    production bot. Ignore the settings file and the env vars for every test;
    tests that need a configuration set it explicitly.
    """
    monkeypatch.setattr(swap_push, "SETTINGS_FILE", str(tmp_path / "no-settings.json"))
    monkeypatch.delenv("TRADBOT_URL", raising=False)
    monkeypatch.delenv("TRADBOT_TOKEN", raising=False)
