import pandas as pd
import streamlit as st
import logging
from modules.plotter import plot_as_graph
from modules.process import load_db

logger = logging.getLogger(__name__)

st.title("Crypto Update")

# session state variable
if "options" not in st.session_state:
    st.session_state.options = []
if "options_save" not in st.session_state:
    st.session_state.options_save = []

df_balance, df_sums, _, _ = load_db(st.session_state.dbfile)

# get last values
balance = df_balance.iloc[-1, 1:].sum()
balance = round(balance, 2)

# show wallet value
st.header("Wallet value : " + str(balance) + " €")

plot_as_graph(df_sums)

# show last values"
st.header("Last values")
last_V = df_balance.tail(5).copy()
last_V = last_V.astype(str) + " €"
st.dataframe(last_V)

if st.session_state.settings["debug_flag"]:
    st.write(st.session_state)
