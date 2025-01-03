import streamlit as st
import pandas as pd
import logging
from modules.cmc import cmc
from modules.database.historybase import HistoryBase
from modules.plotter import plot_as_pie
from modules.database.portfolios import Portfolios

import matplotlib.pyplot as plt

from modules.process import get_current_price


logger = logging.getLogger(__name__)

st.title("Portfolios")


@st.fragment
@st.dialog("Add new portfolio")
def add_new_portfolio():
    name = st.text_input("Name")
    if st.button("Submit"):
        logger.debug(f"Adding portfolio {name}")
        g_portfolios.add_portfolio(name)
        # Close dialog
        st.rerun()


@st.fragment
@st.dialog("Danger Zone")
def danger_zone(name: str):
    st.write(f"Delete portfolio {name}?")
    confirm = st.text_input("Type 'delete' to confirm")
    if st.button("Delete") and confirm == "delete":
        g_portfolios.delete_portfolio(name)
        st.rerun()


@st.fragment
@st.dialog("Rename portfolio")
def rename_portfolio(name: str):
    new_name = st.text_input("New name")
    if st.button("Submit"):
        g_portfolios.rename(name, new_name)
        st.rerun()


@st.fragment
@st.dialog("Add Token")
def add_token(name: str):
    st.write(f"Add token to {name}")
    token = st.text_input("Token")
    token = token.upper()
    amount = st.number_input("Amount", min_value=0.0, format="%.8f")
    if st.button("Submit"):
        g_portfolios.set_token_add(name, token, amount)
        # Close dialog
        st.rerun()


@st.fragment
@st.dialog("Delete Token")
def delete_token(name: str):
    st.write(f"Delete token from {name}")
    token = st.selectbox(
        "Token",
        g_portfolios.get_tokens(name),
        index=None,
        placeholder="Select a token",
    )
    if st.button("Submit"):
        g_portfolios.delete_token(name, token)
        # Close dialog
        st.rerun()


def portfolioUI(tabs: list):
    logger.debug(f"portfolioUI - Tabs: {tabs}")

    tabs_widget = st.tabs(tabs)

    for i, tab in enumerate(tabs_widget):
        with tab:
            pf = g_portfolios.get_portfolio(tabs[i])
            df = g_portfolios.create_portfolio_dataframe(pf)
            if not df.empty:  # Only create DataFrame if data exists
                height = (len(df) * 35) + 38
                logger.debug(f"Dataframe:\n{df}")
                updated_data = st.data_editor(df, use_container_width=True, height=height)
                if not updated_data.equals(df):
                    g_portfolios.update_portfolio({tabs[i]: updated_data.to_dict(orient="index")})
                    logger.debug("## Rerun ##")
                    st.rerun()
                else:
                    logger.debug("## No Rerun ##")
            else:
                st.write("No data available")

            buttons_col1, buttons_col2, buttons_col3, buttons_col4 = st.columns(4)
            with buttons_col1:
                if st.button(
                    "Add Token",
                    key=f"addT_{i}",
                    use_container_width=True,
                    icon=":material/add:",
                ):
                    add_token(tabs[i])
            with buttons_col2:
                if st.button(
                    "Delete Token",
                    key=f"deleteT_{i}",
                    use_container_width=True,
                    icon=":material/delete:",
                ):
                    delete_token(tabs[i])
            with buttons_col3:
                if st.button(
                    "Rename Portfolio",
                    key=f"rename_{i}",
                    use_container_width=True,
                    icon=":material/edit:",
                ):
                    rename_portfolio(tabs[i])
            with buttons_col4:
                if st.button(
                    "Danger Zone",
                    key=f"dangerZ_{i}",
                    use_container_width=True,
                    type="primary",
                    icon=":material/destruction:",
                ):
                    danger_zone(tabs[i])

def aggregaterUI():
    agg = g_portfolios.aggregate_portfolios()
    df = g_portfolios.create_portfolio_dataframe(agg)

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


def update_prices():
    agg = g_portfolios.aggregate_portfolios()
    if not agg:
        st.warning("No data available")
        return
    logger.debug(f"agg: {agg}")

    #save in a list the agg keys
    tokens = list(agg.keys())
    logger.debug(f"tokens: {tokens}")

    cmc_prices = cmc(st.session_state.settings["coinmarketcap_token"])
    tokens_prices = cmc_prices.getCryptoPrices(tokens)
    if not tokens_prices:
        st.warning("No data available")
        return
    logger.debug(f"tokens_prices: {tokens_prices}")

    # merge agg and tokens_prices
    new_entries = {}
    for token in tokens:
        new_entries[token] = {"amount": agg[token]["amount"], "price": tokens_prices[token]["price"]}
    HistoryBase(st.session_state.dbfile).add_data_df(new_entries)

    st.toast("Prices updated")


def load_portfolios(dbfile: str) -> Portfolios:
    return Portfolios(dbfile)


g_portfolios = load_portfolios(st.session_state.dbfile)

# Add new portfolio dialog
if st.sidebar.button(
    "Add new portfolio",
    key="add_new_portfolio",
    icon=":material/note_add:",
    use_container_width=True,
):
    add_new_portfolio()

# Update prices
if st.sidebar.button(
    "Update prices",
    key="update_prices",
    icon=":material/refresh:",
    use_container_width=True,
):
    update_prices()

# Display portfolios
tabs = g_portfolios.get_portfolio_names()
logger.debug(f"Portfolios: {tabs}")

try:
    portfolioUI(tabs)
except Exception as e:
    st.error(f"Error: {str(e)}")

st.divider()

# Display portfolios aggregated data
st.title("Totals")
aggregaterUI()

if st.session_state.settings["debug_flag"]:
    st.write(st.session_state)
