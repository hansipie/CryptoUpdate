import streamlit as st
import pandas as pd
import logging
import os
from modules.database.portfolios import Portfolios
from modules.database.market import Market
from modules.database.historybase import HistoryBase
from modules.plotter import plot_as_graph, plot_as_pie
from modules.process import get_file_hash, load_db


logger = logging.getLogger(__name__)

def load_portfolios(dbfile: str) -> Portfolios:
    return Portfolios(dbfile)

def aggregaterUI():
    portfolios = load_portfolios(st.session_state.dbfile)
    agg = portfolios.aggregate_portfolios()
    df = portfolios.create_portfolio_dataframe(agg)

    col_tbl, col_pie = st.columns(2)
    with col_tbl:
        st.header("Tokens")
        if not df.empty:
            height = (len(df) * 35) + 38
            height = min(height, 650)

            df = df.groupby("token").agg({"amount": "sum", "value(€)": "sum"})
            st.dataframe(df, use_container_width=True, height=height)
            st.write("Total value: €" + str(round(df["value(€)"].sum(), 2)))
        else:
            st.warning("No data available")
    with col_pie:
        st.header("Tokens repartition")
        if not df.empty:
            # Créer un graphique en secteurs pour la colonne "value(€)"
            transposed = df.transpose()
            transposed = transposed.drop("amount")
            logger.debug(f"transposed:\n{transposed}")
            try:
                plot_as_pie(transposed)
            except Exception as e:
                st.error(f"Error: {str(e)}")
        else:
            st.warning("No data available")

def build_tabs(df: pd.DataFrame):
    logger.debug("Build tabs")
    if df is None or df.empty:
        st.warning("No data available")
        return
    if startdate < enddate:
        tokens = list(df.columns)
        st.session_state.options = st.multiselect("Select Tokens to display", tokens)
        options = st.session_state.options
        if options:
            tabs = st.tabs(options)
            count = 0
            for tab in tabs:
                df_view = df.loc[df.index > str(startdate)]
                df_view = df_view.loc[
                    df_view.index < str(enddate + pd.to_timedelta(1, unit="d"))
                ]
                col1, col2 = tab.columns([3,1])
                with col1:
                    plot_as_graph(df_view, options, count, col1)
                with col2:
                    col2.dataframe(df_view[options[count]], use_container_width=True)
                count += 1
        st.session_state.options_save = options
    else:
        st.error("The end date must be after the start date")

def syncMarket():
    market = Market(st.session_state.dbfile, st.session_state.settings["coinmarketcap_token"])
    market.migrateFormDatabase()
    #market.updateMarket()

    st.toast("Sync. Market done", icon="✔️")

@st.cache_data(
    show_spinner=False,
    hash_funcs={str: lambda x: get_file_hash(x) if os.path.isfile(x) else hash(x)}
)
def load_market(dbfile: str) -> pd.DataFrame:
    with st.spinner("Loading market..."):
        logger.debug("Load market")
        market = Market(dbfile, st.session_state.settings["coinmarketcap_token"])
        return market.getMarket()

df_balance, df_sums, df_tokencount = load_db(st.session_state.dbfile)

add_selectbox = st.sidebar.selectbox(
    "Assets View", ("Global", "Assets Value", "Assets Count", "Market")
)

if add_selectbox != "Global":
    st.sidebar.divider()
    startdate = st.sidebar.date_input(
        "Start date", value=pd.to_datetime("today") - pd.to_timedelta(365, unit="d")
    )
    enddate = st.sidebar.date_input("End date", value=pd.to_datetime("today"))

if add_selectbox == "Market":
    st.sidebar.divider()
    st.sidebar.button("Sync. Market", on_click=syncMarket)

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

if st.session_state.settings["debug_flag"]:
    st.write(st.session_state)