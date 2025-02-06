import streamlit as st
import logging

from modules.Notion import Notion
from modules.configuration import configuration as Configuration

logger = logging.getLogger(__name__)


def createNotionDB():
    """Create a new Notion database for cryptocurrency tracking.
    
    Attempts to create database using configured settings.
    Shows success/failure status messages.
    """
    notion = Notion(st.session_state.notion_token)
    with st.spinner("Creating database..."):
        dbid = notion.createDatabase(
            st.session_state.notion_database, st.session_state.notion_parentpage
        )
        if dbid is None:
            st.error("Database not created. Please check your settings.")
        elif dbid == "DB_EXISTS":
            st.warning("Database already exists: " + st.session_state.notion_database)
        else:
            st.success("Database created: " + dbid)


st.title("Settings")

if "settings" not in st.session_state:
    st.session_state.settings = {}

with st.form(key="settings_form"):

    st.subheader("Notion")
    notion_token = st.text_input(
        "Notion API token",
        key="notion_token",
        type="password",
        value=st.session_state.settings.get("notion_token"),
    )
    notion_database = st.text_input(
        "Database name",
        key="notion_database",
        value=st.session_state.settings.get("notion_database"),
    )
    notion_parentpage = st.text_input(
        "Parent page",
        key="notion_parentpage",
        value=st.session_state.settings.get("notion_parentpage"),
    )

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
        st.session_state.settings["notion_token"] = notion_token
        st.session_state.settings["notion_database"] = notion_database
        st.session_state.settings["notion_parentpage"] = notion_parentpage
        st.session_state.settings["coinmarketcap_token"] = coinmarketcap_token
        st.session_state.settings["openai_token"] = openai_token
        st.session_state.settings["debug_flag"] = debug_flag

        conf = Configuration()
        conf.saveConfig(st.session_state.settings)

