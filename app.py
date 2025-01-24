"""Main entry point for CryptoUpdate application.

This module initializes the Streamlit application, sets up logging,
loads configuration and defines the navigation structure.
The application provides a web interface for tracking and managing
cryptocurrency portfolios.
"""

import streamlit as st
import logging
import sys
from modules import tools
from modules.configuration import configuration as cfg

st.set_page_config(layout="wide", page_title="CryptoUpdate", page_icon="📈")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(name)s - %(pathname)s:%(lineno)d - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],  # Configurer pour écrire sur stdout
)

logger = logging.getLogger(__name__)

logger.debug("### Start Render ###")

config = cfg()
try:
    config.readConfig()
except FileNotFoundError:
    st.error("Settings file not found. Please verify your configuration file exists and is accessible.")
    st.stop()

tools.load_settings(config.conf)

home_page = st.Page("app_pages/0_Home.py", title="Home", icon="🏠", default=True)
pfolios_page = st.Page("app_pages/1_Portfolios.py", title="Portfolios", icon="📊")
tools_page = st.Page("app_pages/1_Tools.py", title="Tools", icon="🛠️")
graphs_page = st.Page("app_pages/2_Graphs.py", title="Graphs", icon="💰")
operations_page = st.Page("app_pages/3_Operations.py", title="Operations", icon="💱")
import_page = st.Page("app_pages/4_Import.py", title="Import", icon="📥")
settings_page = st.Page("app_pages/6_Settings.py", title="Settings", icon="⚙️")

pg = st.navigation(
    {
        "Main": [home_page, pfolios_page, tools_page, graphs_page],
        "Inputs": [operations_page, import_page],
        "Settings": [settings_page],
    }
)
if st.session_state.settings["debug_flag"]:
    st.write("Debug mode is ON")
pg.run()

logger.debug("### End Render ###")

if st.session_state.settings["debug_flag"]:
    st.write(st.session_state)
