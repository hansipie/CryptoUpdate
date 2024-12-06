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

configfilepath = "./data/settings.ini"
if not os.path.exists(configfilepath):
    st.error("Please set your settings in the settings page")
    st.stop()

config = configparser.ConfigParser()
config.read(configfilepath)

try:
    # read config
    notion_api_token = config["DEFAULT"]["notion_token"]
    coinmarketcap_api_token = config["DEFAULT"]["coinmarketcap_token"]
    database = config["Notion"]["database"]
    parent_page = config["Notion"]["parent_page"]
    debug = True if config["DEFAULT"]["debug"] == "True" else False
    archive_path = config["Local"]["archive_path"]
    data_path = config["Local"]["data_path"]
    dbfile = os.path.join(data_path, config["Local"]["sqlite_file"])
except KeyError as ke:
    st.error("Error: " + type(ke).__name__ + " - " + str(ke))
    st.error("Please set your settings in the settings page")
    traceback.print_exc()
    st.stop()
except Exception as e:
    st.error("Error: " + type(e).__name__ + " - " + str(e))
    traceback.print_exc()
    st.stop()

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
                notion = Notion(notion_api_token)
                db_id = notion.getObjectId(database, "database", parent_page)
                if db_id == None:
                    st.error("Error: Database not found")
                    st.stop()
                updater = Updater(coinmarketcap_api_token, notion_api_token, db_id)
                updater.getCryptoPrices(debug=debug)
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
                exporter = Exporter(notion_api_token, archive_path)
                csvfile = exporter.GetCSVfile(database)
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
if not os.path.exists(archive_path):
    os.makedirs(archive_path)

with st.form(key="process_archives"):
    with st.spinner("Listing archives..."):
        archiveFiles = list(
            filter(lambda x: x.endswith(".csv"), listfilesrecursive(archive_path))
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
            conn = sqlite3.connect(dbfile)
            migrate_bar = st.progress(0)
            count = 0
            for item in archiveFiles:
                logger.debug(f"Inserting {item}")
                migrate_bar.progress(
                    count / len(archiveFiles), text=f"Inserting {item}"
                )
                if item.endswith(".csv"):
                    df = getDateFrame(item)
                    df.to_sql("Database", conn, if_exists="append", index=False)
                else:
                    logger.debug(f"ignore: {item}")
                count += 1
            migrate_bar.progress(100, text="Done")
            dropDuplicate(conn)
            conn.close()

            # st.write("Clear archives...")
            # # lambda function to filter archivedir to only folders
            # archivedirsitems = list(
            #     filter(
            #         lambda x: (x.endswith(".csv") or x.isnumeric()),
            #         os.listdir(archive_path),
            #     )
            # )
            # logger.debug(f"Delete list: {archivedirsitems}")
            # delete_bar = st.progress(0)
            # count = 0
            # for item in archivedirsitems:
            #     delete_bar.progress(
            #         count / len(archivedirsitems), text=f"Deleting {item}"
            #     )
            #     itempath = os.path.join(archive_path, item)
            #     if os.path.isdir(itempath):
            #         shutil.rmtree(itempath, ignore_errors=True)
            #     else:
            #         try:
            #             os.remove(itempath)
            #         except Exception as e:
            #             logger.debug(f"Exception: {e}")
            #     count += 1

            # delete_bar.progress(100, text="Done")

            st.cache_data.clear()

st.divider()
st.write(st.session_state.database)