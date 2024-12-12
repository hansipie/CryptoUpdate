import os
import shutil
import sqlite3
import configparser
import streamlit as st
import traceback
import logging
from modules.Exporter import Exporter
from modules.Notion import Notion
from modules.Updater import Updater
from modules.process import getDateFrame, dropDuplicate, listfilesrecursive

logger = logging.getLogger(__name__)

with st.form(key="update_database"):
    submit_button = st.form_submit_button(
        label="Update Notion database",
        help="Update the Notion database with the current market values.",
        use_container_width=True,
    )
    if submit_button:
        st.write("Updating database...")

        with st.spinner("Getting current marketprices..."):
            try:
                notion = Notion(st.session_state.notion_token)
                db_id = notion.getObjectId(st.session_state.notion_database, "database", st.session_state.notion_parentpage)
                if db_id == None:
                    st.error("Error: Database not found")
                    st.stop()
                updater = Updater(st.session_state.coinmarketcap_token, st.session_state.notion_token, db_id)
                updater.getCryptoPrices(debug=st.session_state.debug_flag)
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
        updatetokens_bar.progress(100, text="Done")

        with st.spinner("Updating last update..."):
            updater.UpdateLastUpdate()

        with st.spinner("Exporting database..."):
            try:
                exporter = Exporter(st.session_state.notion_token, st.session_state.archive_path)
                csvfile = exporter.GetCSVfile(st.session_state.notion_database)
            except KeyError as ke:
                st.error("Error: " + type(ke).__name__ + " - " + str(ke))
                st.error("Please set your settings in the settings page")
                traceback.print_exc()
                st.stop()
            except Exception as e:
                st.error("Error: " + type(e).__name__ + " - " + str(e))
                traceback.print_exc()
                st.stop()
            st.write("Output file: ", csvfile)

# create archive dir if not exists
if not os.path.exists(st.session_state.archive_path):
    os.makedirs(st.session_state.archive_path)

with st.form(key="process_archives"):
    with st.spinner("Listing archives..."):
        archiveFiles = list(
            filter(lambda x: x.endswith(".csv"), listfilesrecursive(st.session_state.archive_path))
        )
    st.write("Archives count:", len(archiveFiles))

    submit_button = st.form_submit_button(
        label="Process archives",
        help="Process archives directories and migrate them to the application database.",
        use_container_width=True,
    )
    if submit_button:
        if len(archiveFiles) == 0:
            st.warning("No archives found.")
        else:
            st.write("Found in archives: ", archiveFiles)
            conn = sqlite3.connect(st.session_state.dbfile)
            migrate_bar = st.progress(0)
            count = 0
            for item in archiveFiles:
                logger.debug(f"Inserting {item}")
                migrate_bar.progress(
                    count / len(archiveFiles), text=f"Inserting {item}"
                )
                if item.endswith(".csv"):
                    df = getDateFrame(item)
                    logger.debug(f"Inserting {df}")
                    df.to_sql("Database", conn, if_exists="append", index=False)
                else:
                    logger.debug(f"ignore: {item}")
                count += 1
            migrate_bar.progress(100, text="Done")
            dropDuplicate(conn)
            conn.close()

            st.cache_data.clear()

with st.expander("Debug"):
    st.write(st.session_state)
