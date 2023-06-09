import os
import time
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

def get_last_line(df):
    last = df.tail(1)
    last = last.reset_index(drop=True)
    last = last.loc[:, (last != 0).any(axis=0)]
    last = last.dropna(axis='columns')
    last = last.round(2)
    return last

def display_as_pie(df):
    values = df.values.tolist()[0]
    labels = df.columns.tolist()
    plt.figure(figsize=(10,10), facecolor='white')
    ax1 = plt.subplot()
    ax1.pie(values, labels=labels)
    st.pyplot(plt)

def formatepoch(epoch):
    value = int(epoch)
    epochformat = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(value))
    return epochformat

@st.cache_data 
def df_from_archives(column):
    dicolist = []
    dirs=os.listdir("./archives")
    for dir in dirs:
        files=os.listdir("./archives/"+dir)
        dico = {}
        for file in files:
            dfcsv = pd.read_csv("./archives/"+dir+"/"+file)
            dfcsv.reset_index()
            dico['Timeframe'] = formatepoch(dir)
            for index, row in dfcsv.iterrows():
                dico[row['Name']] = row[column]
        dicolist.append(dico)  
    df = pd.DataFrame(dicolist)
    df.set_index('Timeframe',inplace=True)
    df.sort_index(inplace=True)
    return df

def build_tabs(df):
    tokens=list(df.columns)
    print("select options")
    print("check save", st.session_state.options_save)    
    st.session_state.options = st.multiselect("Select Tokens to display", tokens)
    options = st.session_state.options
    print("check options", options)    

    if options:
        tabs = st.tabs(options)
        count = 0
        for tab in tabs:
            tab.line_chart(df[options[count]])
            count += 1
    print("save options")
    st.session_state.options_save = options

add_selectbox = st.sidebar.selectbox(
    "Assets View",
    ("Global", "Assets Value", "Assets Count", "Market")
)

print("-> Root code")

# get dataframes from archives
df_coinscount = df_from_archives('Coins in wallet')
df_coinsvalue = df_from_archives('Wallet Value (€)')
df_market = df_from_archives('Price/Coin')

# session state variable
if 'options' not in st.session_state:
    print("-> options_init")
    st.session_state.options = []
if 'options_save' not in st.session_state:
    print("-> options_save_init")
    st.session_state.options_save = []

# create sum df
df_all_sum = df_coinsvalue.sum(axis=1, numeric_only=True)

if add_selectbox == 'Global':
    st.title("Global")

    # show wallet value
    st.header("Wallet value")
    st.line_chart(df_all_sum)

    # show last values
    st.header("Last values")
    last = get_last_line(df_coinsvalue)
    #show € after value
    last_u = last.astype(str) + " €"
    st.write(last_u)

    # draw pie
    st.header("Tokens repartition")
    display_as_pie(last)

if add_selectbox == 'Assets Value':
    st.title("Assets Value")
    build_tabs(df_coinsvalue)

if add_selectbox == 'Assets Count':
    st.title("Assets Count")
    build_tabs(df_coinscount)

if add_selectbox == 'Market':
    st.title("Market")
    build_tabs(df_market)

if st.checkbox('Clear cache'):
    st.cache_data.clear()

st.subheader("debug")
col1, col2 = st.columns(2)
col1.write("options") 
col1.write(st.session_state.options)
col2.write("options_save") 
col2.write(st.session_state.options_save)
