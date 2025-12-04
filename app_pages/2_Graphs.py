import logging

import pandas as pd
import streamlit as st

from modules.database.apimarket import ApiMarket
from modules.database.market import Market
from modules.database.portfolios import Portfolios
from modules.database.tokensdb import TokensDatabase
from modules.plotter import plot_as_graph, plot_as_pie
from modules.tools import create_portfolio_dataframe, interpolate_price
from modules.utils import toTimestamp_A, toTimestamp_B

logger = logging.getLogger(__name__)


def load_portfolios(dbfile: str) -> Portfolios:
    """Load portfolios from database file.

    Args:
        dbfile: Path to database file

    Returns:
        Portfolios instance initialized with the database
    """
    return Portfolios(dbfile)


def aggregater_ui():
    """Display aggregate view of all portfolios.

    Shows a table of token totals across all portfolios and
    a pie chart showing portfolio value distribution.
    """
    portfolios = load_portfolios(st.session_state.settings["dbfile"])
    agg = portfolios.aggregate_portfolios()
    logger.debug("Aggregated: %s", agg)
    df = create_portfolio_dataframe(agg)

    # Get target currency from settings
    target_currency = st.session_state.settings.get("fiat_currency", "EUR")
    value_column = f"value({target_currency})"

    col_tbl, col_pie = st.columns(2)
    with col_tbl:
        st.header("Tokens")
        if not df.empty:
            height = (len(df) * 35) + 38
            height = min(height, 650)

            df = df.groupby("token").agg({"amount": "sum", value_column: "sum"})
            df["Repartition(%)"] = (df[value_column] / df[value_column].sum()) * 100
            df = df.rename(columns={"amount": "Amount", value_column: f"Value({target_currency})"})
            df = df.sort_values(by="Repartition(%)", ascending=False)
            st.dataframe(df, width='stretch', height=height)

            # Display total with appropriate currency symbol
            currency_symbols = {
                "EUR": "€", "USD": "$", "GBP": "£", "CHF": "CHF",
                "CAD": "CA$", "AUD": "A$", "JPY": "¥", "CNY": "¥",
                "KRW": "₩", "BRL": "R$", "MXN": "MX$", "INR": "₹",
                "RUB": "₽", "TRY": "₺"
            }
            currency_symbol = currency_symbols.get(target_currency, target_currency)
            st.write(f"Total value: {currency_symbol}" + str(round(df[f"Value({target_currency})"].sum(), 2)))
        else:
            st.info("No data available")
    with col_pie:
        st.header("Tokens repartition")
        if not df.empty:
            try:
                plot_as_pie(df, column=f"Value({target_currency})")
            except Exception as e:
                st.error(f"Error: {str(e)}")
        else:
            st.info("No data available")


