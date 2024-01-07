from st_pages import Page, add_page_title, show_pages
from modules.data import Data
import os
import streamlit as st

show_pages(
    [
        Page("app.py", "Home", "🏠"),
        Page("pages/wallets.py", "Wallets", "💰"),
        Page("pages/import.py", "Import", "📥"),
        Page("pages/update.py", "Update", "🔄",)
    ]
)

add_page_title("WalletVision")

db_path = os.path.join(os.path.dirname(__file__), "./outputs/db.sqlite3")

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
balance = last.sum(axis=1).values[0]
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
