import streamlit as st
import traceback
import logging
from modules.Notion import Notion
from modules.Updater import Updater

logger = logging.getLogger(__name__)

with st.form(key="update_database"):
    submit_button = st.form_submit_button(
        label="Update Notion database",
        help="Update the Notion database with the current market values.",
        use_container_width=True,
    )
    if submit_button:
        with st.spinner("Getting current marketprices..."):
            try:
                notion = Notion(st.session_state.settings["notion_token"])
                db_id = notion.getObjectId(st.session_state.settings["notion_database"], "database", st.session_state.settings["notion_parentpage"])
                if db_id == None:
                    st.error("Error: Database not found")
                    st.stop()
                else:
                    updater = Updater(st.session_state.dbfile, st.session_state.settings["coinmarketcap_token"], st.session_state.settings["notion_token"], db_id)
                    updater.getCryptoPrices()
            except KeyError as ke:
                st.error("Error: " + type(ke).__name__ + " - " + str(ke))
                st.error("Please set your settings in the settings page")
                traceback.print_exc()
                st.stop()
            except Exception as e:
                st.error("Error: " + type(e).__name__ + " - " + str(e))
                traceback.print_exc()
                st.stop()

        updatetokens_bar = st.progress(0)
        count = 0
        for token, data in updater.notion_entries.items():
            updatetokens_bar.progress(
                count / len(updater.notion_entries), text=f"Updating {token}"
            )
            updater.updateNotionDatabase(pageId=data["page"], coinPrice=data["price"])
            count += 1
        updatetokens_bar.progress(100, text="Update completed")

        with st.spinner("Updating last update timestamp..."):
            updater.UpdateLastUpdate()
