import os
import shutil
import sqlite3
from dotenv import load_dotenv
import streamlit as st
from modules.Exporter import Exporter
from modules.Updater import Updater
from modules.process import getDateFrame, dropDuplicate

load_dotenv()

st.set_page_config(layout="centered")

if os.getenv("MY_COINMARKETCAP_APIKEY") is None:
    print("Please set your Coinmarketcap API key in the .env file")
    quit()
if os.getenv("NOTION_API_TOKEN") is None:
    print("Please set your Notion API key in the .env file")
    quit()

# debug flag to not consume the Coinmarketcap API
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
            updater = Updater()
            updater.getCryptoPrices(debug=debugflag)    

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
            exporter = Exporter()
            csvfile = exporter.GetCSVfile(debug=debugflag)
            st.write("Output file: ", csvfile)

archivedir = "./archives/"
# lambda function to filter archivedir to only folders
archivedirs = list(filter(lambda x: os.path.isdir(os.path.join(archivedir, x)), os.listdir(archivedir)))

with st.form(key="process_archives"):

    submit_button = st.form_submit_button(
        label="Process archives",
        help="Process archives directories and migrate them to the application database.",
        use_container_width=True,
    )
    if submit_button:
        archivedirs = list(filter(lambda x: os.path.isdir(os.path.join(archivedir, x)), os.listdir(archivedir)))

        if len(archivedirs) == 0:
            st.warning("No archives found.")
        else:
            st.write("Found archives: ", archivedirs)
            if debugflag:
                dbfile = "./outputs/db_debug.sqlite3"
            else:
                dbfile = "./outputs/db.sqlite3"
            conn = sqlite3.connect(dbfile)

            st.write("Migrating archives...")
            migrate_bar = st.progress(0)
            count = 0
            for folder in archivedirs:
                count += 1
                print(f"Migrating {folder}")
                migrate_bar.progress(int((100 * count)/ len(archivedirs)), text=f"Migrating {folder}")
                if folder.isnumeric() or debugflag:
                    # remove _debug from folder name
                    if debugflag:
                        debugfolder = folder.replace("_debug", "")
                        epoch = int(debugfolder)
                    else:
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
