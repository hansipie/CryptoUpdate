import configparser
import os
import streamlit as st
import pandas as pd
import logging
from modules.plotter import plot_as_graph, plot_as_pie
from modules import portfolios as pf

logger = logging.getLogger(__name__)


def build_tabs(df):
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

                tab.write(df_view[options[count]].tail(1))
                count += 1
        st.session_state.options_save = options
    else:
        st.error("End date must be after start date")

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
    last = st.session_state.database["balance"].tail(1)
    balance = last.sum(axis=1).values[0] if not last.empty else 0
    balance = round(balance, 2)

    # show wallet value
    st.header("Wallet value : " + str(balance) + " €")

    plot_as_graph(st.session_state.database["sum"])

    # show last values"
    st.header("Last values")
    last_u = st.session_state.database["balance"].tail(5).astype(str) + " €"
    st.write(last_u)

    col_tbl, col_pie = st.columns(2)
    with col_tbl:
        # show all tokens
        st.header("Tokens")
        g_portfolios = pf.Portfolios()
        table = g_portfolios.get_consolidated_tokens()
        st.dataframe(table, use_container_width=True)

    with col_pie:
        # draw pie
        st.header("Tokens repartition")
        plot_as_pie(st.session_state.database["balance"].tail(5))

if add_selectbox == "Assets Value":
    logger.debug("Assets Value")
    st.title("Assets Value")
    build_tabs(st.session_state.database["balance"])

if add_selectbox == "Assets Count":
    logger.debug("Assets Count")
    st.title("Assets Count")
    build_tabs(st.session_state.database["tokencount"])

if add_selectbox == "Market":
    logger.debug("Market")
    st.title("Market")
    build_tabs(st.session_state.database["market"])

