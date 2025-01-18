import streamlit as st
import pandas as pd
import logging
import os
from modules.database.portfolios import Portfolios
from modules.database.market import Market
from modules.plotter import plot_as_graph, plot_as_pie
from modules.tools import create_portfolio_dataframe, interpolate_EURUSD, load_db
from modules.utils import get_file_hash, toTimestamp


logger = logging.getLogger(__name__)


def load_portfolios(dbfile: str) -> Portfolios:
    return Portfolios(dbfile)


def aggregaterUI():
    portfolios = load_portfolios(st.session_state.dbfile)
    agg = portfolios.aggregate_portfolios()
    df = create_portfolio_dataframe(agg)

    col_tbl, col_pie = st.columns(2)
    with col_tbl:
        st.header("Tokens")
        if not df.empty:
            height = (len(df) * 35) + 38
            height = min(height, 650)

            df = df.groupby("token").agg({"amount": "sum", "value(€)": "sum"})
            df["Repartition(%)"] = round(
                (df["value(€)"] / df["value(€)"].sum()) * 100, 2
            )
            df = df.rename(columns={"amount": "Amount", "value(€)": "Value(€)"})
            df = df.sort_values(by="Repartition(%)", ascending=False)
            st.dataframe(df, use_container_width=True, height=height)
            st.write("Total value: €" + str(round(df["Value(€)"].sum(), 2)))
        else:
            st.warning("No data available")
    with col_pie:
        st.header("Tokens repartition")
        if not df.empty:
            try:
                plot_as_pie(df, column="Value(€)")
            except Exception as e:
                st.error(f"Error: {str(e)}")
        else:
            st.warning("No data available")


def build_tabs(df: pd.DataFrame, columns: list = None):
    logger.debug("Build tabs")
    if df is None or df.empty:
        st.warning("No data available")
        return
    if startdate < enddate:
        if columns is None:
            available_tokens = list(df.columns)
        else:
            available_tokens = columns if all(x in df.columns for x in columns) else None
        if len(available_tokens) > 1:
            tokens = st.multiselect(
                "Select Tokens to display", available_tokens, key="graphtokens"
            )
        else:
            tokens = available_tokens
        if tokens:
            tabs = st.tabs(tokens)
            idx_token = 0
            for tab in tabs:
                df_view = df.loc[df.index > str(startdate)]
                df_view = df_view.loc[
                    df_view.index < str(enddate + pd.to_timedelta(1, unit="d"))
                ]
                df_view = df_view[[tokens[idx_token]]]
                df_view = df_view.dropna()

                mcol1, mcol2 = tab.columns(2)
                with mcol1:
                    nbr_days = enddate - startdate
                    mcol1.metric("Days", value=nbr_days.days)
                with mcol2:
                    first = df_view.iloc[0].values[0]
                    last = df_view.iloc[-1].values[0]
                    logger.debug(f"first: {first}, last: {last}")
                    mcol2.metric(
                        "Performance",
                        value=(
                            f"{round(((last - first) / first) * 100, 2)} %"
                            if first != 0
                            else "0 %" if last == 0 else "∞ %"
                        ),
                    )
                col1, col2 = tab.columns([3, 1])
                with col1:
                    plot_as_graph(df_view, col1)
                with col2:
                    col2.dataframe(df_view, use_container_width=True)
                idx_token += 1
    else:
        st.error("The end date must be after the start date")

@st.cache_data(
    show_spinner=False,
    hash_funcs={str: lambda x: get_file_hash(x) if os.path.isfile(x) else hash(x)},
)
def load_market(dbfile: str) -> pd.DataFrame:
    with st.spinner("Loading market..."):
        logger.debug("Load market")
        market = Market(dbfile, st.session_state.settings["coinmarketcap_token"])
        return market.getMarket()


df_balance, df_sums, df_tokencount = load_db(st.session_state.dbfile)

add_selectbox = st.sidebar.selectbox(
    "Assets View", ("Global", "Assets Value", "Assets Count", "Market", "Currency (EURUSD)")
)

if add_selectbox != "Global":
    st.sidebar.divider()
    startdate = st.sidebar.date_input(
        "Start date", value=pd.to_datetime("today") - pd.to_timedelta(365, unit="d")
    )
    enddate = st.sidebar.date_input("End date", value=pd.to_datetime("today"))

if add_selectbox == "Global":
    logger.debug("Global")
    # Display portfolios aggregated data
    st.title("Global")
    aggregaterUI()

if add_selectbox == "Assets Value":
    logger.debug("Assets Value")
    st.title("Assets Value")
    build_tabs(df_balance)

if add_selectbox == "Assets Count":
    logger.debug("Assets Count")
    st.title("Assets Count")
    build_tabs(df_tokencount)

if add_selectbox == "Market":
    logger.debug("Market")
    st.title("Market")
    df_market = load_market(st.session_state.dbfile)
    build_tabs(df_market)
    st.dataframe(df_market)

if add_selectbox == "Currency (EURUSD)":
    logger.debug("Currency (EURUSD)")
    st.title("Currency (EURUSD)")
    market = Market(st.session_state.dbfile, st.session_state.settings["coinmarketcap_token"])
    df_currency = market.getCurrency()
    build_tabs(df_currency, ["price"])
    
    interpolated = 0.0
    with st.form(key="interpolate"):
        col_date, col_time, col_btn = st.columns([3, 2, 1], vertical_alignment="bottom")
        with col_date:
            date = st.date_input("Date", key="interdate")
        with col_time:
            time = st.time_input("Time", key="intertime")
        with col_btn:
            if st.form_submit_button("Submit", use_container_width=True, ):
                timestamp = toTimestamp(date, time)
                interpolated = interpolate_EURUSD(timestamp, st.session_state.dbfile)
        if interpolated is not None:
            if interpolated != 0.0:
                st.info(f"Interpolated value: {interpolated} USD")
        else:
            st.error("No data available")