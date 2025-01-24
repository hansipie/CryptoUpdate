"""Home page module for CryptoUpdate application.

This module displays the main dashboard with portfolio metrics,
performance graphs and provides functionality for updating prices
and synchronizing with Notion database.
"""

import streamlit as st
import logging
import traceback
from modules.plotter import plot_as_graph
from modules.tools import update_database, load_db
from modules.database.operations import operations
from modules.Notion import Notion
from modules.Updater import Updater

logger = logging.getLogger(__name__)

st.title("Crypto Update")

df_balance, df_sums, _ = load_db(st.session_state.dbfile)


@st.cache_data
def join_dfs(df1, df2):
    df = df1.join(df2)
    return df


def update():
    try:
        update_database(
            st.session_state.dbfile, st.session_state.settings["coinmarketcap_token"]
        )
        st.toast("Prices updated", icon=":material/check:")
        st.rerun()
    except Exception as e:
        st.error(f"Update Error: {str(e)}")
        traceback.print_exc()


@st.dialog("Sync. Notion Database")
def syncNotionMarket():
    with st.spinner("Running ..."):
        try:
            notion = Notion(st.session_state.settings["notion_token"])
            db_id = notion.getObjectId(
                st.session_state.settings["notion_database"],
                "database",
                st.session_state.settings["notion_parentpage"],
            )
            if db_id is None:
                st.error("Error: Database not found")
                st.rerun()
            else:
                updater = Updater(
                    st.session_state.dbfile,
                    st.session_state.settings["coinmarketcap_token"],
                    st.session_state.settings["notion_token"],
                    db_id,
                )
                updater.getCryptoPrices()
        except KeyError as ke:
            st.error("Error: " + type(ke).__name__ + " - " + str(ke))
            st.error("Please set your settings in the settings page")
            traceback.print_exc()
            st.rerun()
        except Exception as e:
            st.error("Error: " + type(e).__name__ + " - " + str(e))
            traceback.print_exc()
            st.rerun()

        updatetokens_bar = st.progress(0)
        count = 0
        for token, data in updater.notion_entries.items():
            updatetokens_bar.progress(
                count / len(updater.notion_entries), text=f"Updating {token}"
            )
            updater.updateNotionDatabase(pageId=data["page"], coinPrice=data["price"])
            count += 1
        updatetokens_bar.progress(100, text="Update completed")
        updater.UpdateLastUpdate()
    st.rerun()


# Update prices
with st.sidebar:
    if st.button(
        "Update prices",
        key="update_prices",
        icon=":material/update:",
        use_container_width=True,
    ):
        update()

    if st.button(
        "Sync. Notion Database", icon=":material/publish:", use_container_width=True
    ):
        syncNotionMarket()

with st.container(border=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        sum = operations(st.session_state.dbfile).sum_buyoperations()
        if sum is None:
            sum = 0
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
    # plot_as_graph(join_dfs(df_sums, df_balance))
    plot_as_graph(df_sums)

# show last values"
st.header("Last values")
last_V = df_balance.tail(5).copy()
last_V = last_V.astype(str) + " €"
st.dataframe(last_V)
