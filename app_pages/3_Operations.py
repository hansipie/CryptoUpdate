"""Operations module for CryptoUpdate application.

This module handles buy and swap operations for cryptocurrencies.
It provides interfaces for adding, editing and deleting operations,
as well as displaying operation history and performance metrics.
"""

import logging
import os
import streamlit as st
import pandas as pd
import tzlocal
from modules.database.portfolios import Portfolios
from modules.database.tokensdb import TokensDatabase
from modules.database.operations import operations
from modules.database.market import Market
from modules.database.swaps import swaps
from modules.tools import calculate_crypto_rate
from modules.utils import get_file_hash, toTimestamp_A

logger = logging.getLogger(__name__)

st.title("Operations")


def submit_buy(timestamp: int, from_amount: float, form_currency: str, 
              to_amount: float, to_token: str, to_wallet: str) -> None:
    """Submit a buy operation to the database.
    
    Args:
        timestamp: Unix timestamp of the operation
        from_amount: Amount in source currency
        form_currency: Source currency code (EUR/USD)
        to_amount: Amount in target token
        to_token: Target token symbol
        to_wallet: Destination wallet name
    """
    logger.debug(
        f"submitbuy: timestamp={timestamp} from_amount={from_amount}, form_currency={form_currency}, to_amount={to_amount}, to_token={to_token}, to_wallet={to_wallet}"
    )

    g_operation.insert(
        "buy", from_amount, to_amount, form_currency, to_token, timestamp, to_wallet
    )

    if to_wallet is not None:
        g_portfolios.set_token_add(to_wallet, to_token, to_amount)

    st.success("Operation submitted")


def submit_swap(timestamp: int, swap_token_from: str, swap_amount_from: float,
               swap_wallet_from: str, swap_token_to: str, swap_amount_to: float,
               swap_wallet_to: str) -> None:
    """Submit a swap operation to the database.
    
    Args:
        timestamp: Unix timestamp of the operation
        swap_token_from: Source token symbol
        swap_amount_from: Amount of source token
        swap_wallet_from: Source wallet name
        swap_token_to: Target token symbol
        swap_amount_to: Amount of target token
        swap_wallet_to: Target wallet name
    """
    logger.debug(
        f"submitswap: timestamp={timestamp} swap_token_from={swap_token_from}, swap_amount_from={swap_amount_from}, swap_wallet_from={swap_wallet_from}, swap_token_to={swap_token_to}, swap_amount_to={swap_amount_to}, swap_wallet_to={swap_wallet_to}"
    )
    g_swaps.insert(
        timestamp,
        swap_token_from,
        swap_amount_from,
        swap_wallet_from,
        swap_token_to,
        swap_amount_to,
        swap_wallet_to,
    )


def swap_row_selected():
    """Get the selected row index in the swap table"""
    logger.debug(f"Row selection: {st.session_state.swapselection}")
    if (
        "selection" in st.session_state.swapselection
        and "rows" in st.session_state.swapselection["selection"]
        and len(st.session_state.swapselection["selection"]["rows"]) > 0
    ):
        selected_row = st.session_state.swapselection["selection"]["rows"][0]
        return selected_row
    else:
        logger.debug("No swap row selected")
        return None


def buy_row_selected():
    """Get the selected row index in the buy table"""
    logger.debug(f"Row selection: {st.session_state.buyselection}")
    if (
        "selection" in st.session_state.buyselection
        and "rows" in st.session_state.buyselection["selection"]
        and len(st.session_state.buyselection["selection"]["rows"]) > 0
    ):
        selected_row = st.session_state.buyselection["selection"]["rows"][0]
        return selected_row
    else:
        logger.debug("No buy row selected")
        return None


