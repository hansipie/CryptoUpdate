import logging
import os

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from modules.configuration import Configuration
from modules.database.apimarket import ApiMarket
from modules.database.market import Market
from modules.database.portfolios import Portfolios
from modules.database.tokensdb import TokensDatabase
from modules.plotter import plot_as_pie
from modules.tools import (
    create_portfolio_dataframe,
    get_currency_symbol,
    convert_dataframe_prices_historical,
)
from modules.utils import to_timestamp_a as toTimestamp_A, to_timestamp_b as toTimestamp_B

logger = logging.getLogger(__name__)


# Cached API wrappers for instant toggle responses
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_api_coins(
    api_url: str, api_key: str, cache_file: str, symbols: tuple = None
) -> pd.DataFrame:
    """Fetch coins from API with Streamlit session cache.

    Args:
        api_url: MarketRaccoon API URL
        api_key: MarketRaccoon API key
        cache_file: Path to JSON cache file
        symbols: Optional tuple of symbols to filter (tuple for hashability)

    Returns:
        DataFrame with coin information or None if empty
    """
    api = ApiMarket(api_url, api_key=api_key, cache_file=cache_file)
    symbols_list = list(symbols) if symbols else None
    return api.get_coins_cached(symbols_list)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_api_crypto_market(
    api_url: str,
    api_key: str,
    cache_file: str,
    token_symbol: str,
    from_ts: int,
    to_ts: int,
) -> pd.DataFrame:
    """Fetch cryptocurrency market data from API with Streamlit session cache.

    Args:
        api_url: MarketRaccoon API URL
        api_key: MarketRaccoon API key
        cache_file: Path to JSON cache file
        token_symbol: Token symbol to fetch
        from_ts: Unix timestamp for start date
        to_ts: Unix timestamp for end date

    Returns:
        DataFrame with columns: Date (index), Price or None if empty
    """
    api = ApiMarket(api_url, api_key=api_key, cache_file=cache_file)
    return api.get_cryptocurrency_market_cached(
        token_symbol=token_symbol, from_timestamp=from_ts, to_timestamp=to_ts
    )


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_api_fiat_rates(api_url: str, api_key: str, cache_file: str) -> pd.DataFrame:
    """Fetch all historical fiat exchange rates from API with Streamlit cache.

    Args:
        api_url: MarketRaccoon API URL
        api_key: MarketRaccoon API key
        cache_file: Path to JSON cache file

    Returns:
        DataFrame with columns: Date (index), price (USD→EUR rate)
        or None if empty
    """
    api = ApiMarket(api_url, api_key=api_key, cache_file=cache_file)
    return api.get_currency()


def plot_modern_graph(
    df: pd.DataFrame,
    title: str = None,
    y_label: str = None,
    optimize_y_range: bool = False,
):
    """Plot data with modern style matching other pages.

    Args:
        df: DataFrame with datetime index and one or more value columns
        title: Optional chart title
        y_label: Optional y-axis label
        optimize_y_range: If True, adjusts y-axis range to fit data tightly
    """
    if df is None or df.empty:
        st.info("No data available")
        return

    # Get target currency from settings
    target_currency = st.session_state.settings.get("fiat_currency", "EUR")
    currency_symbol = get_currency_symbol(target_currency)

    # Create plotly figure
    fig = go.Figure()

    # Add traces for each column
    for col in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df[col],
                mode="lines",
                name=col,
                fill="tozeroy" if len(df.columns) == 1 else None,
                line=dict(width=2),
            )
        )

    # Set default labels if not provided
    if y_label is None:
        y_label = f"Value ({currency_symbol})"
    if title is None:
        title = "Chart"

    layout_config = {
        "title": title,
        "xaxis_title": "Date",
        "yaxis_title": y_label,
        "hovermode": "x unified",
        "height": 400,
    }

    # Optimize y-axis range if requested
    if optimize_y_range:
        # Calculate min and max values across all columns
        y_min = df.min().min()
        y_max = df.max().max()

        # Add 2% margin on each side for better visualization
        y_range = y_max - y_min
        margin = y_range * 0.02

        layout_config["yaxis"] = {
            "title": y_label,
            "range": [y_min - margin, y_max + margin],
        }

    fig.update_layout(**layout_config)

    st.plotly_chart(fig, width="stretch")


