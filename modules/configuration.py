import configparser
import logging
import os
import streamlit as st

from modules import process

logger = logging.getLogger(__name__)

class configuration:

    def __init__(self, inifile: str = "./data/settings.ini"):
        with st.spinner("Loading configuration..."):
            logger.debug("Loading configuration")
            self.inifile = inifile
            self.conf = None
            if not os.path.exists(inifile):
                logger.error("Ini file not found")
                raise FileNotFoundError("Ini file not found")
            self.__readConfig()

    def __readConfig(self):
        self.conf = configparser.ConfigParser()
        self.conf.read(self.inifile)

        try:
            # APIKeys
            if "debug_flag" not in st.session_state:    
                st.session_state.debug_flag = True if self.conf["APIKeys"]["debug"] == "True" else False
            if "notion_token" not in st.session_state:
                st.session_state.notion_token = self.conf["APIKeys"]["notion_token"]
            if "coinmarketcap_token" not in st.session_state:
                st.session_state.coinmarketcap_token = self.conf["APIKeys"]["coinmarketcap_token"]
            if "openai_token" not in st.session_state:
                st.session_state.openai_token = self.conf["APIKeys"]["openai_token"]

            # Notion
            if "notion_database" not in st.session_state:
                st.session_state.notion_database = self.conf["Notion"]["database"]
            if "notion_parentpage" not in st.session_state:
                st.session_state.notion_parentpage = self.conf["Notion"]["parent_page"]

            # Local
            debug_flag = True if self.conf["APIKeys"]["debug"] == "True" else False
            st.session_state.archive_path = os.path.join(os.getcwd(), process.prefix(self.conf["Local"]["archive_path"], debug_flag))
            st.session_state.data_path = os.path.join(os.getcwd(), self.conf["Local"]["data_path"])
            st.session_state.dbfile = os.path.join(st.session_state.data_path, process.prefix(self.conf["Local"]["sqlite_file"], debug_flag))
        except KeyError as ke:
            logger.error("Error: " + type(ke).__name__ + " - " + str(ke))
            raise KeyError("Error Ini file: " + type(ke).__name__ + " - " + str(ke))

    def saveConfig(self, session_state):
        try:
            self.syncConfig(session_state)
            with open(self.inifile, "w") as configfile:
                self.conf.write(configfile)
        except Exception as e:
            st.error("Error: " + type(e).__name__ + " - " + str(e))
            logger.error("Error: " + type(e).__name__ + " - " + str(e))
            quit()

    def syncConfig(self, session_state):
        logger.debug("Sync Config")

        # APIKeys section
        self.conf["APIKeys"]["debug"] = str(session_state.debug_flag)
        self.conf["APIKeys"]["notion_token"] = session_state.notion_token
        self.conf["APIKeys"]["coinmarketcap_token"] = session_state.coinmarketcap_token
        self.conf["APIKeys"]["openai_token"] = session_state.openai_token

        # Notion section
        self.conf["Notion"]["database"] = session_state.notion_database
        self.conf["Notion"]["parent_page"] = session_state.notion_parentpage
