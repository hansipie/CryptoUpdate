"""Tests for time handling, currency conversion and configuration saving."""

import datetime
import json
import os
import stat
from unittest import mock
from zoneinfo import ZoneInfo

import pandas as pd
import pytest
import streamlit as st

from modules import tools, utils
from modules.configuration import Configuration
from modules.database import migrations
from modules.database.market import Market

PARIS = ZoneInfo("Europe/Paris")


@pytest.fixture(autouse=True)
def paris_timezone():
    with mock.patch("tzlocal.get_localzone", return_value=PARIS):
        yield


@pytest.fixture(autouse=True)
def settings():
    st.session_state.settings = {"fiat_currency": "EUR", "coinmarketcap_token": "x"}
    yield st.session_state.settings
    st.session_state.settings = {}


# --- time ---------------------------------------------------------------------


def test_to_timestamp_a_converts_local_time_to_utc():
    ts = utils.to_timestamp_a(datetime.date(2026, 1, 1), datetime.time(1, 0))
    assert ts == pd.Timestamp("2026-01-01 00:00", tz="UTC").timestamp()


@pytest.mark.parametrize(
    "date",
    [datetime.date(2026, 10, 25), datetime.date(2026, 3, 29)],
    ids=["ambiguous-hour", "nonexistent-hour"],
)
def test_to_timestamp_a_survives_dst_changes(date):
    assert utils.to_timestamp_a(date, datetime.time(2, 30)) > 0


def test_interpolate_from_series_reads_naive_index_as_local_time():
    # Paris 01:00 / 03:00 (winter) = 00:00 / 02:00 UTC: 01:00 UTC is the middle
    series = pd.Series(
        [1.0, 3.0], index=pd.to_datetime(["2026-01-01 01:00", "2026-01-01 03:00"])
    )
    ts = int(pd.Timestamp("2026-01-01 01:00", tz="UTC").timestamp())
    assert tools._interpolate_from_series(  # pylint: disable=protected-access
        series, ts
    ) == pytest.approx(2.0)


# --- currency conversion ------------------------------------------------------


def test_fiat_price_in_eur_is_the_inverse_of_the_stored_rate(tmp_path):
    db = str(tmp_path / "db.sqlite3")
    migrations.run_migrations(db)
    Market(db, "x").add_currency(1_700_000_000, "USD", 1.25)  # 1 EUR = 1.25 USD
    price = getattr(tools, "__interpolate_token")("USD", 1_700_000_000, db)
    assert price == pytest.approx(0.8)


def test_conversion_returns_none_when_rate_is_unavailable():
    api = mock.Mock()
    api.get_fiat_latest_rate_cached.return_value = None
    with mock.patch.object(tools, "get_cached_api_market", return_value=api):
        assert tools.convert_price_to_target_currency(100, "USD") is None
        assert tools.convert_price_to_target_currency(100, "EUR") == 100


def test_conversion_uses_latest_usd_to_eur_rate():
    api = mock.Mock()
    api.get_fiat_latest_rate_cached.return_value = pd.DataFrame({"price": [0.8]})
    with mock.patch.object(tools, "get_cached_api_market", return_value=api):
        assert tools.convert_price_to_target_currency(100, "USD") == pytest.approx(80)
        assert tools.convert_price_to_target_currency(
            80, "EUR", "USD"
        ) == pytest.approx(100)


def test_calc_perf_api_has_no_eur_price_without_a_usd_rate():
    df = pd.DataFrame({"Token": ["BTC"], "Rate": [100.0], "Currency": ["EUR"]})
    with mock.patch.object(tools, "_get_api_fiat_rate", return_value=None):
        out = tools.calc_perf_api(
            df,
            "Token",
            "Rate",
            col_currency="Currency",
            prices_usd={"BTC": 110.0},
            usd_to_eur=None,
        )
    assert pd.isna(out["Current Rate"].iloc[0])
    assert pd.isna(out["Perf."].iloc[0])


# --- configuration ------------------------------------------------------------


def _full_settings(tmp_path):
    return {
        "marketraccoon_url": "https://api.example.org",
        "notion_token": "",
        "notion_database": "",
        "notion_parentpage": "",
        "coinmarketcap_token": "cmc",
        "ai_apitoken": "ai",
        "debug_flag": False,
        "data_path": str(tmp_path),
        "archive_path": str(tmp_path / "archive"),
        "dbfile": str(tmp_path / "db.sqlite3"),
    }


def test_save_config_creates_a_private_file(tmp_path):
    target = tmp_path / "settings.json"
    Configuration(str(target)).save_config(_full_settings(tmp_path))
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert json.loads(target.read_text())["Coinmarketcap"]["token"] == "cmc"


def test_save_config_keeps_permissions_of_an_existing_file(tmp_path):
    target = tmp_path / "settings.json"
    target.write_text("{}")
    os.chmod(target, 0o640)
    Configuration(str(target)).save_config(_full_settings(tmp_path))
    assert stat.S_IMODE(target.stat().st_mode) == 0o640


def test_failed_save_config_keeps_the_previous_settings(tmp_path):
    target = tmp_path / "settings.json"
    target.write_text('{"keep": "me"}')
    settings = _full_settings(tmp_path)
    settings["ai_apitoken"] = object()  # not JSON serializable
    with pytest.raises(TypeError):
        Configuration(str(target)).save_config(settings)
    assert json.loads(target.read_text()) == {"keep": "me"}
    assert not (tmp_path / "settings.json.tmp").exists()


def test_compute_cost_basis_carries_cost_through_swaps():
    buys = [
        (1, "buy", 100.0, 100.0, "EUR", "USDC", 10, "w"),
        (2, "buy", 0.0, 5.0, "EUR", "ABC", 20, "w"),  # airdrop
    ]
    swaps = [(1, 30, "USDC", 40.0, "w", "BTC", 0.001, "w", None, None)]
    df = tools.compute_cost_basis(buys, swaps).set_index("Token")
    assert df.loc["USDC", "Quantity"] == pytest.approx(60.0)
    assert df.loc["USDC", "Cost"] == pytest.approx(60.0)
    assert df.loc["BTC", "Cost"] == pytest.approx(40.0)
    assert df.loc["ABC", "Cost"] == 0.0


def test_compute_cost_basis_drops_fully_spent_token():
    buys = [(1, "buy", 50.0, 50.0, "EUR", "USDC", 10, "w")]
    swaps = [(1, 20, "USDC", 50.0, "w", "ETH", 0.02, "w", None, None)]
    df = tools.compute_cost_basis(buys, swaps)
    assert list(df["Token"]) == ["ETH"]
    assert df.iloc[0]["Cost"] == pytest.approx(50.0)