def plot_dual_axis_graph(df: pd.DataFrame, title: str = None, token: str = None):
    """Plot data with two separate optimized y-axes for Value and Count.

    Args:
        df: DataFrame with datetime index, 'Value' and 'Count' columns
        title: Optional chart title
        token: Token symbol for labeling
    """
    if df is None or df.empty:
        st.info("No data available")
        return

    # Get target currency from settings
    target_currency = st.session_state.settings.get("fiat_currency", "EUR")
    currency_symbol = get_currency_symbol(target_currency)

    # Create plotly figure with dual y-axes
    fig = go.Figure()

    # Find the Value column (case-insensitive)
    value_col = None
    count_col = None
    for col in df.columns:
        if col.lower() == "value":
            value_col = col
        elif col.lower() == "count":
            count_col = col

    if value_col is None or count_col is None:
        st.error("DataFrame must contain 'Value' and 'Count' columns")
        return

    # Add Value trace on primary y-axis (left)
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[value_col],
            mode="lines",
            name=f"Value ({currency_symbol})",
            line=dict(width=2, color="#1f77b4"),
            yaxis="y1",
        )
    )

    # Add Count trace on secondary y-axis (right)
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[count_col],
            mode="lines",
            name="Count",
            line=dict(width=2, color="#ff7f0e"),
            yaxis="y2",
        )
    )

    # Calculate optimized ranges for both axes
    value_min = df[value_col].min()
    value_max = df[value_col].max()
    value_range = value_max - value_min
    value_margin = value_range * 0.02

    count_min = df[count_col].min()
    count_max = df[count_col].max()
    count_range = count_max - count_min
    count_margin = count_range * 0.02

    # Set title
    if title is None:
        title = (
            f"{token} - Assets Balance Over Time"
            if token
            else "Assets Balance Over Time"
        )

    # Configure layout with dual y-axes
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis=dict(
            title=f"Value ({currency_symbol})",
            range=[value_min - value_margin, value_max + value_margin],
            side="left",
        ),
        yaxis2=dict(
            title="Count",
            range=[count_min - count_margin, count_max + count_margin],
            overlaying="y",
            side="right",
        ),
        hovermode="x unified",
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    st.plotly_chart(fig, width="stretch")


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
            df = df.rename(
                columns={"amount": "Amount", value_column: f"Value({target_currency})"}
            )
            df = df.sort_values(by="Repartition(%)", ascending=False)
            st.dataframe(df, width="stretch", height=height)

            # Display total with appropriate currency symbol
            currency_symbol = get_currency_symbol(target_currency)
            st.write(
                f"Total value: {currency_symbol}"
                + str(round(df[f"Value({target_currency})"].sum(), 2))
            )
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
    section: str,
    token: str,
    start_timestamp: int,
    end_timestamp: int,
    use_api: bool = False,
):
    logger.debug("Draw tab content for token %s", token)
    if section == "Assets Balances":
        with st.spinner("Loading assets balances...", show_time=True):
            if use_api:
                # Get counts from local database
                df_counts = tokensdb.get_token_counts(
                    token, start_timestamp, end_timestamp
                )
                if df_counts is None:
                    st.warning(f"No balance data found for {token} in local database")
                    df_view = None
                else:
                    # Get prices from API (cached)
                    api_url = st.session_state.settings["marketraccoon_url"]
                    api_key = st.session_state.settings.get("marketraccoon_token")
                    cache_file = os.path.join(
                        st.session_state.settings["data_path"], "api_cache.json"
                    )
                    df_prices = fetch_api_crypto_market(
                        api_url,
                        api_key,
                        cache_file,
                        token,
                        start_timestamp,
                        end_timestamp,
                    )
                    if df_prices is None:
                        st.warning(
                            f"No price data found for {token} in API, falling back to local database"
                        )
                        df_view = tokensdb.get_token_balances(
                            token, start_timestamp, end_timestamp
                        )

                        # Fallback local (EUR) : convertir si nécessaire
                        target_currency = st.session_state.settings.get(
                            "fiat_currency", "EUR"
                        )
                        if df_view is not None and target_currency != "EUR":
                            df_fiat = fetch_api_fiat_rates(api_url, api_key, cache_file)
                            value_col = (
                                "Value" if "Value" in df_view.columns else "value"
                            )
                            df_view = convert_dataframe_prices_historical(
                                df_view, value_col, "EUR", target_currency, df_fiat
                            )
                    else:
                        # Conversion USD → devise cible avec taux historiques
                        if "source_currency" in df_prices.columns:
                            source_currency = df_prices["source_currency"].iloc[0]
                            target_currency = st.session_state.settings.get(
                                "fiat_currency", "EUR"
                            )

                            if source_currency != target_currency:
                                df_fiat = fetch_api_fiat_rates(
                                    api_url, api_key, cache_file
                                )
                                df_prices = convert_dataframe_prices_historical(
                                    df_prices,
                                    "Price",
                                    source_currency,
                                    target_currency,
                                    df_fiat,
                                )

                            df_prices = df_prices.drop(columns=["source_currency"])

                        # Merge counts with API prices (déjà converti)
                        df_view = df_counts.join(df_prices, how="outer")
                        df_view = df_view.ffill()  # Forward fill missing values
                        df_view = df_view.dropna()  # Remove rows with missing data
                        # Calculate Value = Price * Count
                        df_view["Value"] = df_view["Price"] * df_view["Count"]
                        # Keep only Value and Count columns
                        df_view = df_view[["Value", "Count"]]
            else:
                # Use local SQLite database (données en EUR)
                df_view = tokensdb.get_token_balances(
                    token, start_timestamp, end_timestamp
                )

                # Conversion EUR → devise cible si nécessaire
                target_currency = st.session_state.settings.get("fiat_currency", "EUR")
                if df_view is not None and target_currency != "EUR":
                    api_url = st.session_state.settings["marketraccoon_url"]
                    api_key = st.session_state.settings.get("marketraccoon_token")
                    cache_file = os.path.join(
                        st.session_state.settings["data_path"], "api_cache.json"
                    )
                    df_fiat = fetch_api_fiat_rates(api_url, api_key, cache_file)
                    # Value = price * count (en EUR), convertir la colonne Value
                    value_col = "Value" if "Value" in df_view.columns else "value"
                    df_view = convert_dataframe_prices_historical(
                        df_view, value_col, "EUR", target_currency, df_fiat
                    )
    elif section == "Market":
        with st.spinner("Loading market...", show_time=True):
            if use_api:
                # Use MarketRaccoon API (cached)
                api_url = st.session_state.settings["marketraccoon_url"]
                api_key = st.session_state.settings.get("marketraccoon_token")
                cache_file = os.path.join(
                    st.session_state.settings["data_path"], "api_cache.json"
                )
                df_view = fetch_api_crypto_market(
                    api_url, api_key, cache_file, token, start_timestamp, end_timestamp
                )

                # Conversion USD → devise cible avec taux historiques
                if df_view is not None and "source_currency" in df_view.columns:
                    source_currency = df_view["source_currency"].iloc[0]
                    target_currency = st.session_state.settings.get(
                        "fiat_currency", "EUR"
                    )

                    if source_currency != target_currency:
                        df_fiat = fetch_api_fiat_rates(api_url, api_key, cache_file)
                        df_view = convert_dataframe_prices_historical(
                            df_view, "Price", source_currency, target_currency, df_fiat
                        )

                    # Supprimer la colonne de métadonnée pour l'affichage
                    df_view = df_view.drop(columns=["source_currency"])
            else:
                # Use local SQLite database (données en EUR)
                df_view = markgetdb.get_token_market(
                    token, start_timestamp, end_timestamp
                )

                # Conversion EUR → devise cible si nécessaire
                target_currency = st.session_state.settings.get("fiat_currency", "EUR")
                if df_view is not None and target_currency != "EUR":
                    api_url = st.session_state.settings["marketraccoon_url"]
                    api_key = st.session_state.settings.get("marketraccoon_token")
                    cache_file = os.path.join(
                        st.session_state.settings["data_path"], "api_cache.json"
                    )
                    df_fiat = fetch_api_fiat_rates(api_url, api_key, cache_file)
                    df_view = convert_dataframe_prices_historical(
                        df_view, "Price", "EUR", target_currency, df_fiat
                    )
    else:
        df_view = None
    if df_view is not None:
        if section == "Assets Balances":
            column_value = "value"  # Match the actual column name from database
            label = "Balance"
        else:
            column_value = "Price"
            label = "Current Price"

        # Find the actual column name (case-insensitive)
        actual_column = None
        for col in df_view.columns:
            if col.lower() == column_value.lower():
                actual_column = col
                break
        if actual_column is None:
            actual_column = column_value

        # Récupérer le symbole de devise dynamique
        target_currency = st.session_state.settings.get("fiat_currency", "EUR")
        currency_symbol = get_currency_symbol(target_currency)

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
            current_price = df_view[actual_column].iloc[-1]
            st.metric(
                label,
                value=f"{round(current_price, 2)} {currency_symbol}",
                delta=(
                    f"{round(((last - first) / first) * 100, 2)} %"
                    if first != 0
                    else "0 %"
                    if last == 0
                    else "∞ %"
                ),
            )
        with mcol3:
            min_price = df_view[actual_column].min()
            min_price_date = df_view.index[
                df_view[actual_column] == df_view[actual_column].min()
            ]
            st.metric(
                "Timeframe Low",
                value=f"{round(min_price, 2)} {currency_symbol}",
                help=f"Date: {min_price_date[0]}",
                delta=f"{round(((current_price - min_price) / min_price) * 100, 2)} %",
            )
        with mcol4:
            max_price = df_view[actual_column].max()
            max_price_date = df_view.index[
                df_view[actual_column] == df_view[actual_column].max()
            ]
            st.metric(
                "Timeframe High",
                value=f"{round(max_price, 2)} {currency_symbol}",
                help=f"Date: {max_price_date[0]}",
                delta=f"{round(((current_price - max_price) / max_price) * 100, 2)} %",
            )

        col1, col2 = st.columns([3, 1])
        with col1:
            if section == "Assets Balances":
                # Use dual-axis graph for Assets Balances
                plot_dual_axis_graph(df_view, token=token)
            else:
                # Use single-axis graph for Market with optimized y-range
                chart_title = f"{token} - {label} Over Time"
                plot_modern_graph(df_view, title=chart_title, optimize_y_range=True)
        with col2:
            col2.dataframe(df_view, width="stretch")

    else:
        st.info("No data available")


