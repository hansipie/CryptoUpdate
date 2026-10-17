"""Home page module for CryptoUpdate application.

This module displays the main dashboard with portfolio metrics,
performance graphs and provides functionality for updating prices
and synchronizing with Notion database.
"""

import logging

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from modules.database.customdata import Customdata
from modules.database.operations import Operations
from modules.database.tokensdb import TokensDatabase
from modules.plotter import mask_figure_amounts
from modules.tools import (
    convert_dataframe_to_target_currency,
    convert_price_to_target_currency,
    get_currency_symbol,
    mask_amount,
    mask_dataframe,
    parse_last_update,
    update,
)

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
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Sum"],
            mode="lines",
            name="Total Portfolio Value",
            fill="tozeroy",
            line={"width": 2},
        )
    )

    fig.update_layout(
        title="Total Portfolio Value Over Time",
        xaxis_title="Date",
        yaxis_title=f"Value ({currency_symbol})",
        hovermode="x unified",
        height=400,
    )

    mask_figure_amounts(fig)
    st.plotly_chart(fig, width="stretch")


st.title("Crypto Update")

tokensdb = TokensDatabase(st.session_state.settings["dbfile"])
with st.spinner("Loading balances...", show_time=True):
    # TokensDatabase stocke les valeurs en EUR : conversion vers la devise des settings
    df_balance = convert_dataframe_to_target_currency(tokensdb.get_balances())
with st.spinner("Loading sums...", show_time=True):
    df_sums = convert_dataframe_to_target_currency(tokensdb.get_sum_over_time())

# Update prices
with st.sidebar:
    if st.button(
        "Update prices",
        key="update_prices",
        icon=":material/update:",
        width="stretch",
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
    invested_by_unit = Operations(
        st.session_state.settings["dbfile"]
    ).sum_buyoperations_by_unit()
    converted_invested = [
        convert_price_to_target_currency(amount, unit)
        for unit, amount in invested_by_unit.items()
    ]
    # None = exchange rate unavailable: show n/a rather than a wrong total
    total = (
        None
        if any(amount is None for amount in converted_invested)
        else round(sum(converted_invested), 2)
    )
    currency_symbol = get_currency_symbol()
    with col1:
        st.metric(
            "Invested",
            value="n/a" if total is None else mask_amount(f"{total} {currency_symbol}"),
        )
    with col2:
        # get last values
        balance = (
            0 if df_balance is None or df_balance.empty else df_balance.iloc[-1].sum()
        )
        balance = round(balance, 2)
        st.metric("Total value", value=mask_amount(f"{balance} {currency_symbol}"))
    with col3:
        if total is None:
            st.metric("Profit", value="n/a")
        else:
            st.metric(
                "Profit",
                value=mask_amount(f"{round(balance - total, 2)} {currency_symbol}"),
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
    st.dataframe(mask_dataframe(last_V))
