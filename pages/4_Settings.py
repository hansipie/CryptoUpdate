import os
import streamlit as st
import configparser
import traceback 

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
    with open(configfilepath, 'w') as configfile:
        config.write(configfile)
else:
    config.read(configfilepath)

with st.form(key="settings"):
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
            st.stop()
    except Exception as e:
        st.error("Error: " + type(e).__name__ + " - " + str(e))
        traceback.print_exc()
        submit_button = st.form_submit_button(
            label="Save",
            help="Save settings.",
            use_container_width=True,
            disabled=True
        )
        st.stop()