def build_tabs(section: str = "Assets Balances", use_api: bool = False):
    start_timestamp = toTimestamp_A(
        st.session_state.startdate, pd.to_datetime("00:00:00").time()
    )
    end_timestamp = toTimestamp_A(
        st.session_state.enddate, pd.to_datetime("23:59:59").time()
    )
    if section == "Assets Balances":
        # For Assets Balances, always use local tokens since we need count data
        available_tokens = tokensdb.get_tokens()
    elif section == "Market":
        if use_api:
            # Get tokens from API (cached)
            api_url = st.session_state.settings["marketraccoon_url"]
            api_key = st.session_state.settings.get("marketraccoon_token")
            cache_file = os.path.join(
                st.session_state.settings["data_path"], "api_cache.json"
            )
            coins_df = fetch_api_coins(api_url, api_key, cache_file)
            if coins_df is not None and not coins_df.empty:
                available_tokens = coins_df["symbol"].unique().tolist()
            else:
                st.warning(
                    "Unable to fetch tokens from API, falling back to local database"
                )
                available_tokens = markgetdb.get_tokens()
        else:
            available_tokens = markgetdb.get_tokens()
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

        # Save token preferences to settings
        st.session_state.settings["graphs_selected_tokens"] = temp_tokens
        config = Configuration()
        config.save_config(st.session_state.settings)
        logger.debug("Saved token preferences: %s", temp_tokens)

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
                    use_api,
                )
            idx_token += 1


