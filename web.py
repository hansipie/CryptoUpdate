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
def df_from_archives(*columns):
    print("Read archives start")
    dicolist = []
    dirs=os.listdir("./archives")
    for dir in dirs:
        files=os.listdir("./archives/"+dir)
        dico = {}
        for file in files:
            dfcsv = pd.read_csv("./archives/"+dir+"/"+file)
            dfcsv.reset_index()
            dico['Timeframe'] = formatepoch(dir)
            for _, row in dfcsv.iterrows():
                dico[row['Tokens']] = []
                for column in columns:
                    dico[row['Tokens']].append(row[column])
        dicolist.append(dico)  
    df = pd.DataFrame(dicolist)
    df.set_index('Timeframe',inplace=True)
    df.sort_index(inplace=True)
    print("Read archives end")
    return df

def build_tabs(df, index):
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
            df_view = df.applymap(lambda x: x[index] if isinstance(x, list) and len(x) > 0 else x)
            st.write(df_view[options[count]])
            tab.line_chart(df_view[options[count]])
            count += 1
    print("save options")
    st.session_state.options_save = options

print("main")

# get dataframes from archives
df_work = df_from_archives('Coins in wallet', 'Wallet Value (€)', 'Price/Coin')

add_selectbox = st.sidebar.selectbox(
    "Assets View",
    ("Global", "Assets Value", "Assets Count", "Market")
)

startdate = st.sidebar.date_input('Start date', value=pd.to_datetime('today') - pd.to_timedelta(30, unit='d'))
endate = st.sidebar.date_input('End date', value=pd.to_datetime('today'))

# session state variable
if 'options' not in st.session_state:
    st.session_state.options = []
if 'options_save' not in st.session_state:
    st.session_state.options_save = []

# create sum df
df_all_sum = df_work.apply(lambda x: sum(i[1] for i in x if isinstance(i, list)), axis=1)

if add_selectbox == 'Global':
    st.title("Global")

    # get last values
    last = get_last_line(df_work).applymap(lambda x: round(x[1], 2) if isinstance(x, list) and len(x) > 0 else x)
    balance = last.sum(axis=1).values[0]
    balance = round(balance, 2)
    
    # show wallet value
    st.header("Wallet value : " + str(balance) + " €")
    st.line_chart(df_all_sum)

    # show last values
    st.header("Last values")
    last_u = last.astype(str) + " €"
    st.write(last_u)

    # draw pie
    st.header("Tokens repartition")
    display_as_pie(last)

if add_selectbox == 'Assets Value':
    st.title("Assets Value")
    build_tabs(df_work, 1)

if add_selectbox == 'Assets Count':
    st.title("Assets Count")
    build_tabs(df_work, 0)

if add_selectbox == 'Market':
    st.title("Market")
    build_tabs(df_work, 2)

if st.checkbox('Clear cache'):
    st.cache_data.clear()
