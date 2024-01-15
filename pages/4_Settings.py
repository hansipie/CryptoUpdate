import os
import streamlit as st
import configparser
import traceback

from modules.Notion import Notion 

st.set_page_config(layout="wide")
st.title("Settings")

if not os.path.exists("./data"):
    os.makedirs("./data")

configfilepath = "./data/settings.ini"

config = configparser.ConfigParser()
if not os.path.exists(configfilepath):
    config['DEFAULT'] = {
        'notion_token': '',
        'coinmarketcap_token': '',
        'openai_token': '',
        'debug': 'False',
    }
    config['Notion'] = {
        'database': '',
        'parent_page': ''
    }
    with open(configfilepath, 'w') as configfile:
        config.write(configfile)
else:
    config.read(configfilepath)

sheduler_tab, notion_tab, apikeys_tab  = st.tabs(["Sheduler", "Notion Setup", "API Keys"])

with sheduler_tab:
    st.write("Sheduler")
with notion_tab:
    st.write("Notion Setup")
    with st.form(key="notion_setup"):
        try:
            notion = Notion(config["DEFAULT"]["notion_token"])
        except Exception as e:
            st.error("Error: " + type(e).__name__ + " - " + str(e))
            st.error("Please set your Notion API Key")
            traceback.print_exc()
            st.stop()
        try:
            db_name = st.text_input("Database name", value=config["Notion"]["database"])
        except Exception as e:
            db_name = st.text_input("Database name", value="")
        try:
            parentpage_name = st.text_input("Parent page", value=config["Notion"]["parent_page"])
        except Exception as e:
            parentpage_name = st.text_input("Parent page", value="")

        create = st.checkbox("Create Database", value=False) 

        submit_button = st.form_submit_button(
            label="Save",
            help="Set Database from Notion.",
            use_container_width=True,
        )
        if submit_button:
            config['Notion'] = {
                'database': f'{db_name}',
                'parent_page': f'{parentpage_name}',
                'lastupdate_database': 'LastUpdate'
            }
            with open(configfilepath, 'w') as configfile:
                config.write(configfile)

        if db_name != "" and parentpage_name != "" and create:
            with st.spinner("Creating database..."):
                dbid = notion.createDatabase(db_name, parentpage_name)
                if dbid is None:
                    st.error("Database not created. Please check your settings.")
                elif dbid == "DB_EXISTS":
                    st.warning("Database already exists: " + db_name)
                else:
                    st.success("Database created: " + dbid)
            

with apikeys_tab:
    with st.form(key="apikeys_setup"):
        try:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Notion")
                notion_token = st.text_input("Notion API token", value=config["DEFAULT"]["notion_token"])
            with col2:
                st.subheader("Coinmarketcap")
                coinmarketcap_token = st.text_input("Coinmarketcap API token", value=config["DEFAULT"]["coinmarketcap_token"])
            with col1:
                st.subheader("OpenAI")
                openai_token = st.text_input("OpenAI API token", value=config["DEFAULT"]["openai_token"])
            with col2:
                st.subheader("Debug")
                debug = st.checkbox("Debug", value=(True if config["DEFAULT"]["debug"] == "True" else False))

            submit_button = st.form_submit_button(
                label="Save",
                help="Save settings.",
                use_container_width=True,
            )
            if submit_button:
                config["DEFAULT"]["notion_token"] = notion_token
                config["DEFAULT"]["coinmarketcap_token"] = coinmarketcap_token
                config["DEFAULT"]["openai_token"] = openai_token
                config["DEFAULT"]["debug"] = str(debug)
                with open(configfilepath, 'w') as configfile:
                    config.write(configfile)
        except Exception as e:
            st.error("Error: " + type(e).__name__ + " - " + str(e))
            traceback.print_exc()
            submit_button = st.form_submit_button(
                label="Save",
                help="Save settings.",
                use_container_width=True,
                disabled=True
            )