@st.dialog("Add Buy")
def buy_add() -> None:
    """Display dialog for adding a new buy operation.
    
    Shows a form with fields for date, time, amounts, currencies
    and wallet selection. On submit, creates a new buy operation.
    """
    col_date, col_time = st.columns(2)
    with col_date:
        date = st.date_input("Date", key="buy_date")
    with col_time:
        time = st.time_input("Time", key="buy_time")
    col_amount, col_unit = st.columns(2)
    with col_amount:
        from_amount = st.number_input(
            "From", min_value=0.0, format="%.8g", key="from_amount"
        )
        to_amount = st.number_input("To", min_value=0.0, format="%.8g", key="to_amount")
    with col_unit:
        form_currency = st.selectbox(
            "Currency",
            ["EUR", "USD"],
            key="form_currency",
            label_visibility="hidden",
        )
        to_token = st.selectbox(
            "Token",
            g_tokens,
            index=None,
            key="to_token",
            label_visibility="hidden",
        )
    to_wallet = st.selectbox("Portfolio", g_wallets, key="to_wallet", index=None)
    if st.button("Submit", use_container_width=True):
        timestamp = toTimestamp_A(date, time)
        submit_buy(
            timestamp, from_amount, form_currency, to_amount, to_token, to_wallet
        )
        st.rerun()


@st.dialog("Add Swap")
def swap_add() -> None:
    """Display dialog for adding a new swap operation.
    
    Shows a form with fields for date, time, tokens, amounts
    and wallet selection. On submit, creates a new swap operation.
    """
    col_date, col_time = st.columns(2)
    with col_date:
        date = st.date_input("Date", key="swap_date")
    with col_time:
        time = st.time_input("Time", key="swap_time")
    col_token, col_amount, col_portfolio = st.columns(3)
    with col_token:
        swap_token_from = st.text_input("From Token", key="swap_token_from")
        swap_token_to = st.text_input("To Token", key="swap_token_to")

    with col_amount:
        swap_amount_from = st.number_input(
            "From Amount", min_value=0.0, format="%.8g", key="swap_amount_to"
        )
        swap_amount_to = st.number_input(
            "To Amount", min_value=0.0, format="%.8g", key="swap_amount_from"
        )

    with col_portfolio:
        swap_wallet_from = st.selectbox(
            "From Wallet", g_wallets, index=None, key="swap_wallet_from"
        )
        swap_wallet_to = st.selectbox(
            "To Wallet", g_wallets, index=None, key="swap_wallet_to"
        )
    if st.button("Submit", use_container_width=True):
        timestamp = toTimestamp_A(date, time)
        submit_swap(
            timestamp,
            swap_token_from,
            swap_amount_from,
            swap_wallet_from,
            swap_token_to,
            swap_amount_to,
            swap_wallet_to,
        )
        st.rerun()


@st.dialog("Edit Buy")
def buy_edit_dialog(rowidx: int) -> None:
    """Display dialog for editing an existing buy operation.
    
    Args:
        rowidx: Index of the row to edit in the buy list
        
    Shows a form pre-filled with the selected operation's data.
    On submit, updates the existing operation.
    """
    logger.debug(f"Dialog Edit row: {rowidx}")
    data = st.session_state.buylist.iloc[rowidx].to_dict()
    col_date, col_time = st.columns(2)
    with col_date:
        date = st.date_input("Date", key="buy_date", value=data["Date"])
    with col_time:
        time = st.time_input("Time", key="buy_time", value=data["Date"])
    col_amount, col_unit = st.columns(2)
    with col_amount:
        from_amount = st.number_input(
            "From",
            min_value=0.0,
            format="%.8g",
            key="from_amount",
            value=float(data["From"]),
        )
        to_amount = st.number_input(
            "To", min_value=0.0, format="%.8g", key="to_amount", value=float(data["To"])
        )

    with col_unit:
        if data["Token"] in g_tokens:
            idx_token = g_tokens.index(data["Token"])
        else:
            idx_token = None
        form_currency = st.selectbox(
            "Currency",
            ["EUR", "USD"],
            key="form_currency",
            label_visibility="hidden",
        )
        to_token = st.selectbox(
            "Token",
            g_tokens,
            index=idx_token,
            key="to_token",
            label_visibility="hidden",
        )
    if data["Portfolio"] in g_wallets:
        idx_wallet = g_wallets.index(data["Portfolio"])
    else:
        idx_wallet = None
    to_wallet = st.selectbox("Portfolio", g_wallets, key="to_wallet", index=idx_wallet)
    if st.button("Submit", use_container_width=True):
        timestamp = toTimestamp_A(date, time)
        g_operation.delete(data["id"])
        submit_buy(
            timestamp, from_amount, form_currency, to_amount, to_token, to_wallet
        )
        st.rerun()