def draw_tab_content(
    section: str, token: str, start_timestamp: int, end_timestamp: int
):
    logger.debug("Draw tab content for token %s", token)
    if section == "Assets Balances":
        with st.spinner("Loading assets balances...", show_time=True):
            df_view = tokensdb.get_token_balances(token, start_timestamp, end_timestamp)
    elif section == "Market":
        with st.spinner("Loading market...", show_time=True):
            df_view = markgetdb.get_token_market(token, start_timestamp, end_timestamp)
    else:
        df_view = None
    if df_view is not None:
        if section == "Assets Balances":
            column_value = "Value"
            label = "Balance"
        else:
            column_value = "Price"
            label = "Current Price"
        mcol1, mcol2, mcol3, mcol4 = st.columns(4)
        with mcol1:
            nbr_days = df_view.index[-1] - df_view.index[0]
            st.metric(
                "Days",
                value=nbr_days.days,
                help=f"From {df_view.index[0]} to {df_view.index[-1]}",
            )
        with mcol2:
            first = df_view.iloc[0].values[0]
            last = df_view.iloc[-1].values[0]
            current_price = df_view[column_value].iloc[-1]
            st.metric(
                label,
                value=f"{round(current_price, 2)} €",
                delta=(
                    f"{round(((last - first) / first) * 100, 2)} %"
                    if first != 0
                    else "0 %"
                    if last == 0
                    else "∞ %"
                ),
            )
        with mcol3:
            min_price = df_view[column_value].min()
            min_price_date = df_view.index[
                df_view[column_value] == df_view[column_value].min()
            ]
            st.metric(
                "Timeframe Low",
                value=f"{round(min_price, 2)} €",
                help=f"Date: {min_price_date[0]}",
                delta=f"{round(((current_price - min_price) / min_price) * 100, 2)} %",
            )
        with mcol4:
            max_price = df_view[column_value].max()
            max_price_date = df_view.index[
                df_view[column_value] == df_view[column_value].max()
            ]
            st.metric(
                "Timeframe High",
                value=f"{round(max_price, 2)} €",
                help=f"Date: {max_price_date[0]}",
                delta=f"{round(((current_price - max_price) / max_price) * 100, 2)} %",
            )

        col1, col2 = st.columns([3, 1])
        with col1:
            plot_as_graph(df_view)
        with col2:
            col2.dataframe(df_view, width='stretch')

    else:
        st.info("No data available")


def build_tabs(section: str = "Assets Balances"):
    start_timestamp = toTimestamp_A(
        st.session_state.startdate, pd.to_datetime("00:00:00").time()
    )
    end_timestamp = toTimestamp_A(
        st.session_state.enddate, pd.to_datetime("23:59:59").time()
    )
    if section == "Assets Balances":
        available_tokens = tokensdb.get_tokens()
    elif section == "Market":
        available_tokens = markgetdb.getTokens()
    else:
        available_tokens = []
    if not available_tokens:
        st.info("No data available")
        return
    temp_tokens = st.multiselect(
        "Select Tokens to display",
        available_tokens,
        default=st.session_state.tokens,
    )
    if temp_tokens != st.session_state.tokens:
        st.session_state.tokens = temp_tokens
        logger.debug("Tokens list changed")
        st.rerun()
    else:
        logger.debug("Tokens list not changed")

    if st.session_state.tokens:
        tabs = st.tabs(st.session_state.tokens)
        idx_token = 0
        for tab in tabs:
            with tab:
                draw_tab_content(
                    section,
                    st.session_state.tokens[idx_token],
                    start_timestamp,
                    end_timestamp,
                )
            idx_token += 1


def build_price_tab(df: pd.DataFrame):
    logger.debug("Build tabs")
    if df is None or df.empty:
        st.info("No data available")
        return
    if st.session_state.startdate < st.session_state.enddate:
        df_view = df.loc[df.index > str(st.session_state.startdate)]
        df_view = df_view.loc[
            df_view.index < str(st.session_state.enddate + pd.to_timedelta(1, unit="d"))
        ]
        df_view = df_view.loc[:, ["price"]]
        df_view = df_view.dropna()

        mcol1, mcol2 = st.columns(2)
        with mcol1:
            nbr_days = st.session_state.enddate - st.session_state.startdate
            mcol1.metric("Days", value=nbr_days.days)
        with mcol2:
            first = df_view.iloc[0].values[0]
            last = df_view.iloc[-1].values[0]
            logger.debug("first: %s, last: %s", first, last)
            mcol2.metric(
                "Performance",
                value=(
                    f"{round(((last - first) / first) * 100, 2)} %"
                    if first != 0
                    else "0 %"
                    if last == 0
                    else "∞ %"
                ),
            )
        col1, col2 = st.columns([3, 1])
        with col1:
            plot_as_graph(df_view)
        with col2:
            col2.dataframe(df_view, width='stretch')

    else:
        st.error("The end date must be after the start date")


