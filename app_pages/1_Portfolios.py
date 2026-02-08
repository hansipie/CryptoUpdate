import logging
import traceback

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from modules.database.customdata import Customdata
from modules.database.portfolios import Portfolios
from modules.database.tokensdb import TokensDatabase
from modules.tools import (
    create_portfolio_dataframe,
    update,
    parse_last_update,
    get_currency_symbol
)
from modules.utils import dataframe_diff
from modules.configuration import configuration

logger = logging.getLogger(__name__)

st.title("Portfolios")


@st.dialog("Add new portfolio")
def add_new_portfolio():
    """Display dialog for creating a new portfolio.

    Shows a form with name input and bundle flag checkbox.
    On submit, creates the new portfolio.
    """
    name = st.text_input("Name")
    isbundle = st.checkbox("Is a Bundle", value=False)
    if st.button("Submit"):
        logger.debug("Adding portfolio %s", name)
        g_portfolios.add_portfolio(name, (1 if isbundle else 0))
        # Close dialog
        st.rerun()


@st.dialog("Danger Zone")
def danger_zone(name: str):
    """Display confirmation dialog for deleting a portfolio.

    Args:
        name: Name of portfolio to delete

    Shows a confirmation prompt requiring typing 'delete'.
    """
    st.write(f"Delete portfolio {name}?")
    confirm = st.text_input("Type 'delete' to confirm")
    if st.button("Delete") and confirm == "delete":
        g_portfolios.delete_portfolio(name)
        st.rerun()


@st.dialog("Rename portfolio")
def rename_portfolio(name: str):
    """Display dialog for renaming a portfolio.

    Args:
        name: Current name of portfolio to rename

    Shows input for new name and updates on submit.
    """
    new_name = st.text_input("New name")
    if st.button("Submit"):
        g_portfolios.rename_portfolio(name, new_name)
        st.rerun()


@st.dialog("Add Token")
def add_token(name: str):
    """Display dialog for adding a token to a portfolio.

    Args:
        name: Name of portfolio to add token to

    Shows inputs for token symbol and amount.
    """
    st.write(f"Add token to {name}")
    token = st.text_input("Token")
    token = token.upper()
    amount = st.number_input("Amount", min_value=0.0, format="%.8f")
    if st.button("Submit"):
        g_portfolios.set_token_add(name, token, amount)
        # Close dialog
        st.rerun()


@st.dialog("Delete Token")
def delete_token(portfolio_name: str):
    """Display dialog for removing tokens from a portfolio.

    Args:
        portfolio_name: Name of portfolio to remove tokens from

    Shows multi-select for choosing tokens to delete.
    """
    st.write(f"Delete token from {portfolio_name}")
    tokens = st.multiselect(
        "Token(s)",
        g_portfolios.get_tokens(portfolio_name),
        placeholder="Select a token",
    )
    if st.button("Submit"):
        for token in tokens:
            g_portfolios.delete_token_A(portfolio_name, token)
        # Close dialog
        st.rerun()


