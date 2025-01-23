import logging
import streamlit as st
import pandas as pd
import tzlocal
from modules.database.portfolios import Portfolios
from modules.database.tokensdb import TokensDatabase
from modules.database.operations import operations
from modules.database.market import Market
from modules.database.swaps import swaps
from modules.utils import toTimestamp_A

logger = logging.getLogger(__name__)

st.title("Operations")


def submitbuy(timestamp, from_amount, form_currency, to_amount, to_token, to_wallet):
    logger.debug(
        f"submitbuy: timestamp={timestamp} from_amount={from_amount}, form_currency={form_currency}, to_amount={to_amount}, to_token={to_token}, to_wallet={to_wallet}"
    )

    g_operation.insert(
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


def swapRowSelected():
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


def buyRowSelected():
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
def buyAdd():
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
        submitbuy(timestamp, from_amount, form_currency, to_amount, to_token, to_wallet)
        st.rerun()


@st.dialog("Add Swap")
def swapAdd():
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
        swap_amount_to = st.number_input(
            "From Amount", min_value=0.0, format="%.8g", key="swap_amount_to"
        )
        swap_amount_from = st.number_input(
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
        submitswap(
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
def buyEditDialog(rowidx: int):
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
            "From", min_value=0.0, format="%.8g", key="from_amount", value=float(data["From"])
        )
        to_amount = st.number_input("To", min_value=0.0, format="%.8g", key="to_amount", value=float(data["To"])
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
        submitbuy(timestamp, from_amount, form_currency, to_amount, to_token, to_wallet)
        st.rerun()
    

@st.dialog("Edit Swap")
def swapEditDialog(rowidx: int):
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
        swap_amount_to = st.number_input(
            "From Amount",
            min_value=0.0,
            format="%.8g",
            key="swap_amount_to",
            value=float(data["From Amount"]),
        )
        swap_amount_from = st.number_input(
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
        submitswap(
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
def buyDeleteDialog(rowidx: int):
    logger.debug("Dialog Delete row: %s", rowidx)
    data = st.session_state.buylist.iloc[rowidx].to_dict()
    st.dataframe(data, use_container_width=True)
    st.write("Are you sure you want to delete this buy operation?")
    if st.button("Confirm"):
        logger.debug(f"Delete row: {data} - {type(data['id'])}")
        g_operation.delete(data["id"])
        st.rerun()

@st.dialog("Delete Swap")
def swapDeleteDialog(rowidx: int):
    logger.debug("Dialog Delete row: %s", rowidx)
    data = st.session_state.swaplist.iloc[rowidx].to_dict()
    st.dataframe(data, use_container_width=True)
    st.write("Are you sure you want to delete this swap?")
    if st.button("Confirm"):
        logger.debug(f"Delete row: {data} - {type(data['id'])}")
        g_swaps.delete(data["id"])
        st.rerun()


def buyEdit():
    rowidx = buyRowSelected()
    if rowidx is None:
        st.toast("Please select a row", icon=":material/warning:")
    else:
        buyEditDialog(rowidx)


def swapEdit():
    rowidx = swapRowSelected()
    if rowidx is None:
        st.toast("Please select a row", icon=":material/warning:")
    else:
        swapEditDialog(rowidx)


def buyDelete():
    logger.debug("Delete row")
    rowidx = buyRowSelected()
    if rowidx is None:
        st.toast("Please select a row", icon=":material/warning:")
    else:
        buyDeleteDialog(rowidx)
    pass


def swapDelete():
    logger.debug("Delete row")
    rowidx = swapRowSelected()
    if rowidx is None:
        st.toast("Please select a row", icon=":material/warning:")
    else:
        swapDeleteDialog(rowidx)


g_portfolios = Portfolios(st.session_state.dbfile)
g_historybase = TokensDatabase(st.session_state.dbfile)
g_tokens = g_historybase.getTokens()
g_wallets = g_portfolios.get_portfolio_names()
g_operation = operations()
g_swaps = swaps()

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
    # convert timestamp to datetime
    st.session_state.buylist["Date"] = pd.to_datetime(
        st.session_state.buylist["timestamp"], unit="s", utc=True
    )
    local_timezone = tzlocal.get_localzone()
    logger.debug("Timezone locale: %s", local_timezone)
    st.session_state.buylist["Date"] = st.session_state.buylist["Date"].dt.tz_convert(
        local_timezone
    )

    # calculate performance
    market = Market(
        st.session_state.dbfile, st.session_state.settings["coinmarketcap_token"]
    )
    market_df = market.getLastMarket()

    st.session_state.buylist["Buy Rate"] = (
        st.session_state.buylist["From"] / st.session_state.buylist["To"]
    )
    st.session_state.buylist["Current Rate"] = st.session_state.buylist["Token"].map(
        market_df["value"].to_dict()
    )
    st.session_state.buylist["Perf."] = (
        st.session_state.buylist["Current Rate"] * 100
    ) / st.session_state.buylist["Buy Rate"] - 100

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
            on_click=buyAdd,
            use_container_width=True,
            icon=":material/add:",
            key="buy_new",
        )
        st.button(
            "Edit",
            on_click=buyEdit,
            use_container_width=True,
            icon=":material/edit:",
            key="buy_edit",
        )
        st.button(
            "Delete",
            on_click=buyDelete,
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
    # convert timestamp to datetime
    st.session_state.swaplist["Date"] = pd.to_datetime(
        st.session_state.swaplist["timestamp"], unit="s", utc=True
    )
    local_timezone = tzlocal.get_localzone()
    logger.debug("Timezone locale: %s", {local_timezone})
    st.session_state.swaplist["Date"] = st.session_state.swaplist["Date"].dt.tz_convert(
        local_timezone
    )

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
            ),
            column_config={
                "From Amount": st.column_config.NumberColumn(format="%.8g"),
                "To Amount": st.column_config.NumberColumn(format="%.8g"),
            },
            on_select="rerun",
            selection_mode="single-row",
            key="swapselection",
        )
    with col_swapbtns:
        st.button(
            "New",
            on_click=swapAdd,
            use_container_width=True,
            icon=":material/add:",
            key="swap_new",
        )
        st.button(
            "Edit",
            on_click=swapEdit,
            use_container_width=True,
            icon=":material/edit:",
            key="swap_edit",
        )
        st.button(
            "Delete",
            on_click=swapDelete,
            use_container_width=True,
            icon=":material/delete:",
            key="swap_delete",
        )

st.write(st.session_state)
