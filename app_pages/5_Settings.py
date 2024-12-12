import streamlit as st
import traceback
import logging

from modules.Notion import Notion
from modules.configuration import configuration as Configuration

logger = logging.getLogger(__name__)

st.title("Settings")


@st.fragment
def notionUI():
    st.write("Notion Setup")
    with st.form(key="notion_setup"):
        try:
            notion = Notion(st.session_state.notion_token)
        except Exception as e:
            st.error("Error: " + type(e).__name__ + " - " + str(e))
            st.error("Please set your Notion API Key")
            traceback.print_exc()
            st.stop()

        notion_database = st.text_input(
            "Database name", key="notion_database", value=st.session_state.get("notion_database", "")
        )
        notion_parentpage = st.text_input(
            "Parent page", key="notion_parentpage", value=st.session_state.get("notion_parentpage", "")
        )
        create = st.checkbox("Create Database", value=False)
        submit_button = st.form_submit_button(
            label="Save",
            help="Set Database from Notion.",
            use_container_width=True,
        )
        if submit_button:
            Configuration().saveConfig(st.session_state)

        if (
            st.session_state.notion_database != ""
            and st.session_state.notion_parentpage != ""
            and create
        ):
            with st.spinner("Creating database..."):
                dbid = notion.createDatabase(
                    st.session_state.notion_database, st.session_state.notion_parentpage
                )
                if dbid is None:
                    st.error("Database not created. Please check your settings.")
                elif dbid == "DB_EXISTS":
                    st.warning(
                        "Database already exists: " + st.session_state.notion_database
                    )
                else:
                    st.success("Database created: " + dbid)


@st.fragment
def apikeyUI():
    logger.debug("API Keys")
    with st.form(key="apikeys_setup"):
        disabled = False
        try:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Notion")
                notion_token = st.text_input(
                    "Notion API token",
                    key="notion_token",
                    type="password",
                    value=st.session_state.get("notion_token", "")
                )
            with col2:
                st.subheader("Coinmarketcap")
                coinmarketcap_token = st.text_input(
                    "Coinmarketcap API token",
                    key="coinmarketcap_token",
                    type="password",
                    value=st.session_state.get("coinmarketcap_token", "")
                )
            with col1:
                st.subheader("OpenAI")
                openai_token = st.text_input(
                    "OpenAI API token",
                    key="openai_token",
                    type="password",
                    value=st.session_state.get("openai_token", "")
                )
            with col2:
                st.subheader("Debug")
                debug_flag = st.checkbox(
                    "Debug",
                    key="debug_flag",
                    value=st.session_state.get("debug_flag", False)
                )

        except Exception as e:
            st.error("Error: " + type(e).__name__ + " - " + str(e))
            traceback.print_exc()
            disabled = True
        submitted = st.form_submit_button(
            label="Save",
            help="Save settings.",
            use_container_width=True,
            disabled=disabled,
        )
        if submitted:
            logger.debug("Submitted")
            Configuration().saveConfig(st.session_state)


sheduler_tab, notion_tab, apikeys_tab = st.tabs(
    ["Sheduler", "Notion Setup", "API Keys"]
)

with sheduler_tab:
    st.write("Sheduler")
with notion_tab:
    notionUI()
with apikeys_tab:
    apikeyUI()

st.write(st.session_state)