def portfolioUI(tabs: list):
    """Display portfolio management interface.

    Args:
        tabs: List of portfolio names to display

    Shows editable tables of token holdings and management buttons
    for each portfolio.
    """
    logger.debug("portfolioUI - Tabs: %s", tabs)

    tabs_widget = st.tabs(tabs)

    for i, tab in enumerate(tabs_widget):
        with tab:
            # Display historical chart above the table
            plot_portfolio_history(tabs[i], st.session_state.settings["dbfile"])
            st.divider()

            pf = g_portfolios.get_portfolio(tabs[i])
            df = create_portfolio_dataframe(pf)
            if not df.empty:  # Only create DataFrame if data exists
                # Get target currency from settings
                target_currency = st.session_state.settings.get("fiat_currency", "EUR")
                value_column = f"value({target_currency})"

                balance = df[value_column].sum()
                df.sort_values(by=[value_column], ascending=False, inplace=True)

                # Display total with appropriate currency symbol
                currency_symbol = get_currency_symbol(target_currency)
                st.write(f"Total value: {currency_symbol}{round(balance, 2)}")

                height = (len(df) * 35) + 38
                logger.debug("Dataframe:\n%s", df)
                updated_data = st.data_editor(
                    df,
                    width='stretch',
                    height=height,
                    column_config={
                        "token": st.column_config.TextColumn(disabled=True),
                        "amount": st.column_config.NumberColumn(format="%.8g"),
                        value_column: st.column_config.NumberColumn(
                            format=f"%.2f {currency_symbol}", disabled=True
                        ),
                    },
                )
                df_diff = dataframe_diff(df, updated_data)
                if not df_diff.empty:
                    g_portfolios.update_portfolio(
                        {tabs[i]: updated_data.to_dict(orient="index")}
                    )
                    logger.debug("## Rerun ##")
                    st.rerun()
                else:
                    logger.debug("## No Rerun ##")
            else:
                st.info("No data available")

            buttons_col1, buttons_col2, buttons_col3, buttons_col4 = st.columns(4)
            with buttons_col1:
                if st.button(
                    "Add Token",
                    key=f"addT_{i}",
                    width='stretch',
                    icon=":material/add:",
                ):
                    add_token(tabs[i])
            with buttons_col2:
                if st.button(
                    "Delete Token",
                    key=f"deleteT_{i}",
                    width='stretch',
                    icon=":material/remove:",
                ):
                    delete_token(tabs[i])
            with buttons_col3:
                if st.button(
                    "Rename Portfolio",
                    key=f"rename_{i}",
                    width='stretch',
                    icon=":material/edit:",
                ):
                    rename_portfolio(tabs[i])
            with buttons_col4:
                if st.button(
                    "Danger Zone",
                    key=f"dangerZ_{i}",
                    width='stretch',
                    type="primary",
                    icon=":material/destruction:",
                ):
                    danger_zone(tabs[i])


def load_portfolios(dbfile: str) -> Portfolios:
    """Load portfolios from database file.

    Args:
        dbfile: Path to database file

    Returns:
        Portfolios instance initialized with the database
    """
    return Portfolios(dbfile)


def get_portfolio_history(portfolio_name: str, dbfile: str) -> pd.DataFrame:
    """Get historical value of a portfolio over time.

    Args:
        portfolio_name: Name of the portfolio
        dbfile: Path to database file

    Returns:
        DataFrame with timestamp index and portfolio value
    """
    logger.debug("Getting history for portfolio %s", portfolio_name)

    # Get current portfolio tokens and amounts
    portfolio = Portfolios(dbfile)
    tokens_dict = portfolio.get_tokens(portfolio_name)

    if not tokens_dict:
        logger.warning("Portfolio %s is empty", portfolio_name)
        return pd.DataFrame()

    # Get historical prices from TokensDatabase
    tokensdb = TokensDatabase(dbfile)

    # Query all historical data for tokens in this portfolio
    import sqlite3
    with sqlite3.connect(dbfile) as con:
        # Get tokens list
        tokens_list = list(tokens_dict.keys())
        tokens_placeholder = ','.join(['?' for _ in tokens_list])

        query = f"""
            SELECT timestamp, token, price
            FROM TokensDatabase
            WHERE token IN ({tokens_placeholder})
            ORDER BY timestamp
        """
        df = pd.read_sql_query(query, con, params=tokens_list)

    if df.empty:
        logger.warning("No historical data found for portfolio %s", portfolio_name)
        return pd.DataFrame()

    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)
    df['timestamp'] = df['timestamp'].dt.tz_convert(tokensdb.local_timezone).dt.tz_localize(None)

    # Calculate value for each token at each timestamp
    df['amount'] = df['token'].map(lambda t: float(tokens_dict.get(t, 0)))
    df['value'] = df['price'] * df['amount']

    # Group by timestamp and sum values
    portfolio_value = df.groupby('timestamp')['value'].sum().reset_index()
    portfolio_value.columns = ['Date', 'Value']
    portfolio_value.set_index('Date', inplace=True)
    portfolio_value.sort_index(inplace=True)

    logger.debug("Portfolio history shape: %s", portfolio_value.shape)
    return portfolio_value