@st.dialog("Edit Swap")
def swap_edit_dialog(rowidx: int):
    logger.debug(f"Dialog Edit row: {rowidx}")
    data = st.session_state.swaplist.iloc[rowidx].to_dict()
    col_date, col_time = st.columns(2)
    with col_date:
        date = st.date_input("Date", key="swap_date", value=data["Date"])
    with col_time:
        time = st.time_input("Time", key="swap_time", value=data["Date"])
    col_token, col_amount, col_portfolio = st.columns(3)
    with col_token:
        swap_token_from = st.text_input(
            "From Token", key="swap_token_from", value=data["From Token"]
        )
        swap_token_to = st.text_input(
            "To Token", key="swap_token_to", value=data["To Token"]
        )

    with col_amount:
        swap_amount_from = st.number_input(
            "From Amount",
            min_value=0.0,
            format="%.8g",
            key="swap_amount_to",
            value=float(data["From Amount"]),
        )
        swap_amount_to = st.number_input(
            "To Amount",
            min_value=0.0,
            format="%.8g",
            key="swap_amount_from",
            value=float(data["To Amount"]),
        )

    with col_portfolio:
        if data["From Wallet"] in g_wallets:
            idx_from = g_wallets.index(data["From Wallet"])
        else:
            idx_from = None
        if data["To Wallet"] in g_wallets:
            idx_to = g_wallets.index(data["To Wallet"])
        else:
            idx_to = None
        swap_wallet_from = st.selectbox(
            "From Wallet", g_wallets, index=idx_from, key="swap_wallet_from"
        )
        swap_wallet_to = st.selectbox(
            "To Wallet", g_wallets, index=idx_to, key="swap_wallet_to"
        )
    if st.button("Submit", use_container_width=True):
        timestamp = toTimestamp_A(date, time)
        g_swaps.delete(data["id"])
        submit_swap(
            timestamp,
            swap_token_from,
            swap_amount_from,
            swap_wallet_from,
            swap_token_to,
            swap_amount_to,
            swap_wallet_to,
        )
        st.rerun()


@st.dialog("Delete Buy")
def buy_delete_dialog(rowidx: int):
    logger.debug("Dialog Delete row: %s", rowidx)
    data = st.session_state.buylist.iloc[rowidx].to_dict()
    st.dataframe(data, use_container_width=True)
    st.write("Are you sure you want to delete this buy operation?")
    if st.button("Confirm"):
        logger.debug(f"Delete row: {data} - {type(data['id'])}")
        g_operation.delete(data["id"])
        st.rerun()


@st.dialog("Delete Swap")
def swap_delete_dialog(rowidx: int):
    logger.debug("Dialog Delete row: %s", rowidx)
    data = st.session_state.swaplist.iloc[rowidx].to_dict()
    st.dataframe(data, use_container_width=True)
    st.write("Are you sure you want to delete this swap?")
    if st.button("Confirm"):
        logger.debug(f"Delete row: {data} - {type(data['id'])}")
        g_swaps.delete(data["id"])
        st.rerun()


def buy_edit():
    rowidx = buy_row_selected()
    if rowidx is None:
        st.toast("Please select a row", icon=":material/warning:")
    else:
        buy_edit_dialog(rowidx)


