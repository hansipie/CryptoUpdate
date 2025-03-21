"""Home page module for CryptoUpdate application.

This module displays the main dashboard with portfolio metrics,
performance graphs and provides functionality for updating prices
and synchronizing with Notion database.
"""

import logging

import pandas as pd
import streamlit as st

from modules.database.customdata import Customdata
from modules.database.operations import operations
from modules.database.tokensdb import TokensDatabase
from modules.plotter import plot_as_graph
from modules.tools import update

logger = logging.getLogger(__name__)

st.title("Crypto Update")

tokensdb = TokensDatabase(st.session_state.settings["dbfile"])
with st.spinner("Loading balances...", show_time=True):
    df_balance = tokensdb.get_balances()
with st.spinner("Loading sums...", show_time=True):
    df_sums = tokensdb.get_sum_over_time()

# Update prices
with st.sidebar:
    if st.button(
        "Update prices",
        key="update_prices",
        icon=":material/update:",
        use_container_width=True,
    ):
        update()
    # display time since last update
    last_update = Customdata(st.session_state.settings["dbfile"]).get("last_update")
    if last_update:
        last_update = pd.Timestamp.fromtimestamp(float(last_update[0]), tz="UTC")
        last_update = pd.Timestamp.now(tz="UTC") - last_update
        st.markdown(
            " - *Last update: " + str(last_update).split(".", maxsplit=1)[0] + "*"
        )
    else:
        st.markdown(" - *No update yet*")

with st.container(border=True):
    col1, col2, col3 = st.columns(3)
    total = operations(st.session_state.settings["dbfile"]).sum_buyoperations()
    with col1:
        st.metric("Invested", value=f"{total} €")
    with col2:
        # get last values
        balance = (
            0
            if df_balance is None or df_balance.empty
            else df_balance.iloc[-1, 1:].sum()
        )
        balance = round(balance, 2)
        st.metric("Total value", value=f"{balance} €")
    with col3:
        st.metric(
            "Profit",
            value=f"{round(balance - total, 2)} €",
            delta=f"{round((((balance - total) / total) * 100) if total != 0 else 0, 2)} %",
        )

with st.container(border=True):
    if df_sums is None or df_sums.empty:
        st.info("No data available")
    else:
        plot_as_graph(df_sums)

# show last values"
st.header("Last values")
if df_balance is None or df_balance.empty:
    st.info("No data available")
else:
    last_V = df_balance.tail(10).copy()
    # last_V = df_balance.copy()
    last_V = last_V.loc[:, (last_V != 0).any(axis=0)]
    last_V = round(last_V, 2)
    last_V = last_V.astype(str) + " €"
    st.dataframe(last_V)
