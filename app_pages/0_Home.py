import streamlit as st
import logging
from modules.plotter import plot_as_graph
from modules.tools import load_db
from modules.database.operations import operations

logger = logging.getLogger(__name__)

st.title("Crypto Update")

df_balance, df_sums, _ = load_db(st.session_state.dbfile)

@st.cache_data
def join_dfs(df1, df2):
    df = df1.join(df2)
    return df

with st.container(border=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        sum = operations(st.session_state.dbfile).sum_buyoperations()
        st.metric("Invested", value=f"{sum} €")
    with col2:
        # get last values
        balance = df_balance.iloc[-1, 1:].sum()
        balance = round(balance, 2)
        st.metric("Total value", value=f"{balance} €")
    with col3:
        st.metric(
            "Profit",
            value=f"{round(balance - sum, 2)} €",
            delta=f"{round(((balance - sum) / sum) * 100, 2)} %",
        )

with st.container(border=True):
    #plot_as_graph(join_dfs(df_sums, df_balance))
    plot_as_graph(df_sums)

# show last values"
st.header("Last values")
last_V = df_balance.tail(5).copy()
last_V = last_V.astype(str) + " €"
st.dataframe(last_V)
