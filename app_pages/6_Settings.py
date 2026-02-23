import logging

import requests
import streamlit as st

from modules.configuration import Configuration

logger = logging.getLogger(__name__)

st.title("Settings")

if "settings" not in st.session_state:
    st.session_state.settings = {}

# Initialize fiat currency in session state if not already set
if "fiat_currency" not in st.session_state:
    st.session_state.fiat_currency = st.session_state.settings.get(
        "fiat_currency", "EUR"
    )

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


with st.sidebar:
    st.subheader("Status")
    _status = _check_marketraccoon(
        st.session_state.settings.get("marketraccoon_url", ""),
        st.session_state.settings.get("marketraccoon_token", ""),
    )
    if _status == "ok":
        st.success("MarketRaccoon: up")
    elif _status == "down":
        st.error("MarketRaccoon: down")
    elif _status == "connection_error":
        st.error("MarketRaccoon: unreachable")
        logger.error("Connection error during API healthcheck.")
    elif _status == "timeout":
        st.error("MarketRaccoon: timeout")
        logger.error("API request timed out.")

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

    st.subheader("Coinmarketcap")
    coinmarketcap_token = st.text_input(
        "Coinmarketcap API token",
        key="coinmarketcap_token",
        type="password",
        value=st.session_state.settings.get("coinmarketcap_token"),
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
        st.session_state.settings["marketraccoon_url"] = marketraccoon_url
        st.session_state.settings["marketraccoon_token"] = marketraccoon_token
        st.session_state.settings["coinmarketcap_token"] = coinmarketcap_token
        st.session_state.settings["ai_apitoken"] = ai_apitoken
        st.session_state.settings["debug_flag"] = debug_flag
        st.session_state.settings["operations_green_threshold"] = (
            operations_green_threshold
        )
        st.session_state.settings["operations_orange_threshold"] = (
            operations_orange_threshold
        )
        st.session_state.settings["operations_red_threshold"] = operations_red_threshold
        st.session_state.settings["fiat_currency"] = fiat_currency
        st.session_state.fiat_currency = fiat_currency

        conf = Configuration()
        conf.save_config(st.session_state.settings)
        st.success("Settings saved successfully!")
        _check_marketraccoon.clear()