def swap_edit():
    rowidx = swap_row_selected()
    if rowidx is None:
        st.toast("Please select a row", icon=":material/warning:")
    else:
        swap_edit_dialog(rowidx)


def buy_delete():
    logger.debug("Delete row")
    rowidx = buy_row_selected()
    if rowidx is None:
        st.toast("Please select a row", icon=":material/warning:")
    else:
        buy_delete_dialog(rowidx)
    pass


def swap_delete():
    logger.debug("Delete row")
    rowidx = swap_row_selected()
    if rowidx is None:
        st.toast("Please select a row", icon=":material/warning:")
    else:
        swap_delete_dialog(rowidx)


def swap_perf(token_a: str, token_b: str, timestamp: int, dbfile: str) -> float:
    """Calculate the performance of a swap operation.
    
    Args:
        token_a: First token symbol
        token_b: Second token symbol
        timestamp: Unix timestamp of the swap
        dbfile: Path to the database file
        
    Returns:
        Float percentage change in exchange rate between tokens,
        or None if calculation fails
    """
    rate_swap = calculate_crypto_rate(
        token_a, token_b, timestamp, dbfile
    )

    rate_now = calculate_crypto_rate(
        token_a,
        token_b,
        int(pd.Timestamp.now(tz="UTC").timestamp()),
        dbfile,
    )

    if rate_swap is None or rate_now is None:
        return None
    return (rate_now * 100) / rate_swap - 100


@st.cache_data(
    hash_funcs={str: lambda x: get_file_hash(x) if os.path.isfile(x) else hash(x)},
)
def build_buy_table(buytable: pd.DataFrame, dbfile: str) -> pd.DataFrame:
    """Build the buy operations table with performance metrics.
    
    Args:
        buytable: DataFrame containing raw buy operations
        dbfile: Path to the database file
        
    Returns:
        DataFrame with added Date and performance columns
        
    Adds columns for:
    - Date (localized timestamp)
    - Buy Rate (original price)
    - Current Rate (current price)
    - Performance (% change)
    """
    # convert timestamp to datetime
    buytable["Date"] = pd.to_datetime(buytable["timestamp"], unit="s", utc=True)
    local_timezone = tzlocal.get_localzone()
    logger.debug("Timezone locale: %s", local_timezone)
    buytable["Date"] = buytable["Date"].dt.tz_convert(local_timezone)

    # calculate performance
    market = Market(
        dbfile, st.session_state.settings["coinmarketcap_token"]
    )
    market_df = market.getLastMarket()
    if market_df is None:
        st.error("No market data available")
        st.stop()
    logger.debug("Market data:\n%s", market_df.to_string())

    buytable["Buy Rate"] = buytable["From"] / buytable["To"]
    buytable["Current Rate"] = buytable["Token"].map(market_df["value"].to_dict())
    buytable["Perf."] = (buytable["Current Rate"] * 100) / buytable["Buy Rate"] - 100

    return buytable


@st.cache_data(
    hash_funcs={str: lambda x: get_file_hash(x) if os.path.isfile(x) else hash(x)},
)
def build_swap_table(swaptable: pd.DataFrame, dbfile: str) -> pd.DataFrame:
    """Build the swap operations table with performance metrics.
    
    Args:
        swaptable: DataFrame containing raw swap operations
        dbfile: Path to the database file
        
    Returns:
        DataFrame with added Date and performance columns
        
    Adds columns for:
    - Date (localized timestamp) 
    - Performance (% change in exchange rate)
    """
    # convert timestamp to datetime
    swaptable["Date"] = pd.to_datetime(swaptable["timestamp"], unit="s", utc=True)
    local_timezone = tzlocal.get_localzone()
    logger.debug("Timezone locale: %s", local_timezone)
    swaptable["Date"] = swaptable["Date"].dt.tz_convert(local_timezone)

    # Calculate performance for each swap
    swaptable["Perf."] = swaptable.apply(
        lambda row: swap_perf(row["To Token"], row["From Token"], row["timestamp"], dbfile),
        axis=1,
    )

    return swaptable


