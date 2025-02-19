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
from modules.database.customdata import Customdata
from modules.database.portfolios import Portfolios
from modules.database.tokensdb import TokensDatabase
from modules.database.operations import operations
from modules.database.market import Market
from modules.database.swaps import swaps
from modules.tools import calculate_crypto_rate, update
from modules.utils import get_file_hash, toTimestamp_A

logger = logging.getLogger(__name__)

st.title("Operations")


def submit_buy(
    timestamp: int,
    from_amount: float,
    form_currency: str,
    to_amount: float,
    to_token: str,
    to_wallet: str,
) -> None:
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
        "submitbuy: timestamp=%d from_amount=%f, form_currency=%s, to_amount=%f, to_token=%s, to_wallet=%s",
        timestamp,
        from_amount,
        form_currency,
        to_amount,
        to_token,
        to_wallet,
    )

    g_operation.insert(
        "buy", from_amount, to_amount, form_currency, to_token, timestamp, to_wallet
    )

    if to_wallet is not None:
        Portfolios(st.session_state.settings["dbfile"]).set_token_add(
            to_wallet, to_token, to_amount
        )

    st.toast("Operation submitted", icon=":material/check:")


def submit_swap(
    timestamp: int,
    swap_token_from: str,
    swap_amount_from: float,
    swap_wallet_from: str,
    swap_token_to: str,
    swap_amount_to: float,
    swap_wallet_to: str,
) -> None:
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
        "submitswap: timestamp=%d swap_token_from=%s, swap_amount_from=%f, swap_wallet_from=%s, swap_token_to=%s, swap_amount_to=%f, swap_wallet_to=%s",
        timestamp,
        swap_token_from,
        swap_amount_from,
        swap_wallet_from,
        swap_token_to,
        swap_amount_to,
        swap_wallet_to,
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
    logger.debug("Row selection: %s", st.session_state.swapselection)
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
    logger.debug("Row selection: %s", st.session_state.buyselection)
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
def buy_edit_dialog(data: dict) -> None:
    """Display dialog for editing an existing buy operation.

    Args:
        rowidx: Index of the row to edit in the buy list

    Shows a form pre-filled with the selected operation's data.
    On submit, updates the existing operation.
    """
    logger.debug("Dialog Edit row: %d", data["id"])
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
def swap_edit_dialog(data: dict):
    """Display dialog for editing an existing swap operation.

    Args:
        data: Dictionary containing the swap operation data to edit

    Shows a form pre-filled with the selected operation's data.
    On submit, updates the existing operation.
    """
    logger.debug("Dialog Edit row: %d", data["id"])
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
def buy_delete_dialog(data: dict):
    """Display confirmation dialog for deleting a buy operation.

    Args:
        data: Dictionary containing the buy operation data to delete

    Shows a confirmation prompt with operation details.
    On confirm, deletes the operation.
    """
    logger.debug("Dialog Delete row: %s", data["id"])
    st.dataframe(data, use_container_width=True)
    st.write("Are you sure you want to delete this buy operation?")
    if st.button("Confirm"):
        logger.debug("Delete row: %s - %s", data, type(data["id"]))
        g_operation.delete(data["id"])
        st.rerun()


@st.dialog("Delete Swap")
def swap_delete_dialog(data: dict):
    """Display confirmation dialog for deleting a swap operation.

    Args:
        data: Dictionary containing the swap operation data to delete

    Shows a confirmation prompt with operation details.
    On confirm, deletes the operation.
    """
    logger.debug("Dialog Delete row: %s", data["id"])
    st.dataframe(data, use_container_width=True)
    st.write("Are you sure you want to delete this swap?")
    if st.button("Confirm"):
        logger.debug("Delete row: %s - %s", data, type(data["id"]))
        g_swaps.delete(data["id"])
        st.rerun()


def buy_edit():
    """Handle editing of selected buy operation.

    Shows edit dialog if a row is selected.
    Otherwise displays a warning toast.
    """
    rowidx = buy_row_selected()
    if rowidx is None:
        st.toast("Please select a row", icon=":material/warning:")
    else:
        buy_edit_dialog(df_buy.iloc[rowidx].to_dict())


