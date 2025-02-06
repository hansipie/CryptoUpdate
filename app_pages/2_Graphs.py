import logging
import os

import pandas as pd
import streamlit as st

from modules.database.market import Market
from modules.database.portfolios import Portfolios
from modules.database.tokensdb import TokensDatabase
from modules.plotter import plot_as_graph, plot_as_pie
from modules.tools import create_portfolio_dataframe, interpolate_eurusd
from modules.utils import get_file_hash, toTimestamp_A

logger = logging.getLogger(__name__)


def load_portfolios(dbfile: str) -> Portfolios:
    """Load portfolios from database file.

    Args:
        dbfile: Path to database file

    Returns:
        Portfolios instance initialized with the database
    """
    return Portfolios(dbfile)


def aggregater_ui():
    """Display aggregate view of all portfolios.

    Shows a table of token totals across all portfolios and
    a pie chart showing portfolio value distribution.
    """
    portfolios = load_portfolios(st.session_state.settings["dbfile"])
    agg = portfolios.aggregate_portfolios()
    logger.debug("Aggregated: %s", agg)
    df = create_portfolio_dataframe(agg)

    col_tbl, col_pie = st.columns(2)
    with col_tbl:
        st.header("Tokens")
        if not df.empty:
            height = (len(df) * 35) + 38
            height = min(height, 650)

            df = df.groupby("token").agg({"amount": "sum", "value(€)": "sum"})
            df["Repartition(%)"] = (df["value(€)"] / df["value(€)"].sum()) * 100
            df = df.rename(columns={"amount": "Amount", "value(€)": "Value(€)"})
            df = df.sort_values(by="Repartition(%)", ascending=False)
            st.dataframe(df, use_container_width=True, height=height)
            st.write("Total value: €" + str(round(df["Value(€)"].sum(), 2)))
        else:
            st.info("No data available")
    with col_pie:
        st.header("Tokens repartition")
        if not df.empty:
            try:
                plot_as_pie(df, column="Value(€)")
            except Exception as e:
                st.error(f"Error: {str(e)}")
        else:
            st.info("No data available")

def draw_tab_content(section:str, token: str, start_timestamp: int, end_timestamp: int):
    logger.debug("Draw tab content for token %s", token)
    if section == "Assets Balances":
        with st.spinner("Loading assets balances..."):
            df_view = tokensdb.get_token_balances(token, start_timestamp, end_timestamp)
    elif section == "Market":
        with st.spinner("Loading market..."):
            df_view = markgetdb.get_token_market(token, start_timestamp, end_timestamp)
    else:
        df_view = None
    if df_view is not None:
        mcol1, mcol2 = st.columns(2)
        with mcol1:
            nbr_days = st.session_state.enddate - st.session_state.startdate
            mcol1.metric("Days", value=nbr_days.days)
        with mcol2:
            first = df_view.iloc[0].values[0]
            last = df_view.iloc[-1].values[0]
            logger.debug("first: %s, last: %s", first, last)
            mcol2.metric(
                "Performance",
                value=(
                    f"{round(((last - first) / first) * 100, 2)} %"
                    if first != 0
                    else "0 %"
                    if last == 0
                    else "∞ %"
                ),
            )
        col1, col2 = st.columns([3, 1])
        with col1:
            plot_as_graph(df_view)
        with col2:
            col2.dataframe(df_view, use_container_width=True)
    else:
        st.info("No data available")


def build_tabs(section: str = "Assets Balances"):
    start_timestamp = toTimestamp_A(st.session_state.startdate, pd.to_datetime("00:00:00").time())
    end_timestamp = toTimestamp_A(st.session_state.enddate, pd.to_datetime("23:59:59").time())
    if section == "Assets Balances":
        available_tokens = tokensdb.get_tokens()
    elif section == "Market":
        available_tokens = markgetdb.getTokens()
    else:
        available_tokens = []
    if not available_tokens:
        st.info("No data available")
        return
    temp_tokens = st.multiselect(
        "Select Tokens to display",
        available_tokens,
        default=st.session_state.tokens,
    )
    if temp_tokens != st.session_state.tokens:
        st.session_state.tokens = temp_tokens
        logger.debug("Tokens list changed")
        st.rerun()
    else:
        logger.debug("Tokens list not changed")

    if st.session_state.tokens:
        tabs = st.tabs(st.session_state.tokens)
        idx_token = 0
        for tab in tabs:
            with tab:
                draw_tab_content(section, st.session_state.tokens[idx_token], start_timestamp, end_timestamp)
            idx_token += 1

    
