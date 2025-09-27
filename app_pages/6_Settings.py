import logging

import requests
import streamlit as st

from modules.configuration import configuration as Configuration

logger = logging.getLogger(__name__)

st.title("Settings")

if "settings" not in st.session_state:
    st.session_state.settings = {}

# Initialize fiat currency in session state if not already set
if "fiat_currency" not in st.session_state:
    st.session_state.fiat_currency = st.session_state.settings.get("fiat_currency", "EUR")

with st.form(key="settings_form"):
    st.subheader("MarketRaccoon")
    marketraccoon_url = st.text_input(
        "MarketRaccoon URL",
        key="marketraccoon_url",
        value=st.session_state.settings.get("marketraccoon_url"),
    )

    try:
        response = requests.get(
            f"{marketraccoon_url}/api/healthcheck",
            timeout=5,
        )
        if response.status_code == 200:
            st.success("API is up and running.")
        else:
            st.error("API is down.")
    except requests.ConnectionError:
        st.error("Connection to MarketRaccoon failed.")
        logger.error("Connection error during API healthcheck.")
    except requests.Timeout:
        st.error("API request timed out.")
        logger.error("API request timed out.")

    st.subheader("Coinmarketcap")
    coinmarketcap_token = st.text_input(
        "Coinmarketcap API token",
        key="coinmarketcap_token",
        type="password",
        value=st.session_state.settings.get("coinmarketcap_token"),
    )

    st.subheader("OpenAI")
    openai_token = st.text_input(
        "OpenAI API token",
        key="openai_token",
        type="password",
        value=st.session_state.settings.get("openai_token"),
    )

    st.subheader("Debug")
    debug_flag = st.checkbox(
        "Debug",
        key="debug_flag",
        value=st.session_state.settings.get("debug_flag"),
    )

    st.subheader("Currency")
    fiat_currencies = [
        "USD", "EUR", "GBP", "CHF", "CAD", "AUD", "JPY", 
        "CNY", "KRW", "BRL", "MXN", "INR", "RUB", "TRY"
    ]
    fiat_currency = st.selectbox(
        "Reference fiat currency",
        key="fiat_currency_select",
        options=fiat_currencies,
        index=fiat_currencies.index(st.session_state.settings.get("fiat_currency", "EUR")),
        help="Select the reference currency for price display and conversions"
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
            help="Performance >= this value will be colored green"
        )
    with col2:
        operations_orange_threshold = st.number_input(
            "Orange threshold (%)",
            key="operations_orange_threshold", 
            value=st.session_state.settings.get("operations_orange_threshold", 50),
            min_value=0,
            max_value=1000,
            step=1,
            help="Performance >= this value will be colored orange"
        )
    with col3:
        operations_red_threshold = st.number_input(
            "Red threshold (%)",
            key="operations_red_threshold",
            value=st.session_state.settings.get("operations_red_threshold", 0),
            min_value=-1000,
            max_value=1000,
            step=1,
            help="Performance < this value will be colored red"
        )

    submitted = st.form_submit_button(
        label="Save",
        help="Save settings.",
        use_container_width=True,
    )

    if submitted:
        logger.debug("Submitted")
        st.session_state.settings["marketraccoon_url"] = marketraccoon_url
        st.session_state.settings["coinmarketcap_token"] = coinmarketcap_token
        st.session_state.settings["openai_token"] = openai_token
        st.session_state.settings["debug_flag"] = debug_flag
        st.session_state.settings["operations_green_threshold"] = operations_green_threshold
        st.session_state.settings["operations_orange_threshold"] = operations_orange_threshold
        st.session_state.settings["operations_red_threshold"] = operations_red_threshold
        st.session_state.settings["fiat_currency"] = fiat_currency
        st.session_state.fiat_currency = fiat_currency

        conf = Configuration()
        conf.saveConfig(st.session_state.settings)
        st.success("Settings saved successfully!")
