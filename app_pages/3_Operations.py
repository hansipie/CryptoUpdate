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
from modules.database.operations import Operations
from modules.database.market import Market
from modules.database.swaps import Swaps
from modules.tools import (
    batch_convert_historical,
    batch_convert_historical_api,
    calculate_crypto_rate,
    calculate_crypto_rate_api,
    calc_perf_api,
    update,
    parse_last_update,
    _get_api_latest_prices,
    _get_api_fiat_rate,
)
from modules.utils import get_file_hash, to_timestamp_a as toTimestamp_A

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
    note: str = None,
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
    )


def rows_selected(selectable) -> list:
    """Get the selected row index in the swap table"""
    logger.debug("Row selection: %s", selectable)
    if (
        "selection" in selectable
        and "rows" in selectable["selection"]
        and len(selectable["selection"]["rows"]) > 0
    ):
        selected_row = selectable["selection"]["rows"]
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
    if st.button("Submit", width="stretch"):
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
    COL_TOken, col_amount, col_portfolio = st.columns(3)
    with COL_TOken:
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
    swap_note = st.text_area("Note", key="swap_note", value="")
    if st.button("Submit", width="stretch"):
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
    if st.button("Submit", width="stretch"):
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
    COL_TOken, col_amount, col_portfolio = st.columns(3)
    with COL_TOken:
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
    swap_note = st.text_area("Note", key="swap_note", value=data.get("note") or "")
    if st.button("Submit", width="stretch"):
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
            note=swap_note,
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
    st.dataframe(data, width="stretch")
    st.write("Are you sure you want to delete this buy operation?")
    if st.button("Confirm"):
        logger.debug("Delete row: %s - %s", data, type(data["id"]))
        g_operation.delete(data["id"])
        st.rerun()


@st.dialog("Delete Swap")
def swap_delete_dialog(rows: list):
    """Display confirmation dialog for deleting a swap operation.

    Args:
        data: Dictionary containing the swap operation data to delete

    Shows a confirmation prompt with operation details.
    On confirm, deletes the operation.
    """
    todelete = []
    for rowidx in rows:
        data = df_swap.iloc[rowidx].to_dict()
        todelete.append(data)

    logger.debug("Dialog Delete row: %s", todelete)
    st.write(f"{len(todelete)} swap(s) selected. Are you sure you want to delete?")

    if st.button("Confirm"):
        for data in todelete:
            logger.debug("Delete row: %s - %s", data, type(data["id"]))
            g_swaps.delete(data["id"])
        st.rerun()


@st.dialog("Archive Swap")
def swap_archive_dialog(rows: list):
    """Display confirmation dialog for archiving a swap operation.

    Args:
        data: Dictionary containing the swap operation data to archive

    Shows a confirmation prompt with operation details.
    On confirm, archives the operation.
    """
    toarchive = []
    for rowidx in rows:
        data = df_swap.iloc[rowidx].to_dict()
        toarchive.append(data)

    logger.debug("Dialog Archive row: %s", toarchive)
    st.write(f"{len(toarchive)} swap(s) selected. Are you sure you want to archive?")

    if st.button("Confirm"):
        for data in toarchive:
            logger.debug("Archive row: %s - %s", data, type(data["id"]))
            g_swaps.update_tag(data["id"], "archived")
        st.rerun()


@st.dialog("Unarchive Swap")
def swap_unarchive_dialog(rows: list):
    """Display confirmation dialog for unarchiving a swap operation.

    Args:
        data: Dictionary containing the swap operation data to unarchive

    Shows a confirmation prompt with operation details.
    On confirm, unarchives the operation.
    """
    tounarchive = []
    for rowidx in rows:
        data = df_swap_arch.iloc[rowidx].to_dict()
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
def swap_arch_delete_dialog(rows: list):
    """Display confirmation dialog for deleting an archived swap operation.

    Args:
        rows: List of row indices to delete

    Shows a confirmation prompt with operation details.
    On confirm, deletes the archived operations.
    """
    todelete = []
    for rowidx in rows:
        data = df_swap_arch.iloc[rowidx].to_dict()
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
    rowidx = rows_selected(st.session_state.buyselection)[0]
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
    rowidx = rows_selected(st.session_state.buyselection)[0]
    if rowidx is None:
        st.toast("Please select a row", icon=":material/warning:")
    else:
        buy_delete_dialog(df_buy.iloc[rowidx].to_dict())


def swap_edit():
    """Handle editing of selected swap operation.

    Shows edit dialog if a row is selected.
    Otherwise displays a warning toast.
    """
    rowidx = rows_selected(st.session_state.swapselection)
    if len(rowidx) > 1:
        st.toast("Please select only one row", icon=":material/warning:")
    else:
        if rowidx[0] is None:
            st.toast("Please select a row", icon=":material/warning:")
        else:
            swap_edit_dialog(df_swap.iloc[rowidx[0]].to_dict())


