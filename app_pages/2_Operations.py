import streamlit as st
from modules.database.portfolios import Portfolios
from modules.database.historybase import HistoryBase

st.title("Operations")

g_portfolios = Portfolios(st.session_state.dbfile)
g_historybase = HistoryBase(st.session_state.dbfile)

buysell_tab, swap_tab = st.tabs(["Buy/Sell", "Swap"])
with buysell_tab:
    with st.form(key="buysell"):
        st.date_input("Date", key="buysell_date")
        col_buy, col_sell = st.columns(2)
        with col_buy:
            col_buy_amount, col_buy_token = st.columns([3, 1])
            with col_buy_amount:
                st.number_input(
                    "Amount", min_value=0.0, format="%.8f", key="buy_amount"
                )
            with col_buy_token:
                st.selectbox("", ["EUR", "USD"], key="buy_token")
        with col_sell:
            col_buy_amount, col_buy_token = st.columns([3, 1])
            with col_buy_amount:
                st.number_input(
                    "Amount", min_value=0.0, format="%.8f", key="sell_amount"
                )
            with col_buy_token:
                st.selectbox("", g_historybase.getTokens(), index=None, key="sell_token")
            st.selectbox(
                "Portfolio",
                g_portfolios.get_portfolio_names(),
                key="sell_wallet",
                index=None
            )
        st.form_submit_button("Submit", use_container_width=True)

with swap_tab:
    with st.form(key="swap"):
        st.date_input("Date", key="swap_date")
        col_from, col_to = st.columns(2)
        with col_from:
            st.text_input("Token", key="swap_token_from")
            st.number_input(
                "Amount", min_value=0.0, format="%.8f", key="swap_amount_from"
            )
            st.selectbox("Wallet", ["Wallet 1", "Wallet 2"], key="swap_wallet_from")
        with col_to:
            st.text_input("Token", key="swap_token_to")
            st.number_input(
                "Amount", min_value=0.0, format="%.8f", key="swap_amount_to"
            )
            st.selectbox("Wallet", ["Wallet 1", "Wallet 2"], key="swap_wallet_to")
        st.form_submit_button("Submit", use_container_width=True)
