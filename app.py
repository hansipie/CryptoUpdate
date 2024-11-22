import streamlit as st
import logging
import sys

st.set_page_config(layout="wide", page_title="CryptoUpdate", page_icon="📈")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(name)s - %(pathname)s:%(lineno)d - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],  # Configurer pour écrire sur stdout
)

logger = logging.getLogger(__name__)

home_page = st.Page("app_pages/0_Home.py", title="Home", icon="🏠", default=True)
pfolio_page = st.Page("app_pages/1_Portfolio.py", title="Portfolio", icon="📊")
wallets_page = st.Page("app_pages/2_Wallets.py", title="Wallets", icon="💰")
import_page = st.Page("app_pages/3_Import.py", title="Import", icon="📥")
update_page = st.Page("app_pages/4_Update.py", title="Update", icon="🔄")
settings_page = st.Page("app_pages/5_Settings.py", title="Settings", icon="⚙️")


pg = st.navigation([home_page, pfolio_page, wallets_page, import_page, update_page, settings_page])

pg.run()