def swap_delete():
    """Handle deletion of selected swap operation.

    Shows confirmation dialog if a row is selected.
    Otherwise displays a warning toast.
    """
    logger.debug("Delete row")
    rowidx = rows_selected(st.session_state.swapselection)
    if rowidx is None:
        st.toast("Please select a row", icon=":material/warning:")
    else:
        swap_delete_dialog(rowidx)


def swap_archive():
    """Handle archiving of selected swap operation.

    Shows confirmation dialog if a row is selected.
    Otherwise displays a warning toast.
    """
    logger.debug("Archive row")
    rowidx = rows_selected(st.session_state.swapselection)
    if rowidx is None:
        st.toast("Please select a row", icon=":material/warning:")
    else:
        swap_archive_dialog(rowidx)


def swap_unarchive():
    """Handle unarchiving of selected swap operation.

    Shows confirmation dialog if a row is selected.
    Otherwise displays a warning toast.
    """
    logger.debug("Unarchive row")
    rowidx = rows_selected(st.session_state.swapachselection)
    if rowidx is None:
        st.toast("Please select a row", icon=":material/warning:")
    else:
        swap_unarchive_dialog(rowidx)


def swap_arch_delete():
    """Handle deletion of selected archived swap operation.

    Shows confirmation dialog if a row is selected.
    Otherwise displays a warning toast.
    """
    logger.debug("Delete archived row")
    rowidx = rows_selected(st.session_state.swapachselection)
    if rowidx is None:
        st.toast("Please select a row", icon=":material/warning:")
    else:
        swap_arch_delete_dialog(rowidx)


