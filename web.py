import os
import time
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

def get_last_line(df):
    last = df.tail(1)
    last = last.reset_index(drop=True)
    last = last.drop(columns=['_Sum'])
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

add_selectbox = st.sidebar.selectbox(
    "Assets View",
    ("Global", "Tokens Value", "Tokens count")
)

# get dataframes from archives
print('Get dataframes from archives')
df_coinscount = df_from_archives('Coins in wallet')
df_coinsvalue = df_from_archives('Wallet Value (€)')
# add sum column
all_sum = df_coinsvalue.sum(axis=1, numeric_only=True)
df_coinsvalue["_Sum"] = all_sum
print('Dataframes ready')

#persist mutliselect options
options = []

if add_selectbox == 'Global':
    # show last values
    st.subheader("Last values")
    last = get_last_line(df_coinsvalue)
    #show € after value
    last_u = last.astype(str) + " €"
    st.write(last_u)

    # draw pie
    st.subheader("Pie chart")
    display_as_pie(last)

if add_selectbox == 'Tokens Value':
    st.header("Assets values")

    tokens=list(df_coinsvalue.columns)
    options = st.multiselect("Select Tokens to display", tokens, '_Sum')
    
    if options:
        tabs = st.tabs(options)
        count = 0
        for tab in tabs:
            tab.line_chart(df_coinsvalue[options[count]])
            count += 1

if add_selectbox == 'Tokens count':
    st.header("Assets token count")

    tokens=list(df_coinscount.columns)
    options = st.multiselect("Select Tokens to display", tokens)

    if options:
        tabs = st.tabs(options)
        count = 0
        for tab in tabs:
            tab.line_chart(df_coinscount[options[count]])
            count += 1
