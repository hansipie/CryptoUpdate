import logging

import requests
import streamlit as st

from modules.configuration import configuration as Configuration

logger = logging.getLogger(__name__)

st.title("Settings")

if "settings" not in st.session_state:
    st.session_state.settings = {}

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

        conf = Configuration()
        conf.saveConfig(st.session_state.settings)
