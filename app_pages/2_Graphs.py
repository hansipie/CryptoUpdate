import streamlit as st
import pandas as pd
import logging
import os
from modules.database.portfolios import Portfolios
from modules.database.market import Market
from modules.plotter import plot_as_graph, plot_as_pie
from modules.tools import create_portfolio_dataframe, interpolate_eurusd, load_db
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


def build_tabs(df: pd.DataFrame, columns: list = None):
    """Build tabs displaying performance graphs for selected tokens.

    Args:
        df: DataFrame containing token data

    Shows performance metrics and graphs for each selected token
    within the specified date range.
    """
    logger.debug("Build tabs")
    if df is None or df.empty:
        st.info("No data available")
        return
    if st.session_state.startdate < st.session_state.enddate:
        if columns is None:
            available_tokens = list(df.columns)
            st.session_state.tokens = st.multiselect(
                "Select Tokens to display",
                available_tokens,
                default=st.session_state.tokens,
            )
            tokens = st.session_state.tokens
        else:
            tokens = columns if all(x in df.columns for x in columns) else None
        if tokens:
            tabs = st.tabs(tokens)
            idx_token = 0
            for tab in tabs:
                df_view = df.loc[df.index > str(st.session_state.startdate)]
                df_view = df_view.loc[
                    df_view.index
                    < str(st.session_state.enddate + pd.to_timedelta(1, unit="d"))
                ]
                df_view = df_view.loc[:, [tokens[idx_token]]]
                df_view = df_view.dropna()

                mcol1, mcol2 = tab.columns(2)
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
    """Load market data from database.

    Args:
        dbfile: Path to database file

    Returns:
        DataFrame containing market price history
    """
    with st.spinner("Loading market..."):
        logger.debug("Load market")
        ret = Market(dbfile, st.session_state.settings["coinmarketcap_token"])
        return ret.getMarket()


with st.sidebar:
    add_selectbox = st.selectbox(
        "Assets View",
        ("Global", "Assets Value", "Assets Count", "Market", "Currency (EURUSD)"),
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

df_balance, df_sums, df_tokencount = load_db(st.session_state.settings["dbfile"])

if "tokens" not in st.session_state:
    st.session_state.tokens = []

if add_selectbox == "Global":
    logger.debug("Global")
    st.title("Global")
    aggregater_ui()

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
    df_market = load_market(st.session_state.settings["dbfile"])
    build_tabs(df_market)
    st.dataframe(df_market)

if add_selectbox == "Currency (EURUSD)":
    logger.debug("Currency (EURUSD)")
    st.title("Currency (EURUSD)")
    market = Market(
        st.session_state.settings["dbfile"],
        st.session_state.settings["coinmarketcap_token"],
    )
    df_currency = market.get_currency()
    build_tabs(df_currency, ["price"])

    interpolated = 0.0
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