def calc_perf(df: pd.DataFrame, COL_TOken: str, col_rate: str) -> pd.DataFrame:
    """Calculate current performance metrics for operations.

    Args:
        df: DataFrame containing operations data
        COL_TOken: Name of column containing token symbols
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
        df["Current Rate"] = df[COL_TOken].map(market_df["value"].to_dict())
        df["Perf."] = ((df["Current Rate"] * 100) / df[col_rate]) - 100
    return df


def swap_perf(rate_swap, rate_now) -> float:
    if rate_swap is None or rate_now is None:
        return None
    return ((rate_swap * 100) / rate_now) - 100


def build_buy_dataframe(
    convert_from: str = None, convert_to: str = None, use_api: bool = False
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

    # convert timestamp to datetime
    df["Date"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    local_timezone = tzlocal.get_localzone()
    logger.debug("Timezone locale: %s", local_timezone)
    df["Date"] = df["Date"].dt.tz_convert(local_timezone).dt.tz_localize(None)
    df["Buy Rate"] = df["From"] / df["To"]

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
        df["Converted Rate"] = df[from_col] / df[to_col]

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
        df["Perf."] = ((df["Current Rate"] * 100) / df["Converted Rate"]) - 100
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


def build_buy_avg_table(use_api: bool = False):
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

    df["Avg. Rate"] = df["Total Bought"] / df["Tokens Obtained"]
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


@st.cache_data(
    hash_funcs={str: lambda x: get_file_hash(x) if os.path.isfile(x) else hash(x)},
)
def build_swap_dataframes(
    db_file: str,
    convert_from: str = None,
    convert_to: str = None,
    use_api: bool = False,
) -> pd.DataFrame:
    df1 = pd.DataFrame(
        g_swaps.get_by_tag(""),
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
            "note",
        ],
    )
    if not df1.empty:
        df1 = build_swap_dataframe(df1, convert_from, convert_to, use_api)
    else:
        st.info("No swap operations")

    df2 = pd.DataFrame(
        g_swaps.get_by_tag("archived"),
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
            "note",
        ],
    )
    if not df2.empty:
        df2 = build_swap_dataframe(df2, convert_from, convert_to, use_api)
    else:
        st.info("No archived swaps")

    return df1, df2


@st.cache_data()
def build_swap_dataframe(
    df: pd.DataFrame,
    convert_from: str = None,
    convert_to: str = None,
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

    df["Swap Rate"] = df["To Amount"] / df["From Amount"]

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
                st.session_state.settings["dbfile"],
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
                st.session_state.settings["dbfile"],
            )

    # Recalculate Swap Rate if conversions are active
    if (convert_from or convert_to) and not df.empty:
        from_col = f"From Amount ({convert_from})" if convert_from else "From Amount"
        to_col = f"To Amount ({convert_to})" if convert_to else "To Amount"
        df["Swap Rate"] = df[to_col] / df[from_col]

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
        dbfile = st.session_state.settings["dbfile"]
        df["Current Rate"] = df.apply(
            lambda row: (
                calculate_crypto_rate(
                    convert_from if convert_from else row["From Token"],
                    convert_to if convert_to else row["To Token"],
                    now_ts,
                    dbfile,
                )
                if (convert_from or row["From Token"])
                != (convert_to or row["To Token"])
                else 1.0
            ),
            axis=1,
        )

    # Calculate performance for each swap
    df["Perf."] = swap_perf(df["Swap Rate"], df["Current Rate"])

    return df


def draw_swap(df: pd.DataFrame, convert_from: str = None, convert_to: str = None):
    if df.empty:
        st.info("No swap operations")
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

        styled_df = df.style.apply(color_rows, axis=1)

        # Build dynamic column order and config
        COL_FROM_amount = (
            f"From Amount ({convert_from})" if convert_from else "From Amount"
        )
        COL_TO_amount = f"To Amount ({convert_to})" if convert_to else "To Amount"
        RATE_COL = "Swap Rate"

        column_order = [
            "Date",
            COL_FROM_amount,
            *(() if convert_from else ("From Token",)),
            COL_TO_amount,
            *(() if convert_to else ("To Token",)),
            "From Wallet",
            "To Wallet",
            RATE_COL,
            "Current Rate",
            "Perf.",
            "note",
        ]

        column_config = {
            COL_FROM_amount: st.column_config.NumberColumn(format="%.8g"),
            COL_TO_amount: st.column_config.NumberColumn(format="%.8g"),
            RATE_COL: st.column_config.NumberColumn(format="%.8g"),
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
            key="swapselection",
        )


def draw_swap_arch(df: pd.DataFrame, convert_from: str = None, convert_to: str = None):
    if df.empty:
        st.info("No archived swaps")
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

        styled_df = df.style.apply(color_rows, axis=1)

        # Build dynamic column order and config
        COL_FROM_amount = (
            f"From Amount ({convert_from})" if convert_from else "From Amount"
        )
        COL_TO_amount = f"To Amount ({convert_to})" if convert_to else "To Amount"
        RATE_COL = "Swap Rate"

        column_order = [
            "Date",
            COL_FROM_amount,
            *(() if convert_from else ("From Token",)),
            COL_TO_amount,
            *(() if convert_to else ("To Token",)),
            "From Wallet",
            "To Wallet",
            RATE_COL,
            "Current Rate",
            "Perf.",
            "note",
        ]

        column_config = {
            COL_FROM_amount: st.column_config.NumberColumn(format="%.8g"),
            COL_TO_amount: st.column_config.NumberColumn(format="%.8g"),
            RATE_COL: st.column_config.NumberColumn(format="%.8g"),
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
            key="swapachselection",
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

buy_tab, swap_tab = st.tabs(["Buy", "Swap"])
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
        convert_from=buy_cf, convert_to=buy_ct, use_api=use_api
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
                COL_FROM: st.column_config.NumberColumn(format="%.8g"),
                COL_TO: st.column_config.NumberColumn(format="%.8g"),
                RATE_COL: st.column_config.NumberColumn(format="%.8g"),
                "Current Rate": st.column_config.NumberColumn(format="%.8g"),
                "Perf.": st.column_config.NumberColumn(format="%.2f%%"),
            }

            st.dataframe(
                df_buy,
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
    df_avg = build_buy_avg_table(use_api=use_api)
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

        styled_df_avg = df_avg.style.apply(color_avg_rows, axis=1)

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
    df_swap, df_swap_arch = build_swap_dataframes(
        st.session_state.settings["dbfile"],
        convert_from=swap_cf,
        convert_to=swap_ct,
        use_api=use_api,
    )

    col_swaplist, col_swapbtns = st.columns([8, 1])
    with col_swaplist:
        draw_swap(df_swap, convert_from=swap_cf, convert_to=swap_ct)
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
            width="stretch",
            icon=":material/edit:",
            key="swap_edit",
        )
        st.button(
            "Archive",
            on_click=swap_archive,
            width="stretch",
            icon=":material/archive:",
            key="swap_archive",
        )
        st.button(
            "Delete",
            on_click=swap_delete,
            width="stretch",
            icon=":material/delete:",
            key="swap_delete",
        )

    st.title("Archived Swaps")
    col_archlist, col_archbtns = st.columns([8, 1])
    with col_archlist:
        draw_swap_arch(df_swap_arch, convert_from=swap_cf, convert_to=swap_ct)
    with col_archbtns:
        st.button(
            "Unarchive",
            on_click=swap_unarchive,
            width="stretch",
            icon=":material/unarchive:",
            key="swap_unarchive",
        )
        st.button(
            "Delete",
            on_click=swap_arch_delete,
            width="stretch",
            icon=":material/delete:",
            key="swap_arch_delete",
        )
