import configparser
import os
import streamlit as st
import pandas as pd
import logging
from modules.data import Data
from modules.plotter import plot_as_graph, plot_as_pie

logger = logging.getLogger(__name__)

@st.cache_data(show_spinner=False)
def getData():
    dbfile = "./data/db.sqlite3"
    return Data(dbfile)

def build_tabs(df):
    logger.debug("Build tabs")
    if startdate < enddate:
        tokens=list(df.columns)
        st.session_state.options = st.multiselect("Select Tokens to display", tokens)
        options = st.session_state.options
        if options:
            tabs = st.tabs(options)
            count = 0
            for tab in tabs:
                # print df indexes
                df_view = df.loc[df.index>str(startdate)]
                df_view = df_view.loc[df_view.index<str(enddate + pd.to_timedelta(1, unit='d'))]

                plot_as_graph(df_view, options, count, tab)
                
                tab.write(df_view[options[count]].tail(1))          
                count += 1
        st.session_state.options_save = options
    else:
        st.error('End date must be after start date')  

configfilepath = "./data/settings.ini"
if not os.path.exists(configfilepath):
    st.error("Please set your settings in the settings page")
    st.stop()

config = configparser.ConfigParser()
config.read(configfilepath)

with st.spinner('Extracting data...'):
    data = getData()
    df_sum = data.df_sum
    df_balances = data.df_balance
    df_count = data.df_tokencount
    df_market = data.df_market

add_selectbox = st.sidebar.selectbox(
    "Assets View",
    ("Global", "Assets Value", "Assets Count", "Market")
)

st.sidebar.divider()

if add_selectbox != 'Global':
    startdate = st.sidebar.date_input('Start date', value=pd.to_datetime('today') - pd.to_timedelta(365, unit='d'))
    enddate = st.sidebar.date_input('End date', value=pd.to_datetime('today'))

if add_selectbox == 'Global':
    logger.debug("Global")
    st.title("Global")

    # get last values
    last = df_balances.tail(1)
    balance = (last.sum(axis=1).values[0] if not last.empty else 0)
    balance = round(balance, 2)
    
    # show wallet value
    st.header("Wallet value : " + str(balance) + " €")
    
    plot_as_graph(df_sum)

    # show last values"
    st.header("Last values")
    last_u = df_balances.tail(5).astype(str) + " €"
    st.write(last_u)

    # draw pie
    st.header("Tokens repartition")
    plot_as_pie(df_balances.tail(5))

if add_selectbox == 'Assets Value':
    logger.debug("Assets Value")
    st.title("Assets Value")
    build_tabs(df_balances)

if add_selectbox == 'Assets Count':
    logger.debug("Assets Count")
    st.title("Assets Count")
    build_tabs(df_count)

if add_selectbox == 'Market':
    logger.debug("Market")
    st.title("Market")
    build_tabs(df_market)

if st.checkbox('Clear cache'):
    st.cache_data.clear()
