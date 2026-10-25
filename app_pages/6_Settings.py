import logging
from urllib.parse import urlparse

import requests
import streamlit as st

from modules.configuration import Configuration
from modules.swap_push import check_status as check_tradbot
from modules.swap_push import is_allowed_url

logger = logging.getLogger(__name__)

st.title("Settings")

if "settings" not in st.session_state:
    st.session_state.settings = {}


@st.cache_data(ttl=30, show_spinner=False)
def _check_marketraccoon(url: str, api_key: str) -> str:
    """Vérifie la disponibilité de l'API MarketRaccoon (résultat mis en cache 30s)."""
    try:
        headers = {"X-API-Key": api_key} if api_key else {}
        response = requests.get(f"{url}/api/healthcheck", headers=headers, timeout=5)
        return "ok" if response.status_code == 200 else "down"
    except requests.ConnectionError:
        return "connection_error"
    except requests.Timeout:
        return "timeout"
    except requests.exceptions.MissingSchema:
        return "invalid_url"
    except requests.exceptions.RequestException:
        return "request_error"


@st.cache_data(ttl=30, show_spinner=False)
def _check_tradbot(url: str, token: str) -> str:
    """Probe the tradbot service without side effects (cached for 30s)."""
    return check_tradbot(url, token)


# state -> (streamlit level, icon, caption)
_TRADBOT_STATES = {
    "ok": ("success", ":material/check_circle:", None),
    "no_token": ("warning", ":material/key_off:", "No token set"),
    "unauthorized": ("error", ":material/lock:", "Token rejected by the bot"),
    "push_disabled": (
        "warning",
        ":material/block:",
        "Push disabled on the bot (SWAPS_API_TOKEN not set)",
    ),
    "blocked": ("error", ":material/shield:", "Blocked by a proxy/firewall (403)"),
    "down": ("error", ":material/cancel:", "The bot does not respond correctly"),
    "timeout": ("error", ":material/timer_off:", "Timed out"),
    "connection_error": ("error", ":material/link_off:", "Cannot reach the bot"),
    "invalid_url": ("error", ":material/error:", "The URL must be https"),
}


with st.sidebar:
    st.subheader("Status")
    _status = _check_marketraccoon(  # pylint: disable=invalid-name
        st.session_state.settings.get("marketraccoon_url", ""),
        st.session_state.settings.get("marketraccoon_token", ""),
    )
    if _status == "ok":
        st.success("MarketRaccoon :material/check_circle:")
    elif _status == "down":
        st.error("MarketRaccoon :material/cancel:")
    elif _status == "connection_error":
        st.error("MarketRaccoon :material/link_off:")
        logger.error("Connection error during API healthcheck.")
    elif _status == "timeout":
        st.error("MarketRaccoon :material/timer_off:")
        logger.error("API request timed out.")
    elif _status == "invalid_url":
        st.error("MarketRaccoon :material/error:")
        logger.error("Invalid MarketRaccoon URL format.")
    elif _status == "request_error":
        st.error("MarketRaccoon :material/warning:")
        logger.error("Unhandled request error during API healthcheck.")

    _tradbot_state = _check_tradbot(  # pylint: disable=invalid-name
        st.session_state.settings.get("tradbot_url", ""),
        st.session_state.settings.get("tradbot_token", ""),
    )
    if _tradbot_state == "not_configured":
        st.info("Tradbot :material/remove_circle_outline:")
    else:
        _level, _icon, _caption = _TRADBOT_STATES.get(
            _tradbot_state, ("error", ":material/warning:", _tradbot_state)
        )
        getattr(st, _level)(f"Tradbot {_icon}")
        if _caption:
            st.caption(_caption)
        if _level == "error":
            logger.error("Tradbot status check failed: %s", _tradbot_state)

