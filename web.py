import os
import sqlite3
import time
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")

def display_as_pie(df):
    values = df.values.tolist()[0]
    labels = df.columns.tolist()
    plt.figure(figsize=(10,10), facecolor='white')
    ax1 = plt.subplot()
    ax1.pie(values, labels=labels)
    st.pyplot(plt)

@st.cache_data
def make_sum() -> pd.DataFrame:
    print("Make sum df")
    con = sqlite3.connect('./data/db.sqlite3')
    df_timestamp = pd.read_sql_query("SELECT DISTINCT timestamp from Database ORDER BY timestamp", con)
    df = pd.DataFrame(columns=['datetime', 'value'])
    for mytime in df_timestamp['timestamp']:
        dftmp = pd.read_sql_query("SELECT ROUND(sum(price*(CASE WHEN count IS NOT NULL THEN count ELSE 0 END)), 2) as value, DATETIME(timestamp, 'unixepoch') AS datetime from Database WHERE timestamp = " + str(mytime), con)
        df.loc[len(df)] = [dftmp['datetime'][0], dftmp['value'][0]]
    df.set_index('datetime', inplace=True)
    con.close()
    print("Archive loaded")
    return df

@st.cache_data
def get_balances() -> pd.DataFrame:
    print("Get balances df")
    con = sqlite3.connect('./data/db.sqlite3')
    df_result  = pd.DataFrame()
    df_tokens = pd.read_sql_query("select DISTINCT token from Database", con)
    for token in df_tokens['token']:
        df = pd.read_sql_query(f"SELECT DATETIME(timestamp, 'unixepoch') AS datetime, ROUND(price*(CASE WHEN count IS NOT NULL THEN count ELSE 0 END), 2) AS {token} FROM Database WHERE token = '"+token+"' ORDER BY timestamp;", con)
        df.set_index('datetime', inplace=True)
        df_result = pd.concat([df_result, df], axis=1)   
    df_result = df_result.fillna(0)
    df_result.sort_index()
    print(df_result.tail(1))
    con.close()
    return df_result

@st.cache_data
def get_tokencount() -> pd.DataFrame:
    print("Get tokencount df")
    con = sqlite3.connect('./data/db.sqlite3')
    df_result  = pd.DataFrame()
    df_tokens = pd.read_sql_query("select DISTINCT token from Database", con)
    for token in df_tokens['token']:
        df = pd.read_sql_query(f"SELECT DATETIME(timestamp, 'unixepoch') AS datetime, count AS {token} FROM Database WHERE token = '"+token+"' ORDER BY timestamp;", con)
        df.set_index('datetime', inplace=True)
        df_result = pd.concat([df_result, df], axis=1)   
    df_result = df_result.fillna(0)
    df_result.sort_index()
    print(df_result.tail(1))
    con.close()
    return df_result

@st.cache_data
def get_market() -> pd.DataFrame:
    print("Get market df")
    con = sqlite3.connect('./data/db.sqlite3')
    df_result  = pd.DataFrame()
    df_tokens = pd.read_sql_query("select DISTINCT token from Database", con)
    for token in df_tokens['token']:
        df = pd.read_sql_query(f"SELECT DATETIME(timestamp, 'unixepoch') AS datetime, price AS {token} FROM Database WHERE token = '"+token+"' ORDER BY timestamp;", con)
        df.set_index('datetime', inplace=True)
        df_result = pd.concat([df_result, df], axis=1)   
    df_result = df_result.fillna(0)
    df_result.sort_index()
    print(df_result.tail(1))
    con.close()
    return df_result

def build_tabs(df):
    print("Build tabs")
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
                tab.line_chart(df_view[options[count]])    
                st.write(df_view[options[count]].tail(1))          
                count += 1
        st.session_state.options_save = options
    else:
        st.error('End date must be after start date')  

# get dataframes from archives
df_sum = make_sum()
df_balances = get_balances()
df_count = get_tokencount()
df_market = get_market()

add_selectbox = st.sidebar.selectbox(
    "Assets View",
    ("Global", "Assets Value", "Assets Count", "Market")
)

st.sidebar.divider()

if add_selectbox != 'Global':
    startdate = st.sidebar.date_input('Start date', value=pd.to_datetime('today') - pd.to_timedelta(365, unit='d'))
    enddate = st.sidebar.date_input('End date', value=pd.to_datetime('today'))

# session state variable
if 'options' not in st.session_state:
    st.session_state.options = []
if 'options_save' not in st.session_state:
    st.session_state.options_save = []

if add_selectbox == 'Global':
    print("Global")
    st.title("Global")

    # get last values
    last = df_balances.tail(1)
    balance = last.sum(axis=1).values[0]
    balance = round(balance, 2)
    
    # show wallet value
    st.header("Wallet value : " + str(balance) + " €")
    st.line_chart(df_sum)

    # show last values
    st.header("Last values")
    last_u = last.astype(str) + " €"
    st.write(last_u)

    # draw pie
    st.header("Tokens repartition")
    display_as_pie(last)

if add_selectbox == 'Assets Value':
    print("Assets Value")
    st.title("Assets Value")
    build_tabs(df_balances)

if add_selectbox == 'Assets Count':
    print("Assets Count")
    st.title("Assets Count")
    build_tabs(df_count)

if add_selectbox == 'Market':
    print("Market")
    st.title("Market")
    build_tabs(df_market)

if st.checkbox('Clear cache'):
    st.cache_data.clear()