def plot_portfolio_history(portfolio_name: str, dbfile: str):
    """Plot the historical value of a portfolio.

    Args:
        portfolio_name: Name of the portfolio
        dbfile: Path to database file
    """
    df = get_portfolio_history(portfolio_name, dbfile)

    if df.empty:
        st.info("No historical data available for this portfolio")
        return

    # Get target currency from settings
    target_currency = st.session_state.settings.get("fiat_currency", "EUR")
    currency_symbol = get_currency_symbol(target_currency)

    # Create plotly figure
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['Value'],
        mode='lines',
        name=portfolio_name,
        fill='tozeroy',
        line=dict(width=2)
    ))

    fig.update_layout(
        title=f"Historical Value - {portfolio_name}",
        xaxis_title="Date",
        yaxis_title=f"Value ({currency_symbol})",
        hovermode='x unified',
        height=400
    )

    st.plotly_chart(fig, width="stretch")


@st.fragment
def execute_search():
    """Execute token search and display results.

    Shows a table of portfolios containing the searched token
    and their respective amounts.
    """
    df_search = pd.DataFrame.from_dict(
        g_portfolios.get_token_by_portfolio(st.session_state.search_target),
        orient="index",
        columns=["Amount"],
    )
    df_search.sort_index(inplace=True)
    logger.debug("Search result:\n%s", df_search)
    st.dataframe(df_search, width='stretch')


g_portfolios = load_portfolios(st.session_state.settings["dbfile"])


def save_toggle_preference():
    """Save toggle state to settings file when it changes."""
    logger.debug("Saving toggle preference: %s", st.session_state.show_empty_portfolios)
    # Update settings in session state
    st.session_state.settings["show_empty_portfolios"] = st.session_state.show_empty_portfolios
    # Save to file
    config = configuration()
    config.saveConfig(st.session_state.settings)


with st.sidebar:
    # Add new portfolio dialog
    if st.button(
        "Add new portfolio",
        key="add_new_portfolio",
        icon=":material/note_add:",
        width='stretch',
    ):
        add_new_portfolio()

    # Update prices
    if st.button(
        "Update prices",
        key="update_prices",
        icon=":material/update:",
        width='stretch',
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

    # search bar

    tokens = g_portfolios.aggregate_portfolios().keys()
    st.write("Search for a token:")
    if st.selectbox(
        "Search", tokens, index=None, label_visibility="collapsed", key="search_target"
    ):
        execute_search()

    st.divider()

    # Initialize toggle state from settings if not exists
    if "show_empty_portfolios" not in st.session_state:
        st.session_state.show_empty_portfolios = st.session_state.settings.get("show_empty_portfolios", True)

    # Toggle pour afficher/masquer les portefeuilles vides
    st.toggle(
        "Afficher les portefeuilles vides",
        key="show_empty_portfolios",
        help="Afficher ou masquer les portefeuilles sans token ou avec un solde nul.",
        on_change=save_toggle_preference
    )


def is_portfolio_empty(pf_name):
    pf = g_portfolios.get_portfolio(pf_name)
    df = create_portfolio_dataframe(pf)
    if df.empty:
        return True
    # Si tous les montants sont nuls ou absents
    if (df["amount"].fillna(0) == 0).all():
        return True
    return False

all_tabs = g_portfolios.get_portfolio_names()
# Lecture robuste de l'état du toggle avec fallback
show_empty = st.session_state.get("show_empty_portfolios", True)
if show_empty:
    tabs = all_tabs
else:
    tabs = [name for name in all_tabs if not is_portfolio_empty(name)]
logger.debug("Portfolios: %s", tabs)
if not tabs:
    st.info("Aucun portefeuille à afficher avec ce filtre.")
    st.stop()
else:
    try:
        portfolioUI(tabs)
    except Exception as e:
        st.error(f"UI Error: {str(e)}")
        traceback.print_exc()
