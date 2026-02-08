"""Home page module for CryptoUpdate application.

This module displays the main dashboard with portfolio metrics,
performance graphs and provides functionality for updating prices
and synchronizing with Notion database.
"""

import logging

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from modules.database.customdata import Customdata
from modules.database.operations import operations
from modules.database.tokensdb import TokensDatabase
from modules.tools import update, parse_last_update, get_currency_symbol

logger = logging.getLogger(__name__)


def plot_total_value(df: pd.DataFrame):
    """Plot total portfolio value over time with modern style.

    Args:
        df: DataFrame with Date index and Sum column
    """
    if df is None or df.empty:
        st.info("No data available")
        return

    # Get target currency from settings
    target_currency = st.session_state.settings.get("fiat_currency", "EUR")
    currency_symbol = get_currency_symbol(target_currency)

    # Create plotly figure
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['Sum'],
        mode='lines',
        name='Total Portfolio Value',
        fill='tozeroy',
        line=dict(width=2)
    ))

    fig.update_layout(
        title="Total Portfolio Value Over Time",
        xaxis_title="Date",
        yaxis_title=f"Value ({currency_symbol})",
        hovermode='x unified',
        height=400
    )

    st.plotly_chart(fig, width="stretch")


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
        width='stretch',
    ):
        update()
    # display time since last update
    last_update = Customdata(st.session_state.settings["dbfile"]).get("last_update")
    if last_update:
        last_update_ts = parse_last_update(last_update)
        last_update = pd.Timestamp.now(tz="UTC") - last_update_ts
        st.markdown(
            " - *Last update: " + str(last_update).split(".", maxsplit=1)[0] + "*"
        )
    else:
        st.markdown(" - *No update yet*")

with st.container(border=True):
    col1, col2, col3 = st.columns(3)
    total = operations(st.session_state.settings["dbfile"]).sum_buyoperations()
    currency_symbol = get_currency_symbol()
    with col1:
        st.metric("Invested", value=f"{total} {currency_symbol}")
    with col2:
        # get last values
        balance = (
            0
            if df_balance is None or df_balance.empty
            else df_balance.iloc[-1, 1:].sum()
        )
        balance = round(balance, 2)
        st.metric("Total value", value=f"{balance} {currency_symbol}")
    with col3:
        st.metric(
            "Profit",
            value=f"{round(balance - total, 2)} {currency_symbol}",
            delta=f"{round((((balance - total) / total) * 100) if total != 0 else 0, 2)} %",
        )

with st.container(border=True):
    plot_total_value(df_sums)

# show last values"
st.header("Last values")
if df_balance is None or df_balance.empty:
    st.info("No data available")
else:
    last_V = df_balance.tail(10).copy()
    # last_V = df_balance.copy()
    last_V = last_V.loc[:, (last_V != 0).any(axis=0)]
    last_V = round(last_V, 2)
    currency_symbol = get_currency_symbol()
    last_V = last_V.astype(str) + f" {currency_symbol}"
    st.dataframe(last_V)
