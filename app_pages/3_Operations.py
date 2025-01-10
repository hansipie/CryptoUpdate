import streamlit as st
import pandas as pd
import logging
import tzlocal
from modules.database.portfolios import Portfolios
from modules.database.historybase import HistoryBase
from modules.database.operations import operations
from modules.database.swaps import swaps

logger = logging.getLogger(__name__)

st.title("Operations")

g_portfolios = Portfolios(st.session_state.dbfile)
g_historybase = HistoryBase(st.session_state.dbfile)
g_tokens = g_historybase.getTokens()
g_wallets = g_portfolios.get_portfolio_names()

def toTimestamp(date, time):
    # date if formated as yyyy-mm-dd, time as hh:mm:00
    # merge them to a datetime object, convert to UTC and then to epoch timestamp
    datetime_local = pd.to_datetime(f"{date} {time}")
    local_timezone = tzlocal.get_localzone()
    logger.debug(f"Timezone locale: {local_timezone}")
    datetime_utc = datetime_local.tz_localize(local_timezone).tz_convert("UTC")
    timestamp = datetime_utc.timestamp()
    logger.debug(
        f"submitbuy: local_time={datetime_local}, utc_time={datetime_utc}, timestamp={timestamp}"
    )
    return timestamp

def submitbuy(timestamp, from_amount, form_currency, to_amount, to_token, to_wallet):
    logger.debug(
        f"submitbuy: timestamp={timestamp} from_amount={from_amount}, form_currency={form_currency}, to_amount={to_amount}, to_token={to_token}, to_wallet={to_wallet}"
    )

    op.insert(
        "buy", from_amount, to_amount, form_currency, to_token, timestamp, to_wallet
    )

    if to_wallet is not None:
        g_portfolios.set_token_add(to_wallet, to_token, to_amount)

    st.success("Operation submitted")


def submitswap(
    timestamp,
    swap_token_from,
    swap_amount_from,
    swap_wallet_from,
    swap_token_to,
    swap_amount_to,
    swap_wallet_to,
):
    st.warning("This feature is not implemented yet.")


op = operations()
swaps = swaps()

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
                form_currency = st.selectbox("Currency", ["EUR", "USD"], key="form_currency", label_visibility="hidden")
        with col_to:
            col_to_amount, col_to_token = st.columns([3, 1])
            with col_to_amount:
                to_amount = st.number_input(
                    "To", min_value=0.0, format="%.8f", key="to_amount"
                )
            with col_to_token:
                to_token = st.selectbox("Token", g_tokens, index=None, key="to_token", label_visibility="hidden")
            to_wallet = st.selectbox(
                "Portfolio", g_wallets, key="to_wallet", index=None
            )
        if st.form_submit_button("Submit", use_container_width=True):
            timestamp = toTimestamp(date, time)
            submitbuy(
                timestamp, from_amount, form_currency, to_amount, to_token, to_wallet
            )

    buylist = op.get_operations_by_type("buy")
    # save buylist to a dataframe
    df_swaplist = pd.DataFrame(
        buylist,
        columns=[
            "id",
            "type",
            "From",
            "To",
            "Currency",
            "Token",
            "timestamp",
            "Portfolio",
        ],
    )
    # convert timestamp to datetime
    df_swaplist["Date"] = pd.to_datetime(df_swaplist["timestamp"], unit="s", utc=True)
    local_timezone = tzlocal.get_localzone()
    logger.debug(f"Timezone locale: {local_timezone}")
    df_swaplist["Date"] = df_swaplist["Date"].dt.tz_convert(local_timezone)
    # reorder columns
    df_swaplist = df_swaplist[
        ["Date", "From", "Currency", "To", "Token", "Portfolio"]
    ]
    # sort by timestamp in descending order
    df_swaplist.sort_values(by="Date", ascending=False, inplace=True)

    st.dataframe(df_swaplist, use_container_width=True, hide_index=True)

with swap_tab:
    with st.form(key="swap"):
        col_date, col_time = st.columns(2)
        with col_date:
            date = st.date_input("Date", key="swap_date")
        with col_time:
            time = st.time_input("Time", key="swap_time")
        col_from, col_to = st.columns(2)
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
            timestamp = toTimestamp(date, time)
            submitswap(
                timestamp,
                swap_token_from,
                swap_amount_from,
                swap_wallet_from,
                swap_token_to,
                swap_amount_to,
                swap_wallet_to,
            )
    swaplist = swaps.get()
    # save swaplist to a dataframe
    df_swaplist = pd.DataFrame(
        swaplist,
        columns=[
            "timestamp",
            "token_from",
            "amount_from",
            "wallet_from",
            "token_to",
            "amount_to",
            "wallet_to",
            "tag",
        ],
    )
    # convert timestamp to datetime
    df_swaplist["Date"] = pd.to_datetime(df_swaplist["timestamp"], unit="s", utc=True)
    local_timezone = tzlocal.get_localzone()
    logger.debug(f"Timezone locale: {local_timezone}")
    df_swaplist["Date"] = df_swaplist["Date"].dt.tz_convert(local_timezone)

    # reorder columns
    df_swaplist = df_swaplist[
        ["Date", "amount_from", "token_from", "amount_to", "token_to", "wallet_from", "wallet_to"]
    ]
    # sort by timestamp in descending order
    df_swaplist.sort_values(by="Date", ascending=False, inplace=True)

    st.dataframe(df_swaplist, use_container_width=True, hide_index=True)

with import_tab:
    file = st.file_uploader("Upload a file", type=["csv"])
    if file is not None:
        df = pd.read_csv(file)

        # clean up column names
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "")

        df.sort_values(by="timestamp", inplace=True)
        st.dataframe(df)

        if st.button("Import"):
            for index, row in df.iterrows():
                logger.debug(f"\n{row}")
                swaps.insert(
                    row["timestamp"],
                    row["token_from"],
                    row["amount_from"],
                    None,
                    row["token_to"],
                    row["amount_to"],
                    None,
                )
            st.success("Import successfully completed")