def build_price_tab(df: pd.DataFrame):
    logger.debug("Build tabs")
    if df is None or df.empty:
        st.info("No data available")
        return
    if st.session_state.startdate < st.session_state.enddate:

        df_view = df.loc[df.index > str(st.session_state.startdate)]
        df_view = df_view.loc[
            df_view.index
            < str(st.session_state.enddate + pd.to_timedelta(1, unit="d"))
        ]
        df_view = df_view.loc[:, ["price"]]
        df_view = df_view.dropna()

        mcol1, mcol2 = st.columns(2)
        with mcol1:
            nbr_days = st.session_state.enddate - st.session_state.startdate
            mcol1.metric("Days", value=nbr_days.days)
        with mcol2:
            first = df_view.iloc[0].values[0]
            last = df_view.iloc[-1].values[0]
            logger.debug("first: %s, last: %s", first, last)
            mcol2.metric(
                "Performance",
                value=(
                    f"{round(((last - first) / first) * 100, 2)} %"
                    if first != 0
                    else "0 %"
                    if last == 0
                    else "∞ %"
                ),
            )
        col1, col2 = st.columns([3, 1])
        with col1:
            plot_as_graph(df_view)
        with col2:
            col2.dataframe(df_view, use_container_width=True)

    else:
        st.error("The end date must be after the start date")


with st.sidebar:
    add_selectbox = st.selectbox(
        "Assets View",
        ("Global", "Assets Balances", "Market", "Currency (EURUSD)"),
    )

    if add_selectbox != "Global":
        st.divider()
        st.session_state.startdate = st.date_input(
            "Start date",
            value=pd.to_datetime("today") - pd.to_timedelta(365, unit="d"),
        )
        st.session_state.enddate = st.date_input(
            "End date", value=pd.to_datetime("today")
        )

tokensdb = TokensDatabase(st.session_state.settings["dbfile"])
markgetdb = Market(st.session_state.settings["dbfile"], st.session_state.settings["coinmarketcap_token"])

if "tokens" not in st.session_state:
    st.session_state.tokens = []

if add_selectbox == "Global":
    logger.debug("Global")
    st.title("Global")
    aggregater_ui()

if add_selectbox == "Assets Balances":
    logger.debug("Assets Balances")
    st.title("Assets Balances")
    build_tabs()

if add_selectbox == "Market":
    logger.debug("Market")
    st.title("Market")
    build_tabs("Market")

if add_selectbox == "Currency (EURUSD)":
    logger.debug("Currency (EURUSD)")
    st.title("Currency (EURUSD)")
    market = Market(
        st.session_state.settings["dbfile"],
        st.session_state.settings["coinmarketcap_token"],
    )
    df_currency = market.get_currency()
    build_price_tab(df_currency)

    interpolated: float = 0.0
    with st.form(key="interpolate"):
        col_date, col_time, col_btn = st.columns([3, 2, 1], vertical_alignment="bottom")
        with col_date:
            date = st.date_input("Date", key="interdate")
        with col_time:
            time = st.time_input("Time", key="intertime")
        with col_btn:
            if st.form_submit_button(
                "Submit",
                use_container_width=True,
            ):
                timestamp = toTimestamp_A(date, time)
                interpolated = interpolate_eurusd(
                    timestamp, st.session_state.settings["dbfile"]
                )
        if interpolated is not None:
            if interpolated != 0.0:
                st.info(f"Interpolated value: {interpolated} USD")
        else:
            st.info("No data available")