with st.form(key="settings_form"):
    st.subheader("MarketRaccoon")
    marketraccoon_url = st.text_input(
        "MarketRaccoon URL",
        key="marketraccoon_url",
        value=st.session_state.settings.get("marketraccoon_url"),
    )
    marketraccoon_token = st.text_input(
        "MarketRaccoon API token",
        key="marketraccoon_token",
        type="password",
        value=st.session_state.settings.get("marketraccoon_token", ""),
    )

    ratesdb_url = st.text_input(
        "RatesDB URL",
        key="ratesdb_url",
        value=st.session_state.settings.get(
            "ratesdb_url", "https://free.ratesdb.com/v1/rates"
        ),
        help="Fallback API URL for historical EUR/USD rates",
    )

    st.subheader("Coinmarketcap")
    coinmarketcap_token = st.text_input(
        "Coinmarketcap API token",
        key="coinmarketcap_token",
        type="password",
        value=st.session_state.settings.get("coinmarketcap_token"),
    )

    st.subheader("Tradbot")
    tradbot_url = st.text_input(
        "Tradbot URL",
        key="tradbot_url",
        value=st.session_state.settings.get("tradbot_url", ""),
        placeholder="https://bot.example.com",
        help="Base URL of the tradbot service that receives the swaps. "
        "Leave empty to disable the push.",
    )
    tradbot_token = st.text_input(
        "Tradbot API token",
        key="tradbot_token",
        type="password",
        value=st.session_state.settings.get("tradbot_token", ""),
        help="Bearer secret, same value as SWAPS_API_TOKEN on the bot",
    )

    st.subheader("AI")
    ai_apitoken = st.text_input(
        "AI API token (Anthropic)",
        key="ai_apitoken",
        type="password",
        value=st.session_state.settings.get("ai_apitoken"),
    )

    st.subheader("Debug")
    debug_flag = st.checkbox(
        "Debug",
        key="debug_flag",
        value=st.session_state.settings.get("debug_flag"),
    )

    st.subheader("Currency")
    fiat_currencies = ["EUR", "USD"]
    fiat_currency = st.selectbox(
        "Reference fiat currency",
        key="fiat_currency_select",
        options=fiat_currencies,
        index=fiat_currencies.index(
            st.session_state.settings.get("fiat_currency", "EUR")
        )
        if st.session_state.settings.get("fiat_currency", "EUR") in fiat_currencies
        else 0,
        help="Select the reference currency for price display and conversions",
    )

    st.subheader("Operations Colors")
    st.write("Configure color thresholds for performance indicators in Operations tab:")

    col1, col2, col3 = st.columns(3)
    with col1:
        operations_green_threshold = st.number_input(
            "Green threshold (%)",
            key="operations_green_threshold",
            value=st.session_state.settings.get("operations_green_threshold", 100),
            min_value=0,
            max_value=1000,
            step=1,
            help="Performance >= this value will be colored green",
        )
    with col2:
        operations_orange_threshold = st.number_input(
            "Orange threshold (%)",
            key="operations_orange_threshold",
            value=st.session_state.settings.get("operations_orange_threshold", 50),
            min_value=0,
            max_value=1000,
            step=1,
            help="Performance >= this value will be colored orange",
        )
    with col3:
        operations_red_threshold = st.number_input(
            "Red threshold (%)",
            key="operations_red_threshold",
            value=st.session_state.settings.get("operations_red_threshold", 0),
            min_value=-1000,
            max_value=1000,
            step=1,
            help="Performance < this value will be colored red",
        )

    submitted = st.form_submit_button(
        label="Save",
        help="Save settings.",
        width="stretch",
    )

    if submitted:
        logger.debug("Submitted")
        marketraccoon_url = marketraccoon_url.strip().rstrip("/")
        ratesdb_url = ratesdb_url.strip().rstrip("/")
        tradbot_url = tradbot_url.strip().rstrip("/")
        tradbot_token = tradbot_token.strip()
        errors = [
            f"{label} must be a valid http(s) URL"
            for label, url in (
                ("MarketRaccoon URL", marketraccoon_url),
                ("RatesDB URL", ratesdb_url),
            )
            if urlparse(url).scheme not in ("http", "https") or not urlparse(url).netloc
        ]
        if tradbot_url and not is_allowed_url(tradbot_url):
            errors.append("Tradbot URL must start with https://")
        if bool(tradbot_url) != bool(tradbot_token):
            errors.append("Tradbot URL and token must be set together (or both empty)")
        if not (
            operations_green_threshold
            >= operations_orange_threshold
            >= operations_red_threshold
        ):
            errors.append("Thresholds must satisfy green >= orange >= red")
        if errors:
            for message in errors:
                st.error(message)
            st.stop()

        st.session_state.settings["marketraccoon_url"] = marketraccoon_url
        st.session_state.settings["marketraccoon_token"] = marketraccoon_token
        st.session_state.settings["ratesdb_url"] = ratesdb_url
        st.session_state.settings["coinmarketcap_token"] = coinmarketcap_token
        st.session_state.settings["ai_apitoken"] = ai_apitoken
        st.session_state.settings["tradbot_url"] = tradbot_url
        st.session_state.settings["tradbot_token"] = tradbot_token
        st.session_state.settings["debug_flag"] = debug_flag
        st.session_state.settings["operations_green_threshold"] = (
            operations_green_threshold
        )
        st.session_state.settings["operations_orange_threshold"] = (
            operations_orange_threshold
        )
        st.session_state.settings["operations_red_threshold"] = operations_red_threshold
        st.session_state.settings["fiat_currency"] = fiat_currency

        conf = Configuration()
        conf.save_config(st.session_state.settings)
        st.success("Settings saved successfully!")
        _check_marketraccoon.clear()
        _check_tradbot.clear()
