import streamlit as st
import pandas as pd
import logging
from modules.plotter import plot_as_graph
from modules.process import load_db

logger = logging.getLogger(__name__)


def build_tabs(df: pd.DataFrame):
    logger.debug("Build tabs")
    if startdate < enddate:
        tokens = list(df.columns)
        st.session_state.options = st.multiselect("Select Tokens to display", tokens)
        options = st.session_state.options
        if options:
            tabs = st.tabs(options)
            count = 0
            for tab in tabs:
                # print df indexes
                df_view = df.loc[df.index > str(startdate)]
                df_view = df_view.loc[
                    df_view.index < str(enddate + pd.to_timedelta(1, unit="d"))
                ]

                plot_as_graph(df_view, options, count, tab)

                tab.write(df_view[options[count]])
                count += 1
        st.session_state.options_save = options
    else:
        st.error("End date must be after start date")

df_balance, df_sums, df_market, df_tokencount = load_db(st.session_state.dbfile)

add_selectbox = st.sidebar.selectbox(
    "Assets View", ("Global", "Assets Value", "Assets Count", "Market")
)

st.sidebar.divider()

if add_selectbox != "Global":
    startdate = st.sidebar.date_input(
        "Start date", value=pd.to_datetime("today") - pd.to_timedelta(365, unit="d")
    )
    enddate = st.sidebar.date_input("End date", value=pd.to_datetime("today"))

if add_selectbox == "Global":
    logger.debug("Global")
    st.title("Global")

    # get last values
    last = df_balance.tail(1)
    balance = last.sum(axis=1).values[0] if not last.empty else 0
    balance = round(balance, 2)

    # show wallet value
    st.header("Wallet value : " + str(balance) + " €")

    plot_as_graph(df_sums)

    # show last values"
    st.header("Last values")
    last_u = df_balance.tail(5).astype(str) + " €"
    st.write(last_u)

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
    build_tabs(df_market)

if st.session_state.settings["debug_flag"]:
    st.write(st.session_state)
