import streamlit as st
import pandas as pd
import logging
from modules.database.portfolios import Portfolios
from modules.database.historybase import HistoryBase
from modules.database.operations import operations

logger = logging.getLogger(__name__)

st.title("Operations")

g_portfolios = Portfolios(st.session_state.dbfile)
g_historybase = HistoryBase(st.session_state.dbfile)
g_tokens = g_historybase.getTokens()
g_wallets = g_portfolios.get_portfolio_names()


def submitbuy(date, time, from_amount, form_currency, to_amount, to_token, to_wallet):
    logger.debug(
        f"submitbuy: date={date}, time={time} from_amount={from_amount}, form_currency={form_currency}, to_amount={to_amount}, to_token={to_token}, to_wallet={to_wallet}"
    )
    
    #date if formated as yyyy-mm-dd, time as hh:mm:00. merge them to a datetime object and convert it to epoch timestamp
    datetime = pd.to_datetime(f"{date} {time}")
    timestamp = datetime.timestamp()
    logger.debug(f"submitbuy: timestamp={timestamp}")

    op.insert("buy", from_amount, to_amount, form_currency, to_token, timestamp, to_wallet)

    if to_wallet is not None:
        g_portfolios.set_token_add(to_wallet, to_token, to_amount)

    st.success("Operation submitted")


def submitswap(
    date,
    swap_token_from,
    swap_amount_from,
    swap_wallet_from,
    swap_token_to,
    swap_amount_to,
    swap_wallet_to,
):
    st.warning("Not implemented yet")


op = operations()

buy_tab, swap_tab, import_tab = st.tabs(["Buy", "Swap", "Import"])
with buy_tab:
    with st.form(key="buy"):
        col_date, col_time = st.columns(2)
        with col_date:
            date = st.date_input("Date", key="buy_date")
        with col_time:
            time = st.time_input("Time", key="buy_time")
        col_from, col_to = st.columns(2)
        with col_from:
            col_from_amount, col_from_token = st.columns([3, 1])
            with col_from_amount:
                from_amount = st.number_input(
                    "From", min_value=0.0, format="%.8f", key="from_amount"
                )
            with col_from_token:
                form_currency = st.selectbox("", ["EUR", "USD"], key="form_currency")
        with col_to:
            col_to_amount, col_to_token = st.columns([3, 1])
            with col_to_amount:
                to_amount = st.number_input(
                    "To", min_value=0.0, format="%.8f", key="to_amount"
                )
            with col_to_token:
                to_token = st.selectbox("", g_tokens, index=None, key="to_token")
            to_wallet = st.selectbox(
                "Portfolio", g_wallets, key="to_wallet", index=None
            )
        if st.form_submit_button("Submit", use_container_width=True):
            submitbuy(date, time, from_amount, form_currency, to_amount, to_token, to_wallet)
    
    buylist = op.get_operations_by_type("buy")
    #save buylist to a dataframe
    df_buylist = pd.DataFrame(buylist, columns=["id", "type", "From",  "To", "Currency", "Token", "timestamp", "Portfolio"])
    #drop id and type columns
    df_buylist.drop(columns=["id", "type"], inplace=True)
    #convert timestamp to datetime
    df_buylist["timestamp"] = pd.to_datetime(df_buylist["timestamp"], unit="s")
    #reorder columns
    df_buylist = df_buylist[["timestamp", "From", "Currency", "To", "Token", "Portfolio"]]
    #sort by timestamp in descending order
    df_buylist.sort_values(by="timestamp", ascending=False, inplace=True)
    
    st.dataframe(df_buylist, use_container_width=True, hide_index=True)

with swap_tab:
    with st.form(key="swap"):
        date = st.date_input("Date", key="swap_date")
        col_from, col_to = st.columns(2)
        with col_from:
            swap_token_from = st.text_input("Token", key="swap_token_from")
            swap_amount_from = st.number_input(
                "Amount", min_value=0.0, format="%.8f", key="swap_amount_from"
            )
            swap_wallet_from = st.selectbox(
                "Wallet", g_wallets, index=None, key="swap_wallet_from"
            )
        with col_to:
            swap_token_to = st.text_input("Token", key="swap_token_to")
            swap_amount_to = st.number_input(
                "Amount", min_value=0.0, format="%.8f", key="swap_amount_to"
            )
            swap_wallet_to = st.selectbox(
                "Wallet", g_wallets, index=None, key="swap_wallet_to"
            )
        if st.form_submit_button("Submit", use_container_width=True):
            submitswap(
                date,
                swap_token_from,
                swap_amount_from,
                swap_wallet_from,
                swap_token_to,
                swap_amount_to,
                swap_wallet_to,
            )

with import_tab:
    file = st.file_uploader("Upload a file", type=["csv"])
    if file is not None:
        df = pd.read_csv(file)

        # Conversion de la date en timestamp
        if "Creation Date" in df.columns:
            df["Timestamp"] = (
                pd.to_datetime(df["Creation Date"], format="%B %d, %Y %I:%M %p").astype(
                    "int64"
                )
                // 10**9
            )

        # Nettoyage de la colonne Dashboard
        if "Dashboard" in df.columns:
            df["Dashboard"] = (
                df["Dashboard"].str.replace(r"\s*\([^)]*\)", "", regex=True).str.strip()
            )

        # Nettoyage de la colonne Value HT (€)
        if "Value HT (€)" in df.columns:
            df["Value HT (€)"] = df["Value HT (€)"].str.replace("€", "").astype(float)

        df.sort_values(by="Timestamp", inplace=True)
        st.dataframe(df)

        if st.button("Import"):
            for index, row in df.iterrows():
                op.insert(
                    "buy", 
                    row["Value HT (€)"],
                    row["Coins Value"],
                    "EUR",
                    row["Dashboard"],
                    row["Timestamp"],
                    None,
                )
            st.success("Import successful")