def build_price_tab(
    df: pd.DataFrame, chart_title: str = None, chart_y_label: str = None
):
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
            # Use provided title and y_label, or defaults
            title = chart_title if chart_title else "USD/EUR Exchange Rate Over Time"
            y_label = chart_y_label if chart_y_label else "EUR"
            plot_modern_graph(
                df_view, title=title, y_label=y_label, optimize_y_range=True
            )
        with col2:
            col2.dataframe(df_view, width="stretch")

    else:
        st.error("The end date must be after the start date")


use_api_sidebar = False  # Default value, may be overridden in sidebar

with st.sidebar:
    add_selectbox = st.selectbox(
        "Assets View",
        ("Global", "Assets Balances", "Market", "Currency"),
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

    # Data source toggle for Market and Assets Balances views
    if add_selectbox in ("Market", "Assets Balances"):
        st.divider()
        use_api_sidebar = st.toggle(
            "Use API",
            value=False,
            help="Use MarketRaccoon API instead of local SQLite database",
            key="data_source_toggle",
        )
        if use_api_sidebar:
            st.caption("📡 API MarketRaccoon")
            # Clear cache button
            if st.button("Clear API Cache", help="Clear cached API responses"):
                fetch_api_coins.clear()
                fetch_api_crypto_market.clear()
                st.success("Cache cleared!")
                st.rerun()
        else:
            st.caption("💾 SQLite local")

    # Currency direction toggle
    if add_selectbox == "Currency":
        st.divider()
        currency_inverted = st.toggle(
            "EUR/USD",
            value=True,
            help="EUR/USD (default) or USD/EUR",
            key="currency_direction_toggle",
        )

tokensdb = TokensDatabase(st.session_state.settings["dbfile"])
markgetdb = Market(
    st.session_state.settings["dbfile"],
    st.session_state.settings["coinmarketcap_token"],
)

# Initialize ApiMarket for MarketRaccoon API access
cache_file = os.path.join(st.session_state.settings["data_path"], "api_cache.json")
apimarket = ApiMarket(
    st.session_state.settings["marketraccoon_url"],
    api_key=st.session_state.settings.get("marketraccoon_token"),
    cache_file=cache_file,
)

if "tokens" not in st.session_state:
    # Load saved token preferences from settings
    st.session_state.tokens = st.session_state.settings.get(
        "graphs_selected_tokens", []
    )

if add_selectbox == "Global":
    logger.debug("Global")
    st.title("Global")
    aggregater_ui()

if add_selectbox == "Assets Balances":
    logger.debug("Assets Balances")
    st.title("Assets Balances")
    build_tabs(use_api=use_api_sidebar)

if add_selectbox == "Market":
    logger.debug("Market")
    st.title("Market")
    build_tabs("Market", use_api=use_api_sidebar)

if add_selectbox == "Currency":
    # Determine currency direction from toggle
    currency_inverted = st.session_state.get("currency_direction_toggle", True)

    # Update title and labels based on direction
    if currency_inverted:
        TITLE_TEXT = "Currency (EUR/USD)"
        CHART_TITLE = "EUR/USD Exchange Rate Over Time"
        CHART_Y_LABEL = "USD"
    else:
        TITLE_TEXT = "Currency (USD/EUR)"
        CHART_TITLE = "USD/EUR Exchange Rate Over Time"
        CHART_Y_LABEL = "EUR"

    logger.debug(TITLE_TEXT)
    st.title(TITLE_TEXT)

    # Initialize ApiMarket with caching support
    cache_file = os.path.join(st.session_state.settings["data_path"], "api_cache.json")
    market = ApiMarket(
        st.session_state.settings["marketraccoon_url"],
        api_key=st.session_state.settings.get("marketraccoon_token"),
        cache_file=cache_file,
    )

    # Fetch currency data (will use cache internally)
    currency_data = market.get_currency()

    # Invert prices if EUR/USD is selected
    if currency_inverted and currency_data is not None and not currency_data.empty:
        currency_data = currency_data.copy()
        currency_data["price"] = 1 / currency_data["price"]

    build_price_tab(currency_data, chart_title=CHART_TITLE, chart_y_label=CHART_Y_LABEL)

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
            submitted = st.form_submit_button("Submit", width="stretch")

        if submitted:
            timestamp = toTimestamp_B(date, time, utc=False)
            df_result = market.get_currency(timestamp=timestamp)

            if df_result is not None and not df_result.empty:
                value = df_result["price"].iloc[0]
                is_interpolated = df_result.get(
                    "interpolated", pd.Series([False])
                ).iloc[0]

                # Invert value if EUR/USD is selected
                if currency_inverted:
                    value = 1 / value

                st.session_state.interpolation_result = {
                    "value": value,
                    "is_interpolated": is_interpolated,
                    "currency_inverted": currency_inverted,
                }
            else:
                st.session_state.interpolation_result = None

    # Display interpolation results
    if st.session_state.interpolation_result is not None:
        result = st.session_state.interpolation_result
        value = result["value"]
        is_interpolated = result["is_interpolated"]
        result_currency_inverted = result.get("currency_inverted", True)

        # Determine the currency unit to display
        UNIT = "USD" if result_currency_inverted else "EUR"

        if value != 0.0:
            if is_interpolated:
                st.info(f"Interpolated value: {value:.6f} {UNIT}")
            else:
                st.info(f"Exact value: {value:.6f} {UNIT}")
        else:
            st.warning("Value is 0.0")
    elif (
        st.session_state.interpolation_result is None
        and "interpolation_result" in st.session_state
    ):
        st.info("No data available")
