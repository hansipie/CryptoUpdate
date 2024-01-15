import os
import streamlit as st
from st_pages import Page, add_page_title, show_pages
from modules.data import Data

show_pages(
    [
        Page("0_Home.py", "Home", "🏠"),
        Page("pages/1_Wallets.py", "Wallets", "💰"),
        Page("pages/2_Import.py", "Import", "📥"),
        Page("pages/3_Update.py", "Update", "🔄"),
        Page("pages/4_Settings.py", "Settings", "⚙️")
    ]
)

st.set_page_config(layout="wide")
add_page_title("WalletVision")

configfilepath = "./data/settings.ini"
if not os.path.exists(configfilepath):
    st.error("Please set your settings in the settings page")
    st.stop()
    
db_path = "./data/db.sqlite3"

# get dataframes from archives

with st.spinner("Extracting data..."):
    data = Data(db_path)
    df_sum = data.df_sum
    df_balances = data.df_balance

# session state variable
if "options" not in st.session_state:
    st.session_state.options = []
if "options_save" not in st.session_state:
    st.session_state.options_save = []

# get last values
last = df_balances.tail(1)
balance = (last.sum(axis=1).values[0] if not last.empty else 0)
balance = round(balance, 2)

# show wallet value
st.header("Wallet value : " + str(balance) + " €")
st.line_chart(df_sum)

# show last values
st.header("Last values")
last_u = last.astype(str) + " €"
st.write(last_u)

if st.checkbox("Clear cache"):
    st.cache_data.clear()
