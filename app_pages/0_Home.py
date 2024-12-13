import os
import streamlit as st
from modules.plotter import plot_as_graph


st.title("Crypto Update")

# session state variable
if "options" not in st.session_state:
    st.session_state.options = []
if "options_save" not in st.session_state:
    st.session_state.options_save = []

# get last values
last = st.session_state.database["balance"].tail(1)
balance = last.sum(axis=1).values[0] if not last.empty else 0
balance = round(balance, 2)

# show wallet value
st.header("Wallet value : " + str(balance) + " €")

plot_as_graph(st.session_state.database["sum"])

# show last values
st.header("Last values")
last_u = last.astype(str) + " €"
st.write(last_u)

if st.session_state.settings["debug_flag"]:
    st.write(st.session_state)
