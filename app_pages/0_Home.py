import streamlit as st
from modules.plotter import plot_as_graph
from modules.process import load_db


st.title("Crypto Update")

df_balance, df_sums, _, _ = load_db(st.session_state.dbfile)

# session state variable
if "options" not in st.session_state:
    st.session_state.options = []
if "options_save" not in st.session_state:
    st.session_state.options_save = []

# get last values
last = df_balance.tail(1)
balance = last.sum(axis=1).values[0] if not last.empty else 0
balance = round(balance, 2)

# show wallet value
st.header("Wallet value : " + str(balance) + " €")

plot_as_graph(df_sums)

# show last values
st.header("Last values")
last_u = last.astype(str) + " €"
st.write(last_u)

if st.session_state.settings["debug_flag"]:
    st.write(st.session_state)