def swap_edit():
    """Handle editing of selected swap operation.

    Shows edit dialog if a row is selected.
    Otherwise displays a warning toast.
    """
    rowidx = swap_row_selected()
    if rowidx is None:
        st.toast("Please select a row", icon=":material/warning:")
    else:
        swap_edit_dialog(df_swap.iloc[rowidx].to_dict())


def buy_delete():
    """Handle deletion of selected buy operation.

    Shows confirmation dialog if a row is selected.
    Otherwise displays a warning toast.
    """
    logger.debug("Delete row")
    rowidx = buy_row_selected()
    if rowidx is None:
        st.toast("Please select a row", icon=":material/warning:")
    else:
        buy_delete_dialog(df_buy.iloc[rowidx].to_dict())
    pass


def swap_delete():
    """Handle deletion of selected swap operation.

    Shows confirmation dialog if a row is selected.
    Otherwise displays a warning toast.
    """
    logger.debug("Delete row")
    rowidx = swap_row_selected()
    if rowidx is None:
        st.toast("Please select a row", icon=":material/warning:")
    else:
        swap_delete_dialog(df_swap.iloc[rowidx].to_dict())


def calc_perf(df: pd.DataFrame, col_token: str, col_rate: str) -> pd.DataFrame:
    """Calculate current performance metrics for operations.

    Args:
        df: DataFrame containing operations data
        col_token: Name of column containing token symbols
        col_rate: Name of column containing original rates

    Returns:
        DataFrame with added columns for current rates and performance percentages
    """
    market = Market(
        st.session_state.settings["dbfile"],
        st.session_state.settings["coinmarketcap_token"],
    )
    market_df = market.getLastMarket()
    if market_df is None:
        df["Current Rate"] = None
        df["Perf."] = None
    else:
        logger.debug("Market data:\n%s", market_df)
        df["Current Rate"] = df[col_token].map(market_df["value"].to_dict())
        df["Perf."] = ((df["Current Rate"] * 100) / df[col_rate]) - 100
    return df


def swap_perf(rate_swap, rate_now) -> float:
    if rate_swap is None or rate_now is None:
        return None
    return ((rate_now * 100) / rate_swap) - 100


def build_buy_dataframe() -> pd.DataFrame:
    # save buylist to a dataframe
    df = pd.DataFrame(
        g_operation.get_operations_by_type("buy"),
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
    df["Date"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    local_timezone = tzlocal.get_localzone()
    logger.debug("Timezone locale: %s", local_timezone)
    df["Date"] = df["Date"].dt.tz_convert(local_timezone)
    df["Buy Rate"] = df["From"] / df["To"]

    df = calc_perf(df, "Token", "Buy Rate")

    return df


def build_buy_avg_table():
    """Build a table showing average purchase metrics per token.

    Calculates average rates and performance metrics for each token
    bought across all buy operations.

    Returns:
        DataFrame containing token averages and performance indicators
    """
    df = pd.DataFrame(
        g_operation.get_averages(),
        columns=[
            "Token",
            "Total Bought",
            "Currency",
            "Tokens Obtained",
        ],
    )

    if df.empty:
        return df

    green_icon = "🟩"
    yellow_icon = "🟨"
    red_icon = "🟥"

    df["Avg. Rate"] = df["Total Bought"] / df["Tokens Obtained"]
    df = calc_perf(df, "Token", "Avg. Rate")
    df["icon"] = df["Perf."].apply(
        lambda x: green_icon if x > 0 else (red_icon if x < -50 else yellow_icon)
    )
    logger.debug("Average table:\n%s", df)
    # order by Perf.
    df = df.sort_values(by=["Perf."], ascending=False)
    return df


@st.cache_data(
    hash_funcs={str: lambda x: get_file_hash(x) if os.path.isfile(x) else hash(x)},
)
def build_swap_dataframe(dbfile: str) -> pd.DataFrame:
    # save swaps list to a dataframe
    df = pd.DataFrame(
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

    if df.empty:
        return df

    # convert timestamp to datetime
    df["Date"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    local_timezone = tzlocal.get_localzone()
    logger.debug("Timezone locale: %s", local_timezone)
    df["Date"] = df["Date"].dt.tz_convert(local_timezone)

    df["Swap Rate"] = df.apply(
        lambda row: float(row["To Amount"]) / float(row["From Amount"]), axis=1
    )

    df["Current Rate"] = df.apply(
        lambda row: calculate_crypto_rate(
            row["From Token"],
            row["To Token"],
            int(pd.Timestamp.now(tz="UTC").timestamp()),
            dbfile,
        )
        if row["From Token"] != row["To Token"]
        else 1.0,
        axis=1,
    )

    # Calculate performance for each swap
    df["Perf."] = swap_perf(df["Swap Rate"], df["Current Rate"])

    return df


g_wallets = Portfolios(st.session_state.settings["dbfile"]).get_portfolio_names()
g_tokens = TokensDatabase(st.session_state.settings["dbfile"]).get_tokens()

g_operation = operations(st.session_state.settings["dbfile"])
g_swaps = swaps(st.session_state.settings["dbfile"])

# Update prices
with st.sidebar:
    if st.button(
        "Update prices",
        key="update_prices",
        icon=":material/update:",
        use_container_width=True,
    ):
        update()
    # display time since last update
    last_update = Customdata(st.session_state.settings["dbfile"]).get("last_update")
    if last_update:
        last_update = pd.Timestamp.fromtimestamp(float(last_update[0]), tz="UTC")
        last_update = pd.Timestamp.now(tz="UTC") - last_update
        st.markdown(
            " - *Last update: " + str(last_update).split(".", maxsplit=1)[0] + "*"
        )
    else:
        st.markdown(" - *No update yet*")

buy_tab, swap_tab = st.tabs(["Buy", "Swap"])
with buy_tab:
    # build buy table with performance metrics
    df_buy = build_buy_dataframe()

    col_buylist, col_buybtns = st.columns([8, 1])
    with col_buylist:
        if df_buy.empty:
            st.info("No buy operations")
        else:
            st.dataframe(
                df_buy,
                use_container_width=True,
                height=600,
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

    # aquisition average table
    st.title("Aquisition Averages")
    df_avg = build_buy_avg_table()
    if df_avg.empty:
        st.info("No data available")
    else:
        height = (len(df_avg) * 35) + 38
        st.dataframe(
            df_avg,
            use_container_width=True,
            hide_index=True,
            height=height,
            column_order=(
                "icon",
                "Token",
                "Total Bought",
                "Currency",
                "Tokens Obtained",
                "Avg. Rate",
                "Current Rate",
                "Perf.",
            ),
            column_config={
                "icon": st.column_config.TextColumn(label=""),
                "Avg. Rate": st.column_config.NumberColumn(format="%.8f"),
                "Current Rate": st.column_config.NumberColumn(format="%.8f"),
                "Perf.": st.column_config.NumberColumn(format="%.2f%%"),
            },
            key="avgselection",
        )

with swap_tab:
    # build swap table with performance metrics
    df_swap = build_swap_dataframe(st.session_state.settings["dbfile"])

    col_swaplist, col_swapbtns = st.columns([8, 1])
    with col_swaplist:
        if df_swap.empty:
            st.info("No swap operations")
        else:
            st.dataframe(
                df_swap,
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
                    "Swap Rate",
                    "Current Rate",
                    "Perf.",  # Ajout de la colonne Perf. dans l'ordre des colonnes
                ),
                column_config={
                    "From Amount": st.column_config.NumberColumn(format="%.8g"),
                    "To Amount": st.column_config.NumberColumn(format="%.8g"),
                    "Swap Rate": st.column_config.NumberColumn(format="%.8g"),
                    "Current Rate": st.column_config.NumberColumn(format="%.8g"),
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