g_portfolios = Portfolios(st.session_state.dbfile)
g_historybase = TokensDatabase(st.session_state.dbfile)
g_tokens = g_historybase.getTokens()
g_wallets = g_portfolios.get_portfolio_names()
g_operation = operations()
g_swaps = swaps()

if "cryto_rate" not in st.session_state:
    st.session_state.cryto_rate = {}

buy_tab, swap_tab = st.tabs(["Buy", "Swap"])
with buy_tab:
    buylist = g_operation.get_operations_by_type("buy")
    # save buylist to a dataframe
    st.session_state.buylist = pd.DataFrame(
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

    # build buy table with performance metrics
    st.session_state.buylist = build_buy_table(st.session_state.buylist, st.session_state.dbfile)

    col_buylist, col_buybtns = st.columns([8, 1])
    with col_buylist:
        st.dataframe(
            st.session_state.buylist,
            use_container_width=True,
            height=700,
            hide_index=True,
            column_order=(
                "Date",
                "From",
                "Currency",
                "To",
                "Token",
                "Portfolio",
                "Buy Rate",
                "Current Rate",
                "Perf.",
            ),
            column_config={
                "From": st.column_config.NumberColumn(format="%.8g"),
                "To": st.column_config.NumberColumn(format="%.8g"),
                "Buy Rate": st.column_config.NumberColumn(format="%.8g"),
                "Current Rate": st.column_config.NumberColumn(format="%.8g"),
                "Perf.": st.column_config.NumberColumn(format="%.2f%%"),
            },
            on_select="rerun",
            selection_mode="single-row",
            key="buyselection",
        )
    with col_buybtns:
        st.button(
            "New",
            on_click=buy_add,
            use_container_width=True,
            icon=":material/add:",
            key="buy_new",
        )
        st.button(
            "Edit",
            on_click=buy_edit,
            use_container_width=True,
            icon=":material/edit:",
            key="buy_edit",
        )
        st.button(
            "Delete",
            on_click=buy_delete,
            use_container_width=True,
            icon=":material/delete:",
            key="buy_delete",
        )

with swap_tab:
    # save swaps list to a dataframe
    st.session_state.swaplist = pd.DataFrame(
        g_swaps.get(),
        columns=[
            "id",
            "timestamp",
            "From Token",
            "From Amount",
            "From Wallet",
            "To Token",
            "To Amount",
            "To Wallet",
            "tag",
        ],
    )

    # build swap table with performance metrics
    st.session_state.swaplist = build_swap_table(st.session_state.swaplist, st.session_state.dbfile)

    col_swaplist, col_swapbtns = st.columns([8, 1])
    with col_swaplist:
        st.dataframe(
            st.session_state.swaplist,
            use_container_width=True,
            height=700,
            hide_index=True,
            column_order=(
                "Date",
                "From Amount",
                "From Token",
                "To Amount",
                "To Token",
                "From Wallet",
                "To Wallet",
                "Perf.",  # Ajout de la colonne Perf. dans l'ordre des colonnes
            ),
            column_config={
                "From Amount": st.column_config.NumberColumn(format="%.8g"),
                "To Amount": st.column_config.NumberColumn(format="%.8g"),
                "Perf.": st.column_config.NumberColumn(
                    format="%.2f%%"
                ),  # Configuration du format pour Perf.
            },
            on_select="rerun",
            selection_mode="single-row",
            key="swapselection",
        )
    with col_swapbtns:
        st.button(
            "New",
            on_click=swap_add,
            use_container_width=True,
            icon=":material/add:",
            key="swap_new",
        )
        st.button(
            "Edit",
            on_click=swap_edit,
            use_container_width=True,
            icon=":material/edit:",
            key="swap_edit",
        )
        st.button(
            "Delete",
            on_click=swap_delete,
            use_container_width=True,
            icon=":material/delete:",
            key="swap_delete",
        )
