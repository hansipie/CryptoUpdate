import streamlit as st
import logging
import sys
from modules import process
from modules.database.historybase import HistoryBase as hb
from modules.configuration import configuration as cfg
from modules.database.portfolios import Portfolios as pf

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
    st.error("Settings file not found. Please check your settings.")
    st.stop()

process.loadSettings(config.conf)

home_page = st.Page("app_pages/0_Home.py", title="Home", icon="🏠", default=True)
pfolios_page = st.Page("app_pages/1_Portfolios.py", title="Portfolios", icon="📊")
thematics_page = st.Page("app_pages/1_1_Thematics.py", title="Thematics", icon="📊")
wallets_page = st.Page("app_pages/2_Wallets.py", title="Wallets", icon="💰")
operations_page = st.Page("app_pages/3_Operations.py", title="Operations", icon="💱")
import_page = st.Page("app_pages/4_Import.py", title="Import", icon="📥")
update_page = st.Page("app_pages/5_Update.py", title="Update", icon="🔄")
settings_page = st.Page("app_pages/6_Settings.py", title="Settings", icon="⚙️")

pg = st.navigation(
    [
        home_page,
        pfolios_page,
        thematics_page,
        wallets_page,
        operations_page,
        import_page,
        update_page,
        settings_page,
    ]
)
if st.session_state.settings["debug_flag"]:
    st.write("Debug mode is ON")
pg.run()

logger.debug("### End Render ###")
