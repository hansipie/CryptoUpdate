import os
import shutil
import sqlite3
import configparser
import streamlit as st
import traceback
from modules.Exporter import Exporter
from modules.Notion import Notion
from modules.Updater import Updater
from modules.process import getDateFrame, dropDuplicate

st.set_page_config(layout="centered")

configfilepath = "./data/settings.ini"
if not os.path.exists(configfilepath):
    st.error("Please set your settings in the settings page")
    st.stop()

config = configparser.ConfigParser()
config.read(configfilepath)

try:
    debugflag = (True if config["DEFAULT"]["debug"] == "True" else False)
except KeyError:
    debugflag = False

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
                notion = Notion(config["DEFAULT"]["notion_token"])
                db_id = notion.getObjectId(config["Notion"]["database"], "database", config["Notion"]["parent_page"])
                if db_id == None:
                    st.error("Error: Database not found")
                    st.stop()
                updater = Updater(config["DEFAULT"]["coinmarketcap_token"], config["DEFAULT"]["notion_token"], db_id)
                updater.getCryptoPrices(debug=debugflag)                                                        
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
            count += 1
            updatetokens_bar.progress(int((100 * count)/ len(updater.notion_entries)), text=f"Updating {token}")
            updater.updateNotionDatabase(
                pageId=data['page'],
                coinPrice=data['price']
            )
        updatetokens_bar.progress(100, text="Done")

        with st.spinner("Updating last update..."):
            updater.UpdateLastUpdate()
        
        with st.spinner("Exporting database..."): 
            try:
                exporter = Exporter(config["DEFAULT"]["notion_token"])
                csvfile = exporter.GetCSVfile(config["Notion"]["database"])
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

archivedir = "./archives/"
# create archive dir if not exists
if not os.path.exists(archivedir):
    os.makedirs(archivedir)
# lambda function to filter archivedir to only folders
archivedirs = list(filter(lambda x: os.path.isdir(os.path.join(archivedir, x)), os.listdir(archivedir)))

with st.form(key="process_archives"):
    archivedirs = list(filter(lambda x: os.path.isdir(os.path.join(archivedir, x)), os.listdir(archivedir)))
    st.write("Archives count:", len(archivedirs))
    submit_button = st.form_submit_button(
        label="Process archives",
        help="Process archives directories and migrate them to the application database.",
        use_container_width=True,
    )
    if submit_button:
        if len(archivedirs) == 0:
            st.warning("No archives found.")
        else:
            st.write("Found archives: ", archivedirs)
            dbfile = "./data/db.sqlite3"
            conn = sqlite3.connect(dbfile)

            st.write("Migrating archives...")
            migrate_bar = st.progress(0)
            count = 0
            for folder in archivedirs:
                count += 1
                print(f"Migrating {folder}")
                migrate_bar.progress(int((100 * count)/ len(archivedirs)), text=f"Migrating {folder}")
                if folder.isnumeric():
                    epoch = int(folder)
                    forderpath = os.path.join(archivedir, folder)
                    for file in os.listdir(forderpath):
                        if file.endswith("_all.csv"):
                            continue
                        if file.endswith(".csv"):
                            inputfile = os.path.join(forderpath, file)
                            df = getDateFrame(inputfile, epoch)
                            df.to_sql('Database', conn, if_exists='append', index=False)
            migrate_bar.progress(100, text="Done")

            st.write("Clear archives...")
            delete_bar = st.progress(0)
            count = 0
            for folder in archivedirs:
                count += 1
                delete_bar.progress(int((100 * count)/ len(archivedirs)), text=f"Deleting {folder}")
                forderpath = os.path.join(archivedir, folder)
                if os.path.isdir(forderpath):
                    shutil.rmtree(forderpath, ignore_errors=True)
            delete_bar.progress(100, text="Done")

            dropDuplicate(conn)
            conn.close()
            st.cache_data.clear()