"""Operations module for CryptoUpdate application.

This module handles buy and swap operations for cryptocurrencies.
It provides interfaces for adding, editing and deleting operations,
as well as displaying operation history and performance metrics.
"""

import logging
import os

import pandas as pd
import streamlit as st
import tzlocal

from modules.database.customdata import Customdata
from modules.database.market import Market
from modules.database.operations import Operations
from modules.database.portfolios import Portfolios
from modules.database.swaps import Swaps
from modules.database.tokensdb import TokensDatabase
from modules.tools import (
    _get_api_fiat_rate,
    _get_api_latest_prices,
    amount_column,
    batch_convert_historical,
    batch_convert_historical_api,
    calc_perf_api,
    calculate_crypto_rate,
    calculate_crypto_rate_api,
    is_privacy_mode,
    mask_dataframe,
    parse_last_update,
    update,
)
from modules.utils import to_timestamp_a as toTimestamp_A

logger = logging.getLogger(__name__)

st.title("Operations")


def submit_buy(
    timestamp: int,
    from_amount: float,
    form_currency: str,
    to_amount: float,
    to_token: str,
    to_wallet: str,
    adjust_portfolios: bool = False,
) -> None:
    """Submit a buy operation to the database.

    Args:
        timestamp: Unix timestamp of the operation
        from_amount: Amount in source currency
        form_currency: Source currency code (EUR/USD)
        to_amount: Amount in target token
        to_token: Target token symbol
        to_wallet: Destination wallet name
        adjust_portfolios: If True, add to_amount of to_token to the wallet's
            holdings (same transaction as the operation)
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
        "buy",
        from_amount,
        to_amount,
        form_currency,
        to_token,
        timestamp,
        to_wallet,
        portfolio_adjusted=adjust_portfolios,
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
    note: str | None = None,
    adjust_portfolios: bool = False,
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
        note: Optional free-text annotation
        adjust_portfolios: If True, move the amounts between the wallets' holdings
    """
    logger.debug(
        (
            "submitswap: timestamp=%d swap_token_from=%s, swap_amount_from=%f, "
            "swap_wallet_from=%s, swap_token_to=%s, swap_amount_to=%f, "
            "swap_wallet_to=%s"
        ),
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
        note=note,
        portfolio_adjusted=adjust_portfolios,
    )


def rows_selected(selectable, max_len: int) -> list:
    """Get the selected row index in the swap table.

    Selection state can outlive the dataframe it was captured from (e.g. after
    an archive/delete or a refresh shrinks the table), so indices no longer
    valid for the current dataframe (>= max_len) are dropped here to avoid an
    out-of-bounds .iloc[] downstream.
    """
    logger.debug("Row selection: %s", selectable)
    if (
        "selection" in selectable
        and "rows" in selectable["selection"]
        and len(selectable["selection"]["rows"]) > 0
    ):
        selected_row = [i for i in selectable["selection"]["rows"] if i < max_len]
        if not selected_row:
            logger.debug("Selection is stale for current data, ignoring")
            return None
        return selected_row
    else:
        logger.debug("No swap row selected")
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
    adjust_portfolios = st.checkbox(
        "Synchronize portfolios", value=False, key="buy_adjust_portfolios"
    )
    if st.button("Submit", width="stretch"):
        if to_wallet is None or to_token is None:
            st.error("Token and portfolio are required")
            return
        timestamp = toTimestamp_A(date, time)
        submit_buy(
            timestamp,
            from_amount,
            form_currency,
            to_amount,
            to_token,
            to_wallet,
            adjust_portfolios=adjust_portfolios,
        )
        st.rerun()


