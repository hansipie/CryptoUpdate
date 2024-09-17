import os
import streamlit as st
from modules.data import Data

@st.cache_data(show_spinner=False)
def getData():
    db_path = "./data/db.sqlite3"
    return Data(db_path)

st.title("Crypto Update")

configfilepath = "./data/settings.ini"
if not os.path.exists(configfilepath):
    st.error("Please set your settings in the settings page")
    st.stop()

# get dataframes from archives

with st.spinner("Extracting data..."):
    data = getData()

# session state variable
if "options" not in st.session_state:
    st.session_state.options = []
if "options_save" not in st.session_state:
    st.session_state.options_save = []

# get last values
last = data.df_balance.tail(1)
balance = (last.sum(axis=1).values[0] if not last.empty else 0)
balance = round(balance, 2)

# show wallet value
st.header("Wallet value : " + str(balance) + " €")
st.line_chart(data.df_sum)

# show last values
st.header("Last values")
last_u = last.astype(str) + " €"
st.write(last_u)

if st.checkbox("Clear cache"):
    st.cache_data.clear()