with st.sidebar:
    add_selectbox = st.selectbox(
        "Assets View",
        ("Global", "Assets Balances", "Market", "Currency (USDEUR)"),
    )

    if add_selectbox != "Global":
        st.divider()
        st.session_state.enddate = pd.to_datetime("today")
        selected_timeframe = st.selectbox(
            "Timeframe", ["1D", "1W", "1M", "3M", "6M", "1Y", "All"], index=6
        )
        if "1D" == selected_timeframe:
            st.session_state.startdate = st.session_state.enddate - pd.to_timedelta(
                1, unit="d"
            )
        elif "1W" == selected_timeframe:
            st.session_state.startdate = st.session_state.enddate - pd.to_timedelta(
                7, unit="d"
            )
        elif "1M" == selected_timeframe:
            st.session_state.startdate = st.session_state.enddate - pd.to_timedelta(
                30, unit="d"
            )
        elif "3M" == selected_timeframe:
            st.session_state.startdate = st.session_state.enddate - pd.to_timedelta(
                90, unit="d"
            )
        elif "6M" == selected_timeframe:
            st.session_state.startdate = st.session_state.enddate - pd.to_timedelta(
                180, unit="d"
            )
        elif "1Y" == selected_timeframe:
            st.session_state.startdate = st.session_state.enddate - pd.to_timedelta(
                365, unit="d"
            )
        else:  # "All" == selected_timeframe:
            st.session_state.startdate = pd.to_datetime("1900-01-01")

tokensdb = TokensDatabase(st.session_state.settings["dbfile"])
markgetdb = Market(
    st.session_state.settings["dbfile"],
    st.session_state.settings["coinmarketcap_token"],
)

if "tokens" not in st.session_state:
    st.session_state.tokens = []

if add_selectbox == "Global":
    logger.debug("Global")
    st.title("Global")
    aggregater_ui()

if add_selectbox == "Assets Balances":
    logger.debug("Assets Balances")
    st.title("Assets Balances")
    build_tabs()

if add_selectbox == "Market":
    logger.debug("Market")
    st.title("Market")
    build_tabs("Market")

if add_selectbox == "Currency (USDEUR)":
    logger.debug("Currency (USDEUR)")
    st.title("Currency (USDEUR)")
    market = ApiMarket(st.session_state.settings["marketraccoon_url"])

    # Cache currency data to avoid re-fetching on form submission
    if "currency_data" not in st.session_state:
        st.session_state.currency_data = market.get_currency()

    build_price_tab(st.session_state.currency_data)

    # Initialize session state for interpolation results
    if "interpolation_result" not in st.session_state:
        st.session_state.interpolation_result = None

    with st.form(key="interpolate"):
        col_date, col_time, col_btn = st.columns([3, 2, 1], vertical_alignment="bottom")
        with col_date:
            date = st.date_input("Date", key="interdate")
        with col_time:
            time = st.time_input("Time", key="intertime")
        with col_btn:
            submitted = st.form_submit_button("Submit", width='stretch')

        if submitted:
            timestamp = toTimestamp_B(date, time, utc=False)
            df_result = market.get_currency(timestamp=timestamp)

            if df_result is not None and not df_result.empty:
                value = df_result["price"].iloc[0]
                is_interpolated = df_result.get("interpolated", pd.Series([False])).iloc[0]
                st.session_state.interpolation_result = {
                    "value": value,
                    "is_interpolated": is_interpolated
                }
            else:
                st.session_state.interpolation_result = None

    # Display interpolation results
    if st.session_state.interpolation_result is not None:
        result = st.session_state.interpolation_result
        value = result["value"]
        is_interpolated = result["is_interpolated"]

        if value != 0.0:
            if is_interpolated:
                st.info(f"Interpolated value: {value:.6f} EUR")
            else:
                st.info(f"Exact value: {value:.6f} EUR")
        else:
            st.warning("Value is 0.0")
    elif st.session_state.interpolation_result is None and "interpolation_result" in st.session_state:
        st.info("No data available")