def clean_swap_form(
    token_from: str, token_to: str, amount_from: float, amount_to: float
) -> tuple:
    """Normalize the swap form tokens (trim + uppercase) and validate it.

    Returns:
        (token_from, token_to, error): error is None when the form is valid
    """
    token_from = (token_from or "").strip().upper()
    token_to = (token_to or "").strip().upper()
    if not token_from or not token_to:
        return token_from, token_to, "From Token and To Token are required"
    if amount_from <= 0 or amount_to <= 0:
        return token_from, token_to, "Amounts must be greater than 0"
    return token_from, token_to, None


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
            "From Amount", min_value=0.0, format="%.8g", key="swap_amount_from"
        )
        swap_amount_to = st.number_input(
            "To Amount", min_value=0.0, format="%.8g", key="swap_amount_to"
        )

    with col_portfolio:
        swap_wallet_from = st.selectbox(
            "From Wallet", g_wallets, index=None, key="swap_wallet_from"
        )
        swap_wallet_to = st.selectbox(
            "To Wallet", g_wallets, index=None, key="swap_wallet_to"
        )
    swap_note = st.text_area("Note", key="swap_note", value="")
    adjust_portfolios = st.checkbox(
        "Synchronize portfolios", value=False, key="swap_adjust_portfolios"
    )
    if st.button("Submit", width="stretch"):
        if swap_wallet_from is None or swap_wallet_to is None:
            st.error("From Wallet and To Wallet are required")
            return
        swap_token_from, swap_token_to, error = clean_swap_form(
            swap_token_from, swap_token_to, swap_amount_from, swap_amount_to
        )
        if error:
            st.error(error)
            return
        timestamp = toTimestamp_A(date, time)
        submit_swap(
            timestamp,
            swap_token_from,
            swap_amount_from,
            swap_wallet_from,
            swap_token_to,
            swap_amount_to,
            swap_wallet_to,
            note=swap_note,
            adjust_portfolios=adjust_portfolios,
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
    was_adjusted = g_operation.is_portfolio_adjusted(data["id"])
    adjust_portfolios = st.checkbox(
        "Synchronize portfolios", value=was_adjusted, key="buy_adjust_portfolios"
    )
    if st.button("Submit", width="stretch"):
        if to_wallet is None or to_token is None:
            st.error("Token and portfolio are required")
            return
        timestamp = toTimestamp_A(date, time)
        # old effect undone + new row inserted in a single transaction
        g_operation.replace(
            data["id"],
            "buy",
            from_amount,
            to_amount,
            form_currency,
            to_token,
            timestamp,
            to_wallet,
            portfolio_adjusted=adjust_portfolios,
        )
        st.toast("Operation submitted", icon=":material/check:")
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
            key="swap_edit_amount_from",
            value=float(data["From Amount"]),
        )
        swap_amount_to = st.number_input(
            "To Amount",
            min_value=0.0,
            format="%.8g",
            key="swap_edit_amount_to",
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
    swap_note = st.text_area("Note", key="swap_note", value=data.get("note") or "")
    was_adjusted = g_swaps.is_portfolio_adjusted(data["id"])
    adjust_portfolios = st.checkbox(
        "Synchronize portfolios", value=was_adjusted, key="swap_adjust_portfolios"
    )
    if st.button("Submit", width="stretch"):
        if swap_wallet_from is None or swap_wallet_to is None:
            st.error("From Wallet and To Wallet are required")
            return
        swap_token_from, swap_token_to, error = clean_swap_form(
            swap_token_from, swap_token_to, swap_amount_from, swap_amount_to
        )
        if error:
            st.error(error)
            return
        timestamp = toTimestamp_A(date, time)
        # old effect undone + new row inserted in a single transaction
        g_swaps.replace(
            data["id"],
            timestamp,
            swap_token_from,
            swap_amount_from,
            swap_wallet_from,
            swap_token_to,
            swap_amount_to,
            swap_wallet_to,
            note=swap_note,
            portfolio_adjusted=adjust_portfolios,
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
    shown = data
    if is_privacy_mode():
        # From / To (optionally "From (EUR)") hold the bought amounts
        shown = {
            k: (
                "••••" if k in ("From", "To") or k.startswith(("From (", "To (")) else v
            )
            for k, v in data.items()
        }
    st.dataframe(shown, width="stretch")
    st.write("Are you sure you want to delete this buy operation?")
    was_adjusted = g_operation.is_portfolio_adjusted(data["id"])
    sync_portfolios = st.checkbox(
        "Synchronize portfolios",
        value=was_adjusted,
        key="buy_delete_sync_portfolios",
        help="Remove the bought amount from the portfolio",
    )
    if st.button("Confirm"):
        logger.debug("Delete row: %s - %s", data, type(data["id"]))
        g_operation.delete(data["id"], revert_portfolio=sync_portfolios)
        st.rerun()


@st.dialog("Delete Swap")
def swap_delete_dialog(rows: list, df_swaps_active: pd.DataFrame):
    """Display confirmation dialog for deleting a swap operation.

    Args:
        data: Dictionary containing the swap operation data to delete

    Shows a confirmation prompt with operation details.
    On confirm, deletes the operation.
    """
    todelete = []
    for rowidx in rows:
        data = df_swaps_active.iloc[rowidx].to_dict()
        todelete.append(data)

    logger.debug("Dialog Delete row: %s", todelete)
    st.write(f"{len(todelete)} swap(s) selected. Are you sure you want to delete?")

    if st.button("Confirm"):
        for data in todelete:
            logger.debug("Delete row: %s - %s", data, type(data["id"]))
            g_swaps.delete(data["id"])
        st.rerun()


@st.dialog("Archive Swap")
def swap_archive_dialog(rows: list, df_swaps_active: pd.DataFrame):
    """Display confirmation dialog for archiving a swap operation.

    Args:
        data: Dictionary containing the swap operation data to archive

    Shows a confirmation prompt with operation details.
    On confirm, archives the operation.
    """
    toarchive = []
    for rowidx in rows:
        data = df_swaps_active.iloc[rowidx].to_dict()
        toarchive.append(data)

    logger.debug("Dialog Archive row: %s", toarchive)
    st.write(f"{len(toarchive)} swap(s) selected. Are you sure you want to archive?")

    if st.button("Confirm"):
        for data in toarchive:
            logger.debug("Archive row: %s - %s", data, type(data["id"]))
            g_swaps.update_tag(data["id"], "archived")
        st.rerun()


@st.dialog("Unarchive Swap")
def swap_unarchive_dialog(rows: list, df_swaps_archived: pd.DataFrame):
    """Display confirmation dialog for unarchiving a swap operation.

    Args:
        data: Dictionary containing the swap operation data to unarchive

    Shows a confirmation prompt with operation details.
    On confirm, unarchives the operation.
    """
    tounarchive = []
    for rowidx in rows:
        data = df_swaps_archived.iloc[rowidx].to_dict()
        tounarchive.append(data)

    logger.debug("Dialog Unarchive row: %s", tounarchive)
    st.write(
        f"{len(tounarchive)} swap(s) selected. Are you sure you want to unarchive?"
    )

    if st.button("Confirm"):
        for data in tounarchive:
            logger.debug("Unarchive row: %s - %s", data, type(data["id"]))
            g_swaps.update_tag(data["id"], None)
        st.rerun()


@st.dialog("Delete Archived Swap")
def swap_arch_delete_dialog(rows: list, df_swaps_archived: pd.DataFrame):
    """Display confirmation dialog for deleting an archived swap operation.

    Args:
        rows: List of row indices to delete

    Shows a confirmation prompt with operation details.
    On confirm, deletes the archived operations.
    """
    todelete = []
    for rowidx in rows:
        data = df_swaps_archived.iloc[rowidx].to_dict()
        todelete.append(data)

    logger.debug("Dialog Delete archived row: %s", todelete)
    st.write(
        f"{len(todelete)} archived swap(s) selected. Are you sure you want to delete?"
    )

    if st.button("Confirm"):
        for data in todelete:
            logger.debug("Delete archived row: %s - %s", data, type(data["id"]))
            g_swaps.delete(data["id"])
        st.rerun()


def buy_edit():
    """Handle editing of selected buy operation.

    Shows edit dialog if a row is selected.
    Otherwise displays a warning toast.
    """
    _sel = rows_selected(st.session_state.buyselection, len(df_buy))
    rowidx = _sel[0] if _sel is not None else None
    if rowidx is None:
        st.toast("Please select a row", icon=":material/warning:")
    else:
        buy_edit_dialog(df_buy.iloc[rowidx].to_dict())


def buy_delete():
    """Handle deletion of selected buy operation.

    Shows confirmation dialog if a row is selected.
    Otherwise displays a warning toast.
    """
    logger.debug("Delete row")
    _sel = rows_selected(st.session_state.buyselection, len(df_buy))
    rowidx = _sel[0] if _sel is not None else None
    if rowidx is None:
        st.toast("Please select a row", icon=":material/warning:")
    else:
        buy_delete_dialog(df_buy.iloc[rowidx].to_dict())


def swap_edit(df_swaps_active: pd.DataFrame):
    """Handle editing of selected swap operation.

    Shows edit dialog if a row is selected.
    Otherwise displays a warning toast.
    """
    rowidx = rows_selected(st.session_state.swapselection, len(df_swaps_active))
    if rowidx is None:
        st.toast("Please select a row", icon=":material/warning:")
    elif len(rowidx) > 1:
        st.toast("Please select only one row", icon=":material/warning:")
    else:
        swap_edit_dialog(df_swaps_active.iloc[rowidx[0]].to_dict())


def swap_delete(df_swaps_active: pd.DataFrame):
    """Handle deletion of selected swap operation.

    Shows confirmation dialog if a row is selected.
    Otherwise displays a warning toast.
    """
    logger.debug("Delete row")
    rowidx = rows_selected(st.session_state.swapselection, len(df_swaps_active))
    if rowidx is None:
        st.toast("Please select a row", icon=":material/warning:")
    else:
        swap_delete_dialog(rowidx, df_swaps_active)


def swap_archive(df_swaps_active: pd.DataFrame):
    """Handle archiving of selected swap operation.

    Shows confirmation dialog if a row is selected.
    Otherwise displays a warning toast.
    """
    logger.debug("Archive row")
    rowidx = rows_selected(st.session_state.swapselection, len(df_swaps_active))
    if rowidx is None:
        st.toast("Please select a row", icon=":material/warning:")
    else:
        swap_archive_dialog(rowidx, df_swaps_active)


def swap_unarchive(df_swaps_archived: pd.DataFrame):
    """Handle unarchiving of selected swap operation.

    Shows confirmation dialog if a row is selected.
    Otherwise displays a warning toast.
    """
    logger.debug("Unarchive row")
    rowidx = rows_selected(st.session_state.swapachselection, len(df_swaps_archived))
    if rowidx is None:
        st.toast("Please select a row", icon=":material/warning:")
    else:
        swap_unarchive_dialog(rowidx, df_swaps_archived)


def swap_arch_delete(df_swaps_archived: pd.DataFrame):
    """Handle deletion of selected archived swap operation.

    Shows confirmation dialog if a row is selected.
    Otherwise displays a warning toast.
    """
    logger.debug("Delete archived row")
    rowidx = rows_selected(st.session_state.swapachselection, len(df_swaps_archived))
    if rowidx is None:
        st.toast("Please select a row", icon=":material/warning:")
    else:
        swap_arch_delete_dialog(rowidx, df_swaps_archived)


@st.dialog("Add Airdrop")
def airdrop_add() -> None:
    """Display dialog for recording an airdrop (tokens received for free)."""
    col_date, col_time = st.columns(2)
    with col_date:
        date = st.date_input("Date", key="airdrop_date")
    with col_time:
        time = st.time_input("Time", key="airdrop_time")
    amount = st.number_input(
        "Amount", min_value=0.0, format="%.8g", key="airdrop_amount"
    )
    token = st.selectbox("Token", g_tokens, index=None, key="airdrop_token")
    wallet = st.selectbox("Portfolio", g_wallets, key="airdrop_wallet", index=None)
    adjust_portfolios = st.checkbox(
        "Synchronize portfolios", value=False, key="airdrop_adjust_portfolios"
    )
    if st.button("Submit", width="stretch", key="airdrop_add_submit"):
        if wallet is None or token is None:
            st.error("Token and portfolio are required")
            return
        submit_buy(
            toTimestamp_A(date, time),
            0.0,
            "EUR",
            amount,
            token,
            wallet,
            adjust_portfolios=adjust_portfolios,
        )
        st.rerun()


@st.dialog("Edit Airdrop")
def airdrop_edit_dialog(data: dict) -> None:
    """Display dialog for editing an airdrop, replacing the stored row."""
    col_date, col_time = st.columns(2)
    with col_date:
        date = st.date_input("Date", key="airdrop_date", value=data["Date"])
    with col_time:
        time = st.time_input("Time", key="airdrop_time", value=data["Date"])
    amount = st.number_input(
        "Amount",
        min_value=0.0,
        format="%.8g",
        key="airdrop_amount",
        value=float(data["Amount"]),
    )
    idx_token = g_tokens.index(data["Token"]) if data["Token"] in g_tokens else None
    token = st.selectbox("Token", g_tokens, index=idx_token, key="airdrop_token")
    idx_wallet = (
        g_wallets.index(data["Portfolio"]) if data["Portfolio"] in g_wallets else None
    )
    wallet = st.selectbox(
        "Portfolio", g_wallets, index=idx_wallet, key="airdrop_wallet"
    )
    was_adjusted = bool(data["Synchronized"])
    adjust_portfolios = st.checkbox(
        "Synchronize portfolios", value=was_adjusted, key="airdrop_adjust_portfolios"
    )
    if st.button("Submit", width="stretch", key="airdrop_edit_submit"):
        if wallet is None or token is None:
            st.error("Token and portfolio are required")
            return
        g_operation.replace(
            data["id"],
            "buy",
            0.0,
            amount,
            "EUR",
            token,
            toTimestamp_A(date, time),
            wallet,
            portfolio_adjusted=adjust_portfolios,
        )
        st.toast("Operation submitted", icon=":material/check:")
        st.rerun()


def airdrop_edit() -> None:
    """Open the edit dialog for the selected airdrop, or warn if none."""
    _sel = rows_selected(st.session_state.airdropselection, len(df_airdrop))
    if _sel is None:
        st.toast("Please select a row", icon=":material/warning:")
    else:
        airdrop_edit_dialog(df_airdrop.iloc[_sel[0]].to_dict())


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
    market_df = market.get_last_market()
    if market_df is None:
        df["Current Rate"] = None
        df["Perf."] = None
    else:
        logger.debug("Market data:\n%s", market_df)
        df["Current Rate"] = df[col_token].map(market_df["value"].to_dict())
        df["Perf."] = (
            (df["Current Rate"] * 100) / df[col_rate].replace(0, pd.NA)
        ) - 100
    return df


def swap_perf(rate_swap, rate_now) -> float:
    if rate_swap is None or rate_now is None:
        return None
    if rate_now == 0:
        return None
    return ((rate_swap * 100) / rate_now) - 100


def _db_stamp() -> tuple:
    """Cache key reflecting the database state: it changes on every write."""
    stat = os.stat(st.session_state.settings["dbfile"])
    return (stat.st_mtime_ns, stat.st_size)


# The tables below are rebuilt on every rerun (each row selection is one), so
# they are cached. `db_stamp` is only there to key the cache on the database
# state (an "Update prices" or an edit invalidates it); `ttl` bounds the age of
# API prices.
@st.cache_data(ttl=600, show_spinner=False)
def build_buy_dataframe(
    convert_from: str | None = None,
    convert_to: str | None = None,
    use_api: bool = False,
    db_stamp: tuple | None = None,  # pylint: disable=unused-argument
) -> pd.DataFrame:
    # Pre-load API data once for the entire function
    if use_api:
        prices_usd = _get_api_latest_prices()
        usd_to_eur = _get_api_fiat_rate()
        if not prices_usd:
            logger.warning("API: aucun prix crypto disponible")
        if usd_to_eur is None:
            logger.warning("API: taux USD→EUR non disponible")
    else:
        prices_usd = None
        usd_to_eur = None

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

    # Ensure amount columns are numeric
    df["From"] = pd.to_numeric(df["From"], errors="coerce")
    df["To"] = pd.to_numeric(df["To"], errors="coerce")

    # Airdrops (source = 0) have their own tab
    df = df[df["From"] != 0].reset_index(drop=True)

    # convert timestamp to datetime
    df["Date"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    local_timezone = tzlocal.get_localzone()
    logger.debug("Timezone locale: %s", local_timezone)
    df["Date"] = df["Date"].dt.tz_convert(local_timezone).dt.tz_localize(None)
    df["Buy Rate"] = df["From"] / df["To"].replace(0, pd.NA)

    # Historical conversion of From column
    if convert_from and not df.empty:
        col_name = f"From ({convert_from})"
        if use_api:
            df[col_name] = batch_convert_historical_api(
                df,
                "From",
                "Currency",
                convert_from,
                "timestamp",
            )
        else:
            df[col_name] = batch_convert_historical(
                df,
                "From",
                "Currency",
                convert_from,
                "timestamp",
                st.session_state.settings["dbfile"],
            )

    # Historical conversion of To column
    if convert_to and not df.empty:
        col_name = f"To ({convert_to})"
        if use_api:
            df[col_name] = batch_convert_historical_api(
                df,
                "To",
                "Token",
                convert_to,
                "timestamp",
            )
        else:
            df[col_name] = batch_convert_historical(
                df,
                "To",
                "Token",
                convert_to,
                "timestamp",
                st.session_state.settings["dbfile"],
            )

    # Recalculate Buy Rate if conversions are active
    if (convert_from or convert_to) and not df.empty:
        from_col = f"From ({convert_from})" if convert_from else "From"
        to_col = f"To ({convert_to})" if convert_to else "To"
        df["Converted Rate"] = df[from_col] / df[to_col].replace(0, pd.NA)

    # Current Rate and Perf. — use converted units when active
    if (convert_from or convert_to) and not df.empty:
        if use_api:
            df["Current Rate"] = df.apply(
                lambda row: calculate_crypto_rate_api(
                    convert_to if convert_to else row["Token"],
                    convert_from if convert_from else row["Currency"],
                    prices_usd=prices_usd,
                    usd_to_eur=usd_to_eur,
                ),
                axis=1,
            )
        else:
            now_ts = int(pd.Timestamp.now(tz="UTC").timestamp())
            dbfile = st.session_state.settings["dbfile"]
            df["Current Rate"] = df.apply(
                lambda row: calculate_crypto_rate(
                    convert_to if convert_to else row["Token"],
                    convert_from if convert_from else row["Currency"],
                    now_ts,
                    dbfile,
                ),
                axis=1,
            )
        df["Perf."] = (
            (df["Current Rate"] * 100) / df["Converted Rate"].replace(0, pd.NA)
        ) - 100
    else:
        if use_api:
            df = calc_perf_api(
                df,
                "Token",
                "Buy Rate",
                col_currency="Currency",
                prices_usd=prices_usd,
                usd_to_eur=usd_to_eur,
            )
        else:
            df = calc_perf(df, "Token", "Buy Rate")

    return df


@st.cache_data(ttl=600, show_spinner=False)
def build_airdrop_dataframe(
    currency: str,
    use_api: bool = False,
    db_stamp: tuple | None = None,  # pylint: disable=unused-argument
) -> pd.DataFrame:
    """Build the airdrop table: buy operations whose source amount is 0.

    The "Value" column is the airdropped amount priced in `currency` at the
    date of the transaction.
    """
    df = pd.DataFrame(
        g_operation.get_operations_by_type("buy"),
        columns=[
            "id",
            "type",
            "From",
            "Amount",
            "Currency",
            "Token",
            "timestamp",
            "Portfolio",
        ],
    )
    df["From"] = pd.to_numeric(df["From"], errors="coerce")
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
    df = df[df["From"] == 0].sort_values("timestamp", ascending=False)
    df = df.reset_index(drop=True)
    df["Date"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    df["Date"] = df["Date"].dt.tz_convert(tzlocal.get_localzone()).dt.tz_localize(None)
    df["Synchronized"] = df["id"].map(g_operation.is_portfolio_adjusted)
    if df.empty:
        df["Value"] = pd.Series(dtype=float)
    elif use_api:
        df["Value"] = batch_convert_historical_api(
            df, "Amount", "Token", currency, "timestamp"
        )
    else:
        df["Value"] = batch_convert_historical(
            df,
            "Amount",
            "Token",
            currency,
            "timestamp",
            st.session_state.settings["dbfile"],
        )
    return df


@st.cache_data(ttl=600, show_spinner=False)
def build_buy_avg_table(
    use_api: bool = False,
    db_stamp: tuple | None = None,  # pylint: disable=unused-argument
):
    """Build a table showing average purchase metrics per token.

    Calculates average rates and performance metrics for each token
    bought across all buy operations.

    Args:
        use_api: If True, use MarketRaccoon API for current rates

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

    df["Avg. Rate"] = df["Total Bought"] / df["Tokens Obtained"].replace(0, pd.NA)
    if use_api:
        prices_usd = _get_api_latest_prices()
        usd_to_eur = _get_api_fiat_rate()
        df = calc_perf_api(
            df, "Token", "Avg. Rate", prices_usd=prices_usd, usd_to_eur=usd_to_eur
        )
    else:
        df = calc_perf(df, "Token", "Avg. Rate")
    logger.debug("Average table:\n%s", df)
    # order by Perf.
    df = df.sort_values(by=["Perf."], ascending=False)
    return df


@st.cache_data(ttl=600, show_spinner=False)
def build_swap_dataframes(
    db_file: str,
    convert_from: str | None = None,
    convert_to: str | None = None,
    use_api: bool = False,
    db_stamp: tuple | None = None,  # pylint: disable=unused-argument
) -> pd.DataFrame:
    swaps = Swaps(db_file)
    columns = [
        "id",
        "timestamp",
        "From Token",
        "From Amount",
        "From Wallet",
        "To Token",
        "To Amount",
        "To Wallet",
        "tag",
        "note",
    ]
    df1 = pd.DataFrame(swaps.get_by_tag(""), columns=columns)
    if not df1.empty:
        df1 = build_swap_dataframe(df1, db_file, convert_from, convert_to, use_api)

    df2 = pd.DataFrame(swaps.get_by_tag("archived"), columns=columns)
    if not df2.empty:
        df2 = build_swap_dataframe(df2, db_file, convert_from, convert_to, use_api)

    return df1, df2


def build_swap_dataframe(
    df: pd.DataFrame,
    db_file: str,
    convert_from: str | None = None,
    convert_to: str | None = None,
    use_api: bool = False,
) -> pd.DataFrame:
    # Pre-load API data once for the entire function
    if use_api:
        prices_usd = _get_api_latest_prices()
        usd_to_eur = _get_api_fiat_rate()
        if not prices_usd:
            logger.warning("API: aucun prix crypto disponible")
        if usd_to_eur is None:
            logger.warning("API: taux USD→EUR non disponible")
    else:
        prices_usd = None
        usd_to_eur = None

    # Ensure amount columns are numeric
    df["From Amount"] = pd.to_numeric(df["From Amount"], errors="coerce")
    df["To Amount"] = pd.to_numeric(df["To Amount"], errors="coerce")

    # convert timestamp to datetime
    df["Date"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    local_timezone = tzlocal.get_localzone()
    logger.debug("Timezone locale: %s", local_timezone)
    df["Date"] = df["Date"].dt.tz_convert(local_timezone).dt.tz_localize(None)

    df["Swap Rate"] = df["To Amount"] / df["From Amount"].replace(0, pd.NA)

    # Historical conversion of From Amount column
    if convert_from and not df.empty:
        col_name = f"From Amount ({convert_from})"
        if use_api:
            df[col_name] = batch_convert_historical_api(
                df,
                "From Amount",
                "From Token",
                convert_from,
                "timestamp",
            )
        else:
            df[col_name] = batch_convert_historical(
                df,
                "From Amount",
                "From Token",
                convert_from,
                "timestamp",
                db_file,
            )

    # Historical conversion of To Amount column
    if convert_to and not df.empty:
        col_name = f"To Amount ({convert_to})"
        if use_api:
            df[col_name] = batch_convert_historical_api(
                df,
                "To Amount",
                "To Token",
                convert_to,
                "timestamp",
            )
        else:
            df[col_name] = batch_convert_historical(
                df,
                "To Amount",
                "To Token",
                convert_to,
                "timestamp",
                db_file,
            )

    # Recalculate Swap Rate if conversions are active
    if (convert_from or convert_to) and not df.empty:
        from_col = f"From Amount ({convert_from})" if convert_from else "From Amount"
        to_col = f"To Amount ({convert_to})" if convert_to else "To Amount"
        df["Swap Rate"] = df[to_col] / df[from_col].replace(0, pd.NA)

    # Current Rate and Perf. — use converted units when active
    if use_api:
        df["Current Rate"] = df.apply(
            lambda row: (
                calculate_crypto_rate_api(
                    convert_from if convert_from else row["From Token"],
                    convert_to if convert_to else row["To Token"],
                    prices_usd=prices_usd,
                    usd_to_eur=usd_to_eur,
                )
                if (convert_from or row["From Token"])
                != (convert_to or row["To Token"])
                else 1.0
            ),
            axis=1,
        )
    else:
        now_ts = int(pd.Timestamp.now(tz="UTC").timestamp())
        df["Current Rate"] = df.apply(
            lambda row: (
                calculate_crypto_rate(
                    convert_from if convert_from else row["From Token"],
                    convert_to if convert_to else row["To Token"],
                    now_ts,
                    db_file,
                )
                if (convert_from or row["From Token"])
                != (convert_to or row["To Token"])
                else 1.0
            ),
            axis=1,
        )

    # Calculate performance for each swap
    df["Perf."] = ((df["Swap Rate"] * 100) / df["Current Rate"].replace(0, pd.NA)) - 100

    return df


def _draw_swap_table(
    df: pd.DataFrame,
    selection_key: str,
    empty_message: str,
    convert_from: str | None = None,
    convert_to: str | None = None,
):
    if df.empty:
        st.info(empty_message)
    else:
        # Apply styling based on Perf. column values using configurable thresholds
        green_threshold = st.session_state.settings.get(
            "operations_green_threshold", 100
        )
        orange_threshold = st.session_state.settings.get(
            "operations_orange_threshold", 50
        )
        red_threshold = st.session_state.settings.get("operations_red_threshold", 0)

        def color_rows(row):
            if pd.isna(row["Perf."]):
                return [""] * len(row)
            elif row["Perf."] >= green_threshold:
                return ["background-color: #90EE90"] * len(row)  # Light green
            elif row["Perf."] >= orange_threshold:
                return ["background-color: #FFA500"] * len(row)  # Orange
            elif row["Perf."] < red_threshold:
                return ["background-color: #FFB6C1"] * len(row)  # Light red
            else:
                return [""] * len(row)

        # Build dynamic column order and config
        col_from_amount = (
            f"From Amount ({convert_from})" if convert_from else "From Amount"
        )
        col_to_amount = f"To Amount ({convert_to})" if convert_to else "To Amount"

        styled_df = mask_dataframe(df, [col_from_amount, col_to_amount]).style.apply(
            color_rows, axis=1
        )
        rate_col = "Swap Rate"

        column_order = [
            "Date",
            col_from_amount,
            *(() if convert_from else ("From Token",)),
            col_to_amount,
            *(() if convert_to else ("To Token",)),
            "From Wallet",
            "To Wallet",
            rate_col,
            "Current Rate",
            "Perf.",
            "note",
        ]

        column_config = {
            col_from_amount: amount_column(format="%.8g"),
            col_to_amount: amount_column(format="%.8g"),
            rate_col: st.column_config.NumberColumn(format="%.8g"),
            "Current Rate": st.column_config.NumberColumn(format="%.8g"),
            "Perf.": st.column_config.NumberColumn(format="%.2f%%"),
        }

        st.dataframe(
            styled_df,
            width="stretch",
            hide_index=True,
            column_order=column_order,
            column_config=column_config,
            on_select="rerun",
            selection_mode="multi-row",
            key=selection_key,
        )


def draw_swap(
    df: pd.DataFrame, convert_from: str | None = None, convert_to: str | None = None
):
    _draw_swap_table(
        df, "swapselection", "No swap operations", convert_from, convert_to
    )


def draw_swap_arch(
    df: pd.DataFrame, convert_from: str | None = None, convert_to: str | None = None
):
    _draw_swap_table(
        df, "swapachselection", "No archived swaps", convert_from, convert_to
    )


g_wallets = Portfolios(st.session_state.settings["dbfile"]).get_portfolio_names()
g_tokens = TokensDatabase(st.session_state.settings["dbfile"]).get_tokens()

g_operation = Operations(st.session_state.settings["dbfile"])
g_swaps = Swaps(st.session_state.settings["dbfile"])

# Update prices
with st.sidebar:
    if st.button(
        "Update prices",
        key="update_prices",
        icon=":material/update:",
        width="stretch",
    ):
        update()
    # display time since last update
    last_update = Customdata(st.session_state.settings["dbfile"]).get("last_update")
    if last_update:
        last_update_ts = parse_last_update(last_update)
        last_update = pd.Timestamp.now(tz="UTC") - last_update_ts
        st.markdown(
            " - *Last update: " + str(last_update).split(".", maxsplit=1)[0] + "*"
        )
    else:
        st.markdown(" - *No update yet*")

    st.divider()
    use_api = st.toggle(
        "Use API",
        value=False,
        help="Use MarketRaccoon API instead of local SQLite database",
        key="ops_data_source_toggle",
    )
    if use_api:
        st.caption("📡 API MarketRaccoon")
    else:
        st.caption("💾 SQLite local")

buy_tab, swap_tab, airdrop_tab = st.tabs(["Buy", "Swap", "Airdrops"])
with buy_tab:
    # Conversion selectboxes for Buy
    g_convert_options = ["Original", "EUR", "USD"] + g_tokens
    col_conv_from, col_conv_to = st.columns(2)
    with col_conv_from:
        buy_convert_from_sel = st.selectbox(
            "Convert From to:", g_convert_options, key="buy_convert_from"
        )
    with col_conv_to:
        buy_convert_to_sel = st.selectbox(
            "Convert To to:", g_convert_options, key="buy_convert_to"
        )
    buy_cf = None if buy_convert_from_sel == "Original" else buy_convert_from_sel
    buy_ct = None if buy_convert_to_sel == "Original" else buy_convert_to_sel

    # build buy table with performance metrics
    df_buy = build_buy_dataframe(
        convert_from=buy_cf, convert_to=buy_ct, use_api=use_api, db_stamp=_db_stamp()
    )

    col_buylist, col_buybtns = st.columns([8, 1])
    with col_buylist:
        if df_buy.empty:
            st.info("No buy operations")
        else:
            # Build dynamic column order and config
            COL_FROM = f"From ({buy_cf})" if buy_cf else "From"
            COL_TO = f"To ({buy_ct})" if buy_ct else "To"
            RATE_COL = "Converted Rate" if (buy_cf or buy_ct) else "Buy Rate"

            column_order = [
                "Date",
                COL_FROM,
                *(() if buy_cf else ("Currency",)),
                COL_TO,
                *(() if buy_ct else ("Token",)),
                "Portfolio",
                RATE_COL,
                "Current Rate",
                "Perf.",
            ]

            column_config = {
                COL_FROM: amount_column(format="%.8g"),
                COL_TO: amount_column(format="%.8g"),
                RATE_COL: st.column_config.NumberColumn(format="%.8g"),
                "Current Rate": st.column_config.NumberColumn(format="%.8g"),
                "Perf.": st.column_config.NumberColumn(format="%.2f%%"),
            }

            st.dataframe(
                mask_dataframe(df_buy, [COL_FROM, COL_TO]),
                width="stretch",
                height=600,
                hide_index=True,
                column_order=column_order,
                column_config=column_config,
                on_select="rerun",
                selection_mode="single-row",
                key="buyselection",
            )
    with col_buybtns:
        st.button(
            "New",
            on_click=buy_add,
            width="stretch",
            icon=":material/add:",
            key="buy_new",
        )
        st.button(
            "Edit",
            on_click=buy_edit,
            width="stretch",
            icon=":material/edit:",
            key="buy_edit",
        )
        st.button(
            "Delete",
            on_click=buy_delete,
            width="stretch",
            icon=":material/delete:",
            key="buy_delete",
        )

    # aquisition average table
    st.title("Aquisition Averages")
    df_avg = build_buy_avg_table(use_api=use_api, db_stamp=_db_stamp())
    if df_avg.empty:
        st.info("No data available")
    else:
        # Apply styling based on Perf. column values (same logic as icons)
        def color_avg_rows(row):
            if pd.isna(row["Perf."]):
                return [""] * len(row)
            elif row["Perf."] > 0:
                return ["background-color: #90EE90"] * len(row)  # Light green
            elif row["Perf."] < -50:
                return ["background-color: #FFB6C1"] * len(row)  # Light red
            else:
                return ["background-color: #FFFF99"] * len(row)  # Light yellow

        styled_df_avg = mask_dataframe(
            df_avg, ["Total Bought", "Tokens Obtained"]
        ).style.apply(color_avg_rows, axis=1)

        height = (len(df_avg) * 35) + 38
        st.dataframe(
            styled_df_avg,
            width="stretch",
            hide_index=True,
            height=height,
            column_order=(
                "Token",
                "Total Bought",
                "Currency",
                "Tokens Obtained",
                "Avg. Rate",
                "Current Rate",
                "Perf.",
            ),
            column_config={
                "Avg. Rate": st.column_config.NumberColumn(format="%.8f"),
                "Current Rate": st.column_config.NumberColumn(format="%.8f"),
                "Perf.": st.column_config.NumberColumn(format="%.2f%%"),
            },
            key="avgselection",
        )

with swap_tab:
    # Conversion selectboxes for Swap
    col_sconv_from, col_sconv_to = st.columns(2)
    with col_sconv_from:
        swap_convert_from_sel = st.selectbox(
            "Convert From to:", g_convert_options, key="swap_convert_from"
        )
    with col_sconv_to:
        swap_convert_to_sel = st.selectbox(
            "Convert To to:", g_convert_options, key="swap_convert_to"
        )
    swap_cf = None if swap_convert_from_sel == "Original" else swap_convert_from_sel
    swap_ct = None if swap_convert_to_sel == "Original" else swap_convert_to_sel

    # build swap table with performance metrics
    df_swaps_active, df_swaps_archived = build_swap_dataframes(
        st.session_state.settings["dbfile"],
        convert_from=swap_cf,
        convert_to=swap_ct,
        use_api=use_api,
        db_stamp=_db_stamp(),
    )

    col_swaplist, col_swapbtns = st.columns([8, 1])
    with col_swaplist:
        draw_swap(df_swaps_active, convert_from=swap_cf, convert_to=swap_ct)
    with col_swapbtns:
        st.button(
            "New",
            on_click=swap_add,
            width="stretch",
            icon=":material/add:",
            key="swap_new",
        )
        st.button(
            "Edit",
            on_click=swap_edit,
            args=(df_swaps_active,),
            width="stretch",
            icon=":material/edit:",
            key="swap_edit",
        )
        st.button(
            "Archive",
            on_click=swap_archive,
            args=(df_swaps_active,),
            width="stretch",
            icon=":material/archive:",
            key="swap_archive",
        )
        st.button(
            "Delete",
            on_click=swap_delete,
            args=(df_swaps_active,),
            width="stretch",
            icon=":material/delete:",
            key="swap_delete",
        )

    st.title("Archived Swaps")
    col_archlist, col_archbtns = st.columns([8, 1])
    with col_archlist:
        draw_swap_arch(df_swaps_archived, convert_from=swap_cf, convert_to=swap_ct)
    with col_archbtns:
        st.button(
            "Unarchive",
            on_click=swap_unarchive,
            args=(df_swaps_archived,),
            width="stretch",
            icon=":material/unarchive:",
            key="swap_unarchive",
        )
        st.button(
            "Delete",
            on_click=swap_arch_delete,
            args=(df_swaps_archived,),
            width="stretch",
            icon=":material/delete:",
            key="swap_arch_delete",
        )

with airdrop_tab:
    airdrop_currency = st.session_state.settings.get("fiat_currency", "EUR")
    df_airdrop_all = build_airdrop_dataframe(
        airdrop_currency, use_api=use_api, db_stamp=_db_stamp()
    )
    # df_airdrop = displayed rows: airdrop_edit() maps the selected row to it
    df_airdrop = df_airdrop_all

    if not df_airdrop_all.empty:
        airdrop_token_options = sorted(df_airdrop_all["Token"].dropna().unique())
        # Drop filtered tokens that no longer have an airdrop (edit/delete)
        st.session_state["airdrop_token_filter"] = [
            t
            for t in st.session_state.get("airdrop_token_filter", [])
            if t in airdrop_token_options
        ]
        airdrop_token_filter = st.multiselect(
            "Filter tokens",
            airdrop_token_options,
            key="airdrop_token_filter",
            placeholder="All tokens",
        )
        if airdrop_token_filter:
            df_airdrop = df_airdrop_all[
                df_airdrop_all["Token"].isin(airdrop_token_filter)
            ].reset_index(drop=True)

    col_airdroplist, col_airdropbtns = st.columns([8, 1])
    with col_airdroplist:
        if df_airdrop_all.empty:
            st.info("No airdrops")
        else:
            st.dataframe(
                mask_dataframe(df_airdrop, ["Amount", "Value"]),
                width="stretch",
                height=600,
                hide_index=True,
                column_order=["Date", "Amount", "Token", "Value", "Portfolio"],
                column_config={
                    "Amount": amount_column(format="%.8g"),
                    "Value": amount_column(
                        f"Value ({airdrop_currency})", format="%.2f"
                    ),
                },
                on_select="rerun",
                selection_mode="single-row",
                key="airdropselection",
            )
    with col_airdropbtns:
        st.button(
            "New",
            on_click=airdrop_add,
            width="stretch",
            icon=":material/add:",
            key="airdrop_new",
        )
        st.button(
            "Edit",
            on_click=airdrop_edit,
            width="stretch",
            icon=":material/edit:",
            key="airdrop_edit",
        )
