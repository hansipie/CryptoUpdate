import traceback
import streamlit as st
import pandas as pd
import logging
from modules.database.portfolios import Portfolios
from modules.database.customdata import Customdata
from modules.tools import update_database, create_portfolio_dataframe
from modules.utils import dataframe_diff


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
    logger.debug(f"portfolioUI - Tabs: {tabs}")

    tabs_widget = st.tabs(tabs)

    for i, tab in enumerate(tabs_widget):
        with tab:
            pf = g_portfolios.get_portfolio(tabs[i])
            df = create_portfolio_dataframe(pf)
            if not df.empty:  # Only create DataFrame if data exists
                balance = df["value(€)"].sum()
                df.sort_values(by=["value(€)"], ascending=False, inplace=True)
                st.write(f"Total value: €{round(balance, 2)}")
                height = (len(df) * 35) + 38
                logger.debug("Dataframe:\n%s", df.to_string())
                updated_data = st.data_editor(
                    df,
                    use_container_width=True,
                    height=height,
                    column_config={
                        "token": st.column_config.TextColumn(disabled=True),
                        "amount": st.column_config.NumberColumn(format="%.8g"),
                        "value(€)": st.column_config.NumberColumn(format="%.2f €", disabled=True),
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
                    use_container_width=True,
                    icon=":material/add:",
                ):
                    add_token(tabs[i])
            with buttons_col2:
                if st.button(
                    "Delete Token",
                    key=f"deleteT_{i}",
                    use_container_width=True,
                    icon=":material/remove:",
                ):
                    delete_token(tabs[i])
            with buttons_col3:
                if st.button(
                    "Rename Portfolio",
                    key=f"rename_{i}",
                    use_container_width=True,
                    icon=":material/edit:",
                ):
                    rename_portfolio(tabs[i])
            with buttons_col4:
                if st.button(
                    "Danger Zone",
                    key=f"dangerZ_{i}",
                    use_container_width=True,
                    type="primary",
                    icon=":material/destruction:",
                ):
                    danger_zone(tabs[i])


def update():
    """Update cryptocurrency prices in database.
    
    Attempts to fetch latest prices and update the database.
    Shows success toast or error message on completion.
    """
    try:
        update_database(
            st.session_state.settings["dbfile"], st.session_state.settings["coinmarketcap_token"]
        )
        st.toast("Prices updated", icon=":material/check:")
        st.rerun()
    except Exception as e:
        st.error(f"Update Error: {str(e)}")


def load_portfolios(dbfile: str) -> Portfolios:
    """Load portfolios from database file.
    
    Args:
        dbfile: Path to database file
        
    Returns:
        Portfolios instance initialized with the database
    """
    return Portfolios(dbfile)


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
    logger.debug("Search result:\n%s", df_search.to_string())
    st.dataframe(df_search, use_container_width=True)


g_portfolios = load_portfolios(st.session_state.settings["dbfile"])

with st.sidebar:
    # Add new portfolio dialog
    if st.button(
        "Add new portfolio",
        key="add_new_portfolio",
        icon=":material/note_add:",
        use_container_width=True,
    ):
        add_new_portfolio()

    # Update prices
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
        st.markdown(" - *Last update: " + str(last_update).split('.', maxsplit=1)[0] + "*")
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

# Display portfolios
tabs = g_portfolios.get_portfolio_names()
logger.debug(f"Portfolios: {tabs}")
if not tabs:
    st.info("No portfolios found")
    st.stop()
else:
    try:
        portfolioUI(tabs)
    except Exception as e:
        st.error(f"UI Error: {str(e)}")
        traceback.print_exc